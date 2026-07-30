import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from date_utils import DateEntry, to_display, to_storage, today_storage
from searchable_combo import SearchableComboBox
from database import (get_vendors, get_purchases, create_credit_note,
                      create_debit_note, get_notes, cancel_note, update_note)


class CreditDebitNoteFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None, note_type="credit"):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self.note_type = note_type
        self.table = "credit_notes" if note_type == "credit" else "debit_notes"
        self.title_text = "Credit Note" if note_type == "credit" else "Debit Note"
        self.desc = "Reduces payable" if note_type == "credit" else "Increases payable"
        self._editing_id = None
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self._editing_id = None

        title_color = "#16A34A" if self.note_type == "credit" else "#DC2626"
        ctk.CTkLabel(self, text=self.title_text,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=title_color).pack(anchor="w", padx=24, pady=(20, 2))
        ctk.CTkLabel(self, text=self.desc,
                     font=ctk.CTkFont(size=12), text_color="#888").pack(anchor="w", padx=24, pady=(0, 8))

        form = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        form.pack(fill="x", padx=24, pady=(0, 12))
        form.grid_columnconfigure((1, 3), weight=1)
        kw = {"padx": 14, "pady": 8}

        ctk.CTkLabel(form, text="Date *", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", **kw)
        self._date_entry = DateEntry(form)
        self._date_entry.grid(row=0, column=1, sticky="w", **kw)

        ctk.CTkLabel(form, text="Vendor *", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=2, sticky="w", **kw)
        vendors = get_vendors(self.db_path)
        self._vendor_names = ["-- Select Vendor --"] + [v["name"] for v in vendors]
        self._vendor_ids = [None] + [v["id"] for v in vendors]
        self._vendor_var = tk.StringVar(value="-- Select Vendor --")
        self._vendor_menu = SearchableComboBox(form, values=self._vendor_names,
                                               textvariable=self._vendor_var,
                                               command=self._on_vendor_change, width=220)
        self._vendor_menu.grid(row=0, column=3, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Ref Invoice").grid(row=1, column=0, sticky="w", **kw)
        self._inv_var = tk.StringVar(value="-- Select Invoice --")
        self._purchase_labels = ["-- Select Invoice --"]
        self._purchase_ids = [None]
        self._purchases_for_vendor = []
        self._inv_menu = SearchableComboBox(form, values=self._purchase_labels,
                                            textvariable=self._inv_var,
                                            command=self._on_invoice_change, width=220)
        self._inv_menu.grid(row=1, column=1, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Value *", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=2, sticky="w", **kw)
        self._value_var = tk.StringVar()
        self._value_var.trace_add("write", self._calc_total)
        ctk.CTkEntry(form, textvariable=self._value_var,
                     placeholder_text="0.00").grid(row=1, column=3, sticky="ew", **kw)

        ctk.CTkLabel(form, text="GST").grid(row=2, column=0, sticky="w", **kw)
        self._gst_var = tk.StringVar(value="0")
        self._gst_var.trace_add("write", self._calc_total)
        ctk.CTkEntry(form, textvariable=self._gst_var).grid(row=2, column=1, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Total", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=2, sticky="w", **kw)
        self._total_lbl = ctk.CTkLabel(form, text="\u20b90.00",
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        text_color=title_color)
        self._total_lbl.grid(row=2, column=3, sticky="w", **kw)

        ctk.CTkLabel(form, text="Narration").grid(row=3, column=0, sticky="w", **kw)
        self._narration_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._narration_var).grid(
            row=3, column=1, columnspan=3, sticky="ew", **kw)

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.grid(row=4, column=0, columnspan=4, pady=14)
        ctk.CTkButton(btn_row, text="Clear", width=90, fg_color="#6B7280",
                      command=self._clear).pack(side="left", padx=8)
        fg = "#16A34A" if self.note_type == "credit" else "#DC2626"
        self._save_btn = ctk.CTkButton(btn_row, text=f"Save {self.title_text}", width=150,
                                        fg_color=fg, command=self._submit)
        self._save_btn.pack(side="left", padx=8)

        self._status_lbl = ctk.CTkLabel(form, text="",
                                         font=ctk.CTkFont(size=13, weight="bold"),
                                         text_color=fg)
        self._status_lbl.grid(row=5, column=0, columnspan=4, pady=4)

        # History
        ctk.CTkLabel(self, text=f"Recent {self.title_text}s",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=26, pady=(4, 4))
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        headers = ["Voucher No", "Date", "Vendor", "Ref Invoice", "Value", "GST", "Total", "Status"]
        widths = [90, 100, 170, 110, 90, 80, 100, 80]
        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(headers, widths):
            ctk.CTkLabel(h, text=col, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        ctk.CTkLabel(h, text="Actions", width=100,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=4, pady=6)

        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._widths = widths
        self._load_list()

    def _on_vendor_change(self, val):
        vid = self._get_vendor_id()
        if vid:
            purchases = get_purchases(self.db_path, vendor_id=vid, fy_id=self.fy_id)
            self._purchases_for_vendor = purchases
            self._purchase_labels = ["-- Select Invoice --"] + [
                f"{p['voucher_no']} | {p.get('invoice_number') or p['date']} | \u20b9{p['total_value']:,.0f}"
                for p in purchases
            ]
            self._purchase_ids = [None] + [p["id"] for p in purchases]
        else:
            self._purchase_labels = ["-- Select Invoice --"]
            self._purchase_ids = [None]
            self._purchases_for_vendor = []
        self._inv_menu.configure(values=self._purchase_labels)
        self._inv_menu.set(self._purchase_labels[0])

    def _on_invoice_change(self, val):
        if val in self._purchase_labels:
            idx = self._purchase_labels.index(val)
            if idx > 0:
                p = self._purchases_for_vendor[idx - 1]
                self._value_var.set(str(p["purchase_value"]))
                self._gst_var.set(str(p["gst_amount"]))

    def _calc_total(self, *_):
        try:
            v = float(self._value_var.get() or 0)
            g = float(self._gst_var.get() or 0)
            self._total_lbl.configure(text=f"\u20b9{v + g:,.2f}")
        except ValueError:
            self._total_lbl.configure(text="\u20b9-")

    def _get_vendor_id(self):
        name = self._vendor_var.get()
        if name in self._vendor_names:
            idx = self._vendor_names.index(name)
            return self._vendor_ids[idx]
        return None

    def _get_purchase_id(self):
        val = self._inv_var.get()
        if val in self._purchase_labels:
            return self._purchase_ids[self._purchase_labels.index(val)]
        return None

    def _submit(self):
        date_str = self._date_entry.get()
        if not date_str:
            messagebox.showerror("Error", "Date is required.")
            return
        vendor_id = self._get_vendor_id()
        if not vendor_id:
            messagebox.showerror("Error", "Select a vendor.")
            return
        try:
            value = float(self._value_var.get() or 0)
            if value <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid value > 0.")
            return
        try:
            gst = float(self._gst_var.get() or 0)
        except ValueError:
            gst = 0

        ref_id = self._get_purchase_id()
        narration = self._narration_var.get().strip()

        if self._editing_id:
            update_note(self.db_path, self.table, self._editing_id,
                        date_str, vendor_id, ref_id, value, gst, narration)
            self._status_lbl.configure(text=f"{self.title_text} updated!")
            self._editing_id = None
            self._save_btn.configure(text=f"Save {self.title_text}")
        else:
            if self.note_type == "credit":
                _, vno = create_credit_note(self.db_path, date_str, vendor_id,
                                            ref_purchase_id=ref_id,
                                            value=value, gst_amount=gst, narration=narration)
            else:
                _, vno = create_debit_note(self.db_path, date_str, vendor_id,
                                           ref_purchase_id=ref_id,
                                           value=value, gst_amount=gst, narration=narration)
            self._status_lbl.configure(text=f"{self.title_text} #{vno} saved!")

        self._clear(keep_status=True)
        self._load_list()

    def load_for_edit(self, note_id):
        notes = get_notes(self.db_path, self.table, include_cancelled=False)
        n = next((x for x in notes if x["id"] == note_id), None)
        if not n:
            return
        self._editing_id = note_id
        self._date_entry.set(n["date"])
        self._value_var.set(str(n["value"]))
        self._gst_var.set(str(n["gst_amount"]))
        self._narration_var.set(n.get("narration") or "")
        if n.get("vendor_id") in self._vendor_ids:
            idx = self._vendor_ids.index(n["vendor_id"])
            self._vendor_menu.set(self._vendor_names[idx])
            self._on_vendor_change(self._vendor_names[idx])
        self._save_btn.configure(text=f"Update {self.title_text}")
        self._status_lbl.configure(text=f"Editing {self.title_text} #{n['voucher_no']}",
                                   text_color="#D97706")

    def _clear(self, keep_status=False):
        self._date_entry.set(today_storage())
        self._vendor_menu.set("-- Select Vendor --")
        self._inv_menu.set("-- Select Invoice --")
        self._value_var.set("")
        self._gst_var.set("0")
        self._narration_var.set("")
        self._total_lbl.configure(text="\u20b90.00")
        self._editing_id = None
        self._save_btn.configure(text=f"Save {self.title_text}")
        if not keep_status:
            self._status_lbl.configure(text="")

    def _load_list(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        notes = get_notes(self.db_path, self.table, fy_id=self.fy_id, include_cancelled=True)
        if not notes:
            ctk.CTkLabel(self._scroll, text=f"No {self.title_text}s yet.",
                         text_color="#999").pack(pady=20)
            return
        for i, n in enumerate(reversed(notes[:60])):
            is_cancelled = n["status"] == "cancelled"
            bg = "#FFF0F0" if is_cancelled else ("#F8FAFF" if i % 2 == 0 else "white")
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            vals = [n["voucher_no"], to_display(n["date"]),
                    (n.get("vendor_name") or "")[:20],
                    str(n.get("ref_purchase_id") or "-"),
                    f"\u20b9{n['value']:,.2f}", f"\u20b9{n['gst_amount']:,.2f}",
                    f"\u20b9{n['total_value']:,.2f}", n["status"]]
            color = "#888" if is_cancelled else "#333"
            for val, width in zip(vals, self._widths):
                ctk.CTkLabel(row, text=str(val)[:20], width=width,
                             font=ctk.CTkFont(size=11), text_color=color).pack(side="left", padx=4, pady=4)
            if not is_cancelled:
                ctk.CTkButton(row, text="Edit", width=46, height=24,
                              fg_color="#6366F1", hover_color="#4F46E5",
                              font=ctk.CTkFont(size=10),
                              command=lambda nid=n["id"]: self.load_for_edit(nid)).pack(side="left", padx=2)
                ctk.CTkButton(row, text="Cancel", width=54, height=24,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=10),
                              command=lambda nid=n["id"], vno=n["voucher_no"]: self._cancel(nid, vno)
                              ).pack(side="left", padx=2)

    def _cancel(self, nid, vno):
        if messagebox.askyesno("Cancel", f"Cancel {self.title_text} {vno}?"):
            cancel_note(self.db_path, self.table, nid)
            self._load_list()

    def refresh(self):
        self._load_list()
