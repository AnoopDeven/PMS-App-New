import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from date_utils import DateEntry, to_display, to_storage, today_storage
from searchable_combo import SearchableComboBox
from database import (get_vendors, create_purchase, update_purchase,
                      get_purchases, cancel_purchase, get_purchase,
                      validate_fy_date, get_vendor_advance_balance,
                      apply_advance_to_purchase)
from pdf_generator import print_purchase_pdf


class PurchaseVoucherFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self._editing_id = None
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self._editing_id = None

        ctk.CTkLabel(self, text="Purchase Voucher",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=24, pady=(20, 8))

        form = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        form.pack(fill="x", padx=24, pady=(0, 12))
        form.grid_columnconfigure((1, 3), weight=1)

        kw = {"padx": 14, "pady": 8}

        # Row 0: Entry Date + Invoice No.
        ctk.CTkLabel(form, text="Entry Date *", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", **kw)
        self._date_entry = DateEntry(form)
        self._date_entry.grid(row=0, column=1, sticky="w", **kw)

        ctk.CTkLabel(form, text="Invoice No.", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=2, sticky="w", **kw)
        self._inv_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._inv_var).grid(row=0, column=3, sticky="ew", **kw)

        # Row 1: Invoice Date + Vendor
        ctk.CTkLabel(form, text="Invoice Date", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", **kw)
        self._inv_date_entry = DateEntry(form)
        self._inv_date_entry.grid(row=1, column=1, sticky="w", **kw)

        ctk.CTkLabel(form, text="Vendor *", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=2, sticky="w", **kw)
        self._vendor_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._vendor_frame.grid(row=1, column=3, sticky="ew", **kw)
        self._refresh_vendor_ui()

        # Row 2: Purchase Value + GST
        ctk.CTkLabel(form, text="Purchase Value *", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, sticky="w", **kw)
        self._pv_var = tk.StringVar()
        self._pv_var.trace_add("write", self._calc_total)
        ctk.CTkEntry(form, textvariable=self._pv_var,
                     placeholder_text="0.00").grid(row=2, column=1, sticky="ew", **kw)

        ctk.CTkLabel(form, text="GST Amount").grid(row=2, column=2, sticky="w", **kw)
        self._gst_var = tk.StringVar(value="0")
        self._gst_var.trace_add("write", self._calc_total)
        ctk.CTkEntry(form, textvariable=self._gst_var).grid(row=2, column=3, sticky="ew", **kw)

        # Row 3: Total + Narration
        ctk.CTkLabel(form, text="Total Value", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, sticky="w", **kw)
        self._total_lbl = ctk.CTkLabel(form, text="\u20b90.00",
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        text_color="#1B4FD8")
        self._total_lbl.grid(row=3, column=1, sticky="w", **kw)

        ctk.CTkLabel(form, text="Narration").grid(row=3, column=2, sticky="w", **kw)
        self._narration_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._narration_var).grid(
            row=3, column=3, sticky="ew", **kw)

        # Row 4: Advance info (shown when vendor has advance balance)
        self._advance_lbl = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=11),
                                          text_color="#16A34A")
        self._advance_lbl.grid(row=4, column=0, columnspan=4, pady=(0, 4), padx=14, sticky="w")

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.grid(row=5, column=0, columnspan=4, pady=14)
        ctk.CTkButton(btn_row, text="Clear", width=90, fg_color="#6B7280",
                      command=self._clear).pack(side="left", padx=8)
        self._save_btn = ctk.CTkButton(btn_row, text="Save Purchase", width=130,
                                        fg_color="#1B4FD8", hover_color="#1440B0",
                                        command=self._submit)
        self._save_btn.pack(side="left", padx=8)
        self._print_btn = ctk.CTkButton(btn_row, text="Print PDF", width=110,
                                         fg_color="#7C3AED", hover_color="#6D28D9",
                                         command=self._print_pdf, state="disabled")
        self._print_btn.pack(side="left", padx=8)

        self._status_lbl = ctk.CTkLabel(form, text="",
                                         font=ctk.CTkFont(size=13, weight="bold"),
                                         text_color="#16A34A")
        self._status_lbl.grid(row=6, column=0, columnspan=4, pady=4)

        # Recent list
        headers = ["Voucher No", "Entry Date", "Inv Date", "Vendor", "Invoice No",
                   "Value", "GST", "Total", "Outstanding"]
        widths = [80, 90, 90, 150, 100, 80, 70, 90, 100]

        ctk.CTkLabel(self, text="Recent Purchases",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=26, pady=(4, 4))
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(headers, widths):
            ctk.CTkLabel(h, text=col, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        ctk.CTkLabel(h, text="Actions", width=110,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._widths = widths
        self._last_pid = None
        self._load_list()

    def _refresh_vendor_ui(self):
        for w in self._vendor_frame.winfo_children():
            w.destroy()
        vendors = get_vendors(self.db_path, category="creditor")
        self._vendor_names = ["-- Select Vendor --"] + [v["name"] for v in vendors]
        self._vendor_ids = [None] + [v["id"] for v in vendors]
        self._vendor_var = tk.StringVar(value="-- Select Vendor --")
        self._vendor_menu = SearchableComboBox(self._vendor_frame, values=self._vendor_names,
                                               textvariable=self._vendor_var,
                                               command=self._on_vendor_change, width=220)
        self._vendor_menu.pack(side="left")
        ctk.CTkButton(self._vendor_frame, text="Refresh", width=70, height=28,
                      fg_color="#6B7280", font=ctk.CTkFont(size=11),
                      command=self._refresh_vendor_ui).pack(side="left", padx=6)

    def _on_vendor_change(self, val=None):
        vid = self._get_vendor_id()
        if vid and not self._editing_id:
            adv = get_vendor_advance_balance(self.db_path, vid)
            if adv > 0:
                self._advance_lbl.configure(
                    text=f"Advance Available: \u20b9{adv:,.2f} — will be auto-applied on save.",
                    text_color="#16A34A")
            else:
                self._advance_lbl.configure(text="", text_color="#555")
        else:
            self._advance_lbl.configure(text="", text_color="#555")

    def _calc_total(self, *_):
        try:
            pv = float(self._pv_var.get() or 0)
            gst = float(self._gst_var.get() or 0)
            self._total_lbl.configure(text=f"\u20b9{pv + gst:,.2f}")
        except ValueError:
            self._total_lbl.configure(text="\u20b9-")

    def _get_vendor_id(self):
        name = self._vendor_var.get()
        if name in self._vendor_names:
            idx = self._vendor_names.index(name)
            return self._vendor_ids[idx]
        return None

    def _submit(self):
        date_str = self._date_entry.get()
        if not date_str:
            messagebox.showerror("Error", "Entry Date is required.")
            return
        valid, err = validate_fy_date(self.db_path, date_str, self.fy_id)
        if not valid:
            messagebox.showerror("Date Out of Range", err)
            return
        vendor_id = self._get_vendor_id()
        if not vendor_id:
            messagebox.showerror("Error", "Select a vendor.")
            return
        try:
            pv = float(self._pv_var.get() or 0)
            if pv <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid purchase value > 0.")
            return
        try:
            gst = float(self._gst_var.get() or 0)
        except ValueError:
            gst = 0

        narration = self._narration_var.get().strip()
        inv = self._inv_var.get().strip()
        inv_date = self._inv_date_entry.get() or None

        if self._editing_id:
            update_purchase(self.db_path, self._editing_id, date_str, vendor_id,
                            inv, pv, gst, narration, invoice_date=inv_date)
            vno = get_purchase(self.db_path, self._editing_id)["voucher_no"]
            self._last_pid = self._editing_id
            self._status_lbl.configure(text=f"Purchase #{vno} updated!")
            self._editing_id = None
            self._save_btn.configure(text="Save Purchase")
        else:
            pid, voucher_no = create_purchase(
                self.db_path, date_str, vendor_id,
                invoice_number=inv, purchase_value=pv,
                gst_amount=gst, narration=narration,
                invoice_date=inv_date
            )
            self._last_pid = pid
            # Auto-apply any advance balance against the new purchase
            advance_applied = apply_advance_to_purchase(self.db_path, pid, vendor_id)
            if advance_applied > 0:
                self._status_lbl.configure(
                    text=f"Purchase #{voucher_no} saved! Advance \u20b9{advance_applied:,.2f} auto-applied.")
            else:
                self._status_lbl.configure(text=f"Purchase #{voucher_no} saved!")

        self._print_btn.configure(state="normal")
        self._clear(keep_status=True)
        self._load_list()

    def load_for_edit(self, purchase_id):
        p = get_purchase(self.db_path, purchase_id)
        if not p:
            return
        self._editing_id = purchase_id
        self._date_entry.set(p["date"])
        inv_date = p.get("invoice_date") or ""
        self._inv_date_entry.set(inv_date)
        self._inv_var.set(p.get("invoice_number") or "")
        self._pv_var.set(str(p["purchase_value"]))
        self._gst_var.set(str(p["gst_amount"]))
        self._narration_var.set(p.get("narration") or "")
        if p.get("vendor_id"):
            idx = next((i for i, vid in enumerate(self._vendor_ids) if vid == p["vendor_id"]), 0)
            if idx > 0:
                self._vendor_menu.set(self._vendor_names[idx])
        self._save_btn.configure(text="Update Purchase")
        self._status_lbl.configure(text=f"Editing Purchase #{p['voucher_no']}", text_color="#D97706")

    def _print_pdf(self):
        if self._last_pid:
            p = get_purchase(self.db_path, self._last_pid)
            if p:
                from database import get_meta
                entity_name = get_meta(self.db_path, "entity_name", "")
                print_purchase_pdf(p, entity_name=entity_name)

    def _clear(self, keep_status=False):
        self._date_entry.set(today_storage())
        self._inv_date_entry.set(today_storage())
        self._inv_var.set("")
        self._pv_var.set("")
        self._gst_var.set("0")
        self._narration_var.set("")
        self._total_lbl.configure(text="\u20b90.00")
        self._vendor_menu.set("-- Select Vendor --")
        self._advance_lbl.configure(text="")
        self._editing_id = None
        self._save_btn.configure(text="Save Purchase")
        if not keep_status:
            self._status_lbl.configure(text="", text_color="#16A34A")

    def _load_list(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        purchases = get_purchases(self.db_path, fy_id=self.fy_id, include_cancelled=True)
        if not purchases:
            ctk.CTkLabel(self._scroll, text="No purchases yet.", text_color="#999").pack(pady=20)
            return
        for i, p in enumerate(reversed(purchases[:60])):
            bg = "#F8FAFF" if i % 2 == 0 else "white"
            is_cancelled = p["status"] == "cancelled"
            row = ctk.CTkFrame(self._scroll, fg_color="#FFF0F0" if is_cancelled else bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            vals = [p["voucher_no"],
                    to_display(p["date"]),
                    to_display(p.get("invoice_date") or "") or "-",
                    (p.get("vendor_name") or "")[:18],
                    p.get("invoice_number") or "-",
                    f"\u20b9{p['purchase_value']:,.2f}",
                    f"\u20b9{p['gst_amount']:,.2f}",
                    f"\u20b9{p['total_value']:,.2f}",
                    f"\u20b9{p['outstanding']:,.2f}"]
            color = "#888" if is_cancelled else "#333"
            for val, width in zip(vals, self._widths):
                ctk.CTkLabel(row, text=str(val)[:18], width=width,
                             font=ctk.CTkFont(size=11), text_color=color).pack(side="left", padx=4, pady=4)
            if not is_cancelled:
                ctk.CTkButton(row, text="Edit", width=46, height=24,
                              fg_color="#6366F1", hover_color="#4F46E5",
                              font=ctk.CTkFont(size=10),
                              command=lambda pid=p["id"]: self.load_for_edit(pid)).pack(side="left", padx=2)
                ctk.CTkButton(row, text="Cancel", width=54, height=24,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=10),
                              command=lambda pid=p["id"], vno=p["voucher_no"]: self._cancel(pid, vno)
                              ).pack(side="left", padx=2)

    def _cancel(self, pid, vno):
        if messagebox.askyesno("Cancel", f"Cancel purchase {vno}?"):
            cancel_purchase(self.db_path, pid)
            self._load_list()

    def refresh(self):
        self._refresh_vendor_ui()
        self._load_list()
