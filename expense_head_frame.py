import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from database import get_expense_heads, create_expense_head, update_expense_head, delete_expense_head, restore_expense_head


class ExpenseHeadFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, **kwargs):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 10))
        ctk.CTkLabel(top, text="Expense Head Master",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(side="left")
        ctk.CTkButton(top, text="+ Add Expense Head", width=150,
                      fg_color="#1B4FD8", hover_color="#1440B0",
                      command=self._open_add).pack(side="right", padx=6)

        fr = ctk.CTkFrame(self, fg_color="transparent")
        fr.pack(fill="x", padx=24, pady=(0, 8))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._load_table())
        ctk.CTkEntry(fr, placeholder_text="Search expense heads...",
                     textvariable=self._search_var, width=260).pack(side="left")
        self._show_inactive_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(fr, text="Show Deleted", variable=self._show_inactive_var,
                        command=self._load_table,
                        font=ctk.CTkFont(size=12)).pack(side="left", padx=(14, 0))

        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(["ID", "Name", "Description"],
                          [60, 240, 400]):
            ctk.CTkLabel(h, text=col, width=w,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        ctk.CTkLabel(h, text="Actions", width=110,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=4, pady=6)

        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._load_table()

    def _load_table(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        show_inactive = self._show_inactive_var.get() if hasattr(self, "_show_inactive_var") else False
        heads = get_expense_heads(self.db_path, search=self._search_var.get(),
                                  include_inactive=show_inactive)
        if not heads:
            ctk.CTkLabel(self._scroll, text="No expense heads defined yet.",
                         text_color="#999").pack(pady=20)
            return
        for i, h in enumerate(heads):
            is_inactive = (h.get("status") or "active") == "inactive"
            bg = "#FEF2F2" if is_inactive else ("#F8FAFF" if i % 2 == 0 else "white")
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            name_display = (h["name"] + (" [Deleted]" if is_inactive else ""))
            for val, width in zip([h["id"], name_display, h.get("description") or "-"],
                                  [60, 240, 400]):
                color = "#9CA3AF" if is_inactive else "#333"
                ctk.CTkLabel(row, text=str(val)[:50], width=width,
                             font=ctk.CTkFont(size=12), text_color=color).pack(side="left", padx=4, pady=5)
            af = ctk.CTkFrame(row, fg_color="transparent")
            af.pack(side="left", padx=4)
            if is_inactive:
                ctk.CTkButton(af, text="Restore", width=62, height=26,
                              fg_color="#16A34A", hover_color="#15803D",
                              font=ctk.CTkFont(size=11),
                              command=lambda eh=h: self._restore(eh)).pack(side="left", padx=2)
            else:
                ctk.CTkButton(af, text="Edit", width=46, height=26,
                              fg_color="#6366F1", hover_color="#4F46E5",
                              font=ctk.CTkFont(size=11),
                              command=lambda eh=h: self._open_edit(eh)).pack(side="left", padx=2)
                ctk.CTkButton(af, text="Del", width=40, height=26,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=11),
                              command=lambda eh=h: self._delete(eh)).pack(side="left", padx=2)

    def _open_add(self):
        ExpenseHeadDialog(self, title="Add Expense Head", on_save=self._save_new)

    def _open_edit(self, head):
        ExpenseHeadDialog(self, title="Edit Expense Head", initial=head,
                          on_save=lambda d: self._save_edit(head["id"], d))

    def _save_new(self, data):
        try:
            create_expense_head(self.db_path, **data)
            self._load_table()
        except ValueError as e:
            messagebox.showerror("Duplicate", str(e))

    def _save_edit(self, head_id, data):
        try:
            update_expense_head(self.db_path, head_id, **data)
            self._load_table()
        except ValueError as e:
            messagebox.showerror("Duplicate", str(e))

    def _delete(self, head):
        if messagebox.askyesno("Delete", f"Delete expense head '{head['name']}'?\n\nIt will be hidden but can be restored later."):
            delete_expense_head(self.db_path, head["id"])
            self._load_table()

    def _restore(self, head):
        restore_expense_head(self.db_path, head["id"])
        self._load_table()

    def refresh(self):
        self._load_table()


class ExpenseHeadDialog(ctk.CTkToplevel):
    def __init__(self, master, title, on_save, initial=None):
        super().__init__(master)
        self.title(title)
        self.geometry("480x240")
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save
        self.initial = initial or {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Name *",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=12, sticky="w")
        self._name = tk.StringVar(value=self.initial.get("name", "") or "")
        ctk.CTkEntry(self, textvariable=self._name).grid(row=0, column=1, padx=20, pady=12, sticky="ew")

        ctk.CTkLabel(self, text="Description").grid(row=1, column=0, padx=20, pady=12, sticky="w")
        self._desc = tk.StringVar(value=self.initial.get("description", "") or "")
        ctk.CTkEntry(self, textvariable=self._desc).grid(row=1, column=1, padx=20, pady=12, sticky="ew")

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.grid(row=2, column=0, columnspan=2, pady=16)
        ctk.CTkButton(btn, text="Cancel", fg_color="#6B7280",
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn, text="Save", fg_color="#1B4FD8",
                      command=self._save).pack(side="left", padx=8)

    def _save(self):
        name = self._name.get().strip()
        if not name:
            messagebox.showerror("Error", "Expense head name is required.", parent=self)
            return
        self.on_save({"name": name, "description": self._desc.get().strip()})
        self.destroy()
