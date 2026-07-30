import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from date_utils import DateEntry, to_display, today_storage
from database import (get_expense_heads, get_accounts, create_expense, get_expenses,
                      cancel_expense, validate_fy_date, get_expense, update_expense)
from searchable_combo import SearchableComboBox
from pdf_generator import print_expense_pdf


class ExpenseFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self._edit_id = None
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self._edit_id = None

        self._title_lbl = ctk.CTkLabel(self, text="Expense Entry",
                                        font=ctk.CTkFont(size=22, weight="bold"),
                                        text_color="#1B2B6B")
        self._title_lbl.pack(anchor="w", padx=24, pady=(20, 8))

        form = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        form.pack(fill="x", padx=24, pady=(0, 12))
        form.grid_columnconfigure((1, 3), weight=1)
        kw = {"padx": 14, "pady": 8}

        ctk.CTkLabel(form, text="Date *", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", **kw)
        self._date_entry = DateEntry(form)
        self._date_entry.grid(row=0, column=1, sticky="w", **kw)

        ctk.CTkLabel(form, text="Amount *", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=2, sticky="w", **kw)
        self._amount_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._amount_var,
                     placeholder_text="0.00").grid(row=0, column=3, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Expense Head *", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", **kw)
        self._head_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._head_frame.grid(row=1, column=1, columnspan=3, sticky="ew", **kw)
        self._head_menu = None
        self._head_names = []
        self._head_ids = []
        self._refresh_head_ui()

        ctk.CTkLabel(form, text="Paid From (Account) *", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, sticky="w", **kw)
        accounts = get_accounts(self.db_path)
        self._acc_names = [a["name"] for a in accounts]
        self._acc_ids = [a["id"] for a in accounts]
        self._acc_menu = SearchableComboBox(form, values=self._acc_names, width=280)
        self._acc_menu.grid(row=2, column=1, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Payment Mode *", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=2, sticky="w", **kw)
        self._pm_var = tk.StringVar(value="Cash")
        ctk.CTkOptionMenu(form, values=["Cash", "Cheque", "NEFT", "RTGS", "UPI", "Other"],
                          variable=self._pm_var, width=160).grid(row=2, column=3, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Narration").grid(row=3, column=0, sticky="w", **kw)
        self._narration_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._narration_var).grid(
            row=3, column=1, columnspan=3, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Prepared By").grid(row=4, column=0, sticky="w", **kw)
        self._prepared_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._prepared_var,
                     placeholder_text="Name").grid(row=4, column=1, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Processed By").grid(row=4, column=2, sticky="w", **kw)
        self._processed_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._processed_var,
                     placeholder_text="Name").grid(row=4, column=3, sticky="ew", **kw)

        ctk.CTkLabel(form, text="Authorized By").grid(row=5, column=0, sticky="w", **kw)
        self._authorized_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._authorized_var,
                     placeholder_text="Name").grid(row=5, column=1, sticky="ew", **kw)

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.grid(row=6, column=0, columnspan=4, pady=14)
        ctk.CTkButton(btn_row, text="Clear", width=90, fg_color="#6B7280",
                      command=self._clear).pack(side="left", padx=8)
        self._save_btn = ctk.CTkButton(btn_row, text="Save Expense", width=130,
                                        fg_color="#1B4FD8", hover_color="#1440B0",
                                        command=self._submit)
        self._save_btn.pack(side="left", padx=8)

        self._status_lbl = ctk.CTkLabel(form, text="",
                                         font=ctk.CTkFont(size=13, weight="bold"),
                                         text_color="#16A34A")
        self._status_lbl.grid(row=7, column=0, columnspan=4, pady=4)

        ctk.CTkLabel(self, text="Recent Expenses",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=26, pady=(4, 4))
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        headers = ["Voucher No", "Date", "Expense Head", "Account", "Amount", "Narration"]
        widths = [90, 100, 190, 140, 110, 220]
        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(headers, widths):
            ctk.CTkLabel(h, text=col, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        ctk.CTkLabel(h, text="Actions", width=130,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._widths = widths
        self._load_list()

    def _refresh_head_ui(self):
        for w in self._head_frame.winfo_children():
            w.destroy()
        heads = get_expense_heads(self.db_path)
        self._head_names = [h["name"] for h in heads]
        self._head_ids = [h["id"] for h in heads]
        self._head_menu = SearchableComboBox(self._head_frame, values=self._head_names, width=280)
        self._head_menu.pack(side="left")
        ctk.CTkButton(self._head_frame, text="Refresh", width=70, height=28,
                      fg_color="#6B7280", font=ctk.CTkFont(size=11),
                      command=self._refresh_head_ui).pack(side="left", padx=6)

    def _get_head_id(self):
        name = self._head_menu.get() if self._head_menu else ""
        if name and name in self._head_names:
            return self._head_ids[self._head_names.index(name)]
        return None

    def _get_acc_id(self):
        name = self._acc_menu.get()
        if name and name in self._acc_names:
            return self._acc_ids[self._acc_names.index(name)]
        return None

    def _submit(self):
        date_str = self._date_entry.get()
        if not date_str:
            messagebox.showerror("Error", "Date is required.")
            return
        valid, err = validate_fy_date(self.db_path, date_str, self.fy_id)
        if not valid:
            messagebox.showerror("Date Out of Range", err)
            return
        head_id = self._get_head_id()
        if not head_id:
            messagebox.showerror("Error", "Select an Expense Head.")
            return
        acc_id = self._get_acc_id()
        if not acc_id:
            messagebox.showerror("Error", "Select a Paid From account.")
            return
        try:
            amount = float(self._amount_var.get() or 0)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid amount > 0.")
            return
        narration = self._narration_var.get().strip()
        payment_mode = self._pm_var.get()
        prepared_by = self._prepared_var.get().strip()
        processed_by = self._processed_var.get().strip()
        authorized_by = self._authorized_var.get().strip()

        if self._edit_id:
            update_expense(self.db_path, self._edit_id, date_str, head_id, acc_id, amount,
                           narration, payment_mode, prepared_by, processed_by, authorized_by)
            exp = get_expense(self.db_path, self._edit_id)
            vno = exp["voucher_no"] if exp else str(self._edit_id)
            self._status_lbl.configure(text=f"Expense #{vno} updated!", text_color="#16A34A")
            self._edit_id = None
            self._title_lbl.configure(text="Expense Entry")
            self._save_btn.configure(text="Save Expense")
        else:
            eid, vno = create_expense(self.db_path, date_str, head_id, acc_id, amount,
                                      narration, payment_mode, prepared_by, processed_by, authorized_by)
            self._status_lbl.configure(text=f"Expense #{vno} saved!", text_color="#16A34A")
        self._clear(keep_status=True)
        self._load_list()

    def load_for_edit(self, expense_id):
        exp = get_expense(self.db_path, expense_id)
        if not exp:
            messagebox.showerror("Error", f"Expense #{expense_id} not found.")
            return
        self._edit_id = expense_id
        self._title_lbl.configure(text=f"Edit Expense — {exp['voucher_no']}")
        self._save_btn.configure(text="Update Expense")
        self._date_entry.set(exp["date"])
        self._amount_var.set(str(exp["amount"]))
        self._narration_var.set(exp.get("narration") or "")
        self._pm_var.set(exp.get("payment_mode") or "Cash")
        self._prepared_var.set(exp.get("prepared_by") or "")
        self._processed_var.set(exp.get("processed_by") or "")
        self._authorized_var.set(exp.get("authorized_by") or "")
        head_name = exp.get("expense_head_name") or ""
        acc_name = exp.get("account_name") or ""
        if self._head_menu:
            self._head_menu.set(head_name)
        self._acc_menu.set(acc_name)
        self._status_lbl.configure(text="")

    def _clear(self, keep_status=False):
        self._edit_id = None
        self._title_lbl.configure(text="Expense Entry")
        self._save_btn.configure(text="Save Expense")
        self._date_entry.set(today_storage())
        self._amount_var.set("")
        self._narration_var.set("")
        self._pm_var.set("Cash")
        self._prepared_var.set("")
        self._processed_var.set("")
        self._authorized_var.set("")
        if self._head_menu:
            self._head_menu.set("")
        self._acc_menu.set("")
        if not keep_status:
            self._status_lbl.configure(text="")

    def _load_list(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        expenses = get_expenses(self.db_path, fy_id=self.fy_id, include_cancelled=True)
        if not expenses:
            ctk.CTkLabel(self._scroll, text="No expenses recorded yet.",
                         text_color="#999").pack(pady=20)
            return
        for i, e in enumerate(reversed(expenses[:60])):
            bg = "#F8FAFF" if i % 2 == 0 else "white"
            is_cancelled = e["status"] == "cancelled"
            row = ctk.CTkFrame(self._scroll, fg_color="#FFF0F0" if is_cancelled else bg,
                               corner_radius=4)
            row.pack(fill="x", pady=1)
            vals = [e["voucher_no"], to_display(e["date"]),
                    (e.get("expense_head_name") or "-")[:24],
                    (e.get("account_name") or "-")[:18],
                    f"\u20b9{e['amount']:,.2f}",
                    (e.get("narration") or "-")[:30]]
            color = "#888" if is_cancelled else "#333"
            for val, width in zip(vals, self._widths):
                ctk.CTkLabel(row, text=str(val), width=width,
                             font=ctk.CTkFont(size=11), text_color=color).pack(side="left", padx=4, pady=4)
            if not is_cancelled:
                ctk.CTkButton(row, text="Edit", width=50, height=24,
                              fg_color="#6366F1", hover_color="#4F46E5",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"]: self.load_for_edit(eid)
                              ).pack(side="left", padx=2)
                ctk.CTkButton(row, text="Print", width=55, height=24,
                              fg_color="#0891B2", hover_color="#0E7490",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"]: self._print(eid)
                              ).pack(side="left", padx=2)
                ctk.CTkButton(row, text="Cancel", width=60, height=24,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"], vno=e["voucher_no"]: self._cancel(eid, vno)
                              ).pack(side="left", padx=2)

    def _print(self, expense_id):
        exp = get_expense(self.db_path, expense_id)
        if not exp:
            messagebox.showerror("Error", "Expense record not found.")
            return
        print_expense_pdf(dict(exp))

    def _cancel(self, eid, vno):
        if messagebox.askyesno("Cancel", f"Cancel expense {vno}?"):
            cancel_expense(self.db_path, eid)
            self._load_list()

    def refresh(self):
        self._refresh_head_ui()
        accounts = get_accounts(self.db_path)
        self._acc_names = [a["name"] for a in accounts]
        self._acc_ids = [a["id"] for a in accounts]
        self._acc_menu.configure(values=self._acc_names)
        self._load_list()
