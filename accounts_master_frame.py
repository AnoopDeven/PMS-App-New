import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import openpyxl
from database import get_accounts, create_account, update_account, delete_account, restore_account

COLS = ["ID", "Name", "Type", "Bank Name", "Acct No."]
COL_KEYS = ["id", "name", "type", "bank_name", "account_number"]
COL_WIDTHS = [50, 200, 90, 180, 160]


class AccountsMasterFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, **kwargs):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 10))
        ctk.CTkLabel(top, text="Cash / Bank Master",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(side="left")
        ctk.CTkButton(top, text="Export Excel", width=120, fg_color="#16A34A",
                      hover_color="#15803D", command=self._export_excel).pack(side="right", padx=6)
        ctk.CTkButton(top, text="+ Add Account", width=130, fg_color="#1B4FD8",
                      hover_color="#1440B0", command=self._open_add).pack(side="right", padx=6)

        fr = ctk.CTkFrame(self, fg_color="transparent")
        fr.pack(fill="x", padx=24, pady=(0, 8))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._load_table())
        ctk.CTkEntry(fr, placeholder_text="Search accounts...",
                     textvariable=self._search_var, width=240).pack(side="left", padx=(0, 12))
        self._type_var = tk.StringVar(value="All")
        ctk.CTkOptionMenu(fr, values=["All", "cash", "bank"],
                          variable=self._type_var,
                          command=lambda *a: self._load_table()).pack(side="left")
        self._show_inactive_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(fr, text="Show Deleted", variable=self._show_inactive_var,
                        command=self._load_table,
                        font=ctk.CTkFont(size=12)).pack(side="left", padx=(14, 0))

        note = ctk.CTkLabel(self, text="Cash/Bank accounts track transactions only. No opening balance or carry-forward.",
                            font=ctk.CTkFont(size=11), text_color="#666")
        note.pack(anchor="w", padx=26, pady=(0, 4))

        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(COLS, COL_WIDTHS):
            ctk.CTkLabel(h, text=col, width=w,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        ctk.CTkLabel(h, text="Actions", width=100,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=4, pady=6)

        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._load_table()

    def _load_table(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        tf = self._type_var.get() if hasattr(self, "_type_var") else "All"
        show_inactive = self._show_inactive_var.get() if hasattr(self, "_show_inactive_var") else False
        accounts = get_accounts(self.db_path, search=self._search_var.get(),
                                type_filter=None if tf == "All" else tf,
                                include_inactive=show_inactive)
        if not accounts:
            ctk.CTkLabel(self._scroll, text="No accounts found.",
                         text_color="#999").pack(pady=20)
            return
        for i, a in enumerate(accounts):
            is_inactive = (a.get("status") or "active") == "inactive"
            bg = "#FEF2F2" if is_inactive else ("#F8FAFF" if i % 2 == 0 else "white")
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            for key, width in zip(COL_KEYS, COL_WIDTHS):
                raw_val = a.get(key, "") or ""
                val = (str(raw_val) + (" [Deleted]" if is_inactive and key == "name" else ""))
                color = "#9CA3AF" if is_inactive else "#333"
                ctk.CTkLabel(row, text=str(val)[:30], width=width,
                             font=ctk.CTkFont(size=12), text_color=color).pack(side="left", padx=4, pady=5)
            af = ctk.CTkFrame(row, fg_color="transparent")
            af.pack(side="left", padx=4)
            if is_inactive:
                ctk.CTkButton(af, text="Restore", width=62, height=26,
                              fg_color="#16A34A", hover_color="#15803D",
                              font=ctk.CTkFont(size=11),
                              command=lambda acc=a: self._restore(acc)).pack(side="left", padx=2)
            else:
                ctk.CTkButton(af, text="Edit", width=46, height=26,
                              fg_color="#6366F1", hover_color="#4F46E5",
                              font=ctk.CTkFont(size=11),
                              command=lambda acc=a: self._open_edit(acc)).pack(side="left", padx=2)
                ctk.CTkButton(af, text="Del", width=40, height=26,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=11),
                              command=lambda acc=a: self._delete(acc)).pack(side="left", padx=2)

    def _open_add(self):
        AccountDialog(self, title="Add Cash/Bank Account", on_save=self._save_new)

    def _open_edit(self, acc):
        AccountDialog(self, title="Edit Cash/Bank Account", initial=acc,
                      on_save=lambda d: self._save_edit(acc["id"], d))

    def _save_new(self, data):
        try:
            create_account(self.db_path, **data)
            self._load_table()
        except ValueError as e:
            messagebox.showerror("Duplicate", str(e))

    def _save_edit(self, account_id, data):
        try:
            update_account(self.db_path, account_id, **data)
            self._load_table()
        except ValueError as e:
            messagebox.showerror("Duplicate", str(e))

    def _delete(self, acc):
        if messagebox.askyesno("Delete", f"Delete account '{acc['name']}'?\n\nThe account will be hidden but can be restored later."):
            delete_account(self.db_path, acc["id"])
            self._load_table()

    def _restore(self, acc):
        restore_account(self.db_path, acc["id"])
        self._load_table()

    def _export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel", "*.xlsx")],
                                            title="Save Accounts as Excel")
        if not path:
            return
        accounts = get_accounts(self.db_path)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Cash-Bank"
        ws.append(COLS)
        for a in accounts:
            ws.append([a.get(k, "") or "" for k in COL_KEYS])
        wb.save(path)
        messagebox.showinfo("Exported", f"Accounts exported:\n{path}")

    def refresh(self):
        self._load_table()


class AccountDialog(ctk.CTkToplevel):
    def __init__(self, master, title, on_save, initial=None):
        super().__init__(master)
        self.title(title)
        self.geometry("440x300")
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save
        self.initial = initial or {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Account Name *",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=8, sticky="w")
        self._name = tk.StringVar(value=self.initial.get("name", "") or "")
        ctk.CTkEntry(self, textvariable=self._name).grid(row=0, column=1, padx=20, pady=8, sticky="ew")

        ctk.CTkLabel(self, text="Type *",
                     font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=8, sticky="w")
        self._type = tk.StringVar(value=self.initial.get("type", "cash") or "cash")
        ctk.CTkOptionMenu(self, values=["cash", "bank"],
                          variable=self._type,
                          command=self._toggle_bank).grid(row=1, column=1, padx=20, pady=8, sticky="w")

        ctk.CTkLabel(self, text="Bank Name").grid(row=2, column=0, padx=20, pady=8, sticky="w")
        self._bank = tk.StringVar(value=self.initial.get("bank_name", "") or "")
        self._bank_entry = ctk.CTkEntry(self, textvariable=self._bank)
        self._bank_entry.grid(row=2, column=1, padx=20, pady=8, sticky="ew")

        ctk.CTkLabel(self, text="Account Number").grid(row=3, column=0, padx=20, pady=8, sticky="w")
        self._acct_no = tk.StringVar(value=self.initial.get("account_number", "") or "")
        self._acct_entry = ctk.CTkEntry(self, textvariable=self._acct_no)
        self._acct_entry.grid(row=3, column=1, padx=20, pady=8, sticky="ew")

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.grid(row=4, column=0, columnspan=2, pady=16)
        ctk.CTkButton(btn, text="Cancel", fg_color="#6B7280",
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn, text="Save", fg_color="#1B4FD8",
                      command=self._save).pack(side="left", padx=8)

        self._toggle_bank(self._type.get())

    def _toggle_bank(self, val):
        state = "normal" if val == "bank" else "disabled"
        self._bank_entry.configure(state=state)
        self._acct_entry.configure(state=state)

    def _save(self):
        name = self._name.get().strip()
        if not name:
            messagebox.showerror("Error", "Account name is required.", parent=self)
            return
        data = {
            "name": name, "acc_type": self._type.get(),
            "bank_name": self._bank.get().strip(),
            "account_number": self._acct_no.get().strip(),
            "opening_balance": 0,
        }
        self.on_save(data)
        self.destroy()
