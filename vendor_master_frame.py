import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import openpyxl
from database import get_vendors, create_vendor, update_vendor, delete_vendor, restore_vendor

COLS = ["ID", "Name", "Opening Bal.", "OB Type", "Phone", "Email"]
COL_KEYS = ["id", "name", "opening_balance", "_ob_type", "phone", "email"]
COL_WIDTHS = [45, 160, 110, 90, 110, 150]


def _ob_type_from_value(ob):
    """Return display type string from stored signed opening balance."""
    if ob is None or ob == 0:
        return "—"
    return "Credit (Payable)" if ob > 0 else "Debit (Advance)"


class VendorMasterFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, **kwargs):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 10))
        ctk.CTkLabel(top, text="Vendor Master",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(side="left")
        ctk.CTkButton(top, text="Export Excel", width=120, fg_color="#16A34A",
                      hover_color="#15803D", command=self._export_excel).pack(side="right", padx=6)
        ctk.CTkButton(top, text="+ Add Vendor", width=120, fg_color="#1B4FD8",
                      hover_color="#1440B0", command=self._open_add).pack(side="right", padx=6)

        fr = ctk.CTkFrame(self, fg_color="transparent")
        fr.pack(fill="x", padx=24, pady=(0, 8))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._load_table())
        ctk.CTkEntry(fr, placeholder_text="Search vendors...",
                     textvariable=self._search_var, width=240).pack(side="left", padx=(0, 10))
        self._cat_var = tk.StringVar(value="All")
        ctk.CTkOptionMenu(fr, values=["All", "creditor"],
                          variable=self._cat_var,
                          command=lambda *a: self._load_table()).pack(side="left")
        self._show_inactive_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(fr, text="Show Deleted", variable=self._show_inactive_var,
                        command=self._load_table,
                        font=ctk.CTkFont(size=12)).pack(side="left", padx=(14, 0))

        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(COLS, COL_WIDTHS):
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
        cat = self._cat_var.get() if hasattr(self, "_cat_var") else "All"
        show_inactive = self._show_inactive_var.get() if hasattr(self, "_show_inactive_var") else False
        vendors = get_vendors(self.db_path, search=self._search_var.get(),
                              category=None if cat == "All" else cat,
                              include_inactive=show_inactive)
        if not vendors:
            ctk.CTkLabel(self._scroll, text="No vendors found.",
                         text_color="#999").pack(pady=20)
            return
        for i, v in enumerate(vendors):
            is_inactive = (v.get("status") or "active") == "inactive"
            bg = "#FEF2F2" if is_inactive else ("#F8FAFF" if i % 2 == 0 else "white")
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            ob = float(v.get("opening_balance") or 0)
            ob_type = _ob_type_from_value(ob)
            display_vals = {
                "id": v["id"],
                "name": (v["name"] or "") + (" [Deleted]" if is_inactive else ""),
                "opening_balance": f"\u20b9{abs(ob):,.2f}",
                "_ob_type": ob_type,
                "phone": v.get("phone") or "",
                "email": v.get("email") or "",
            }
            for key, width in zip(COL_KEYS, COL_WIDTHS):
                val = display_vals.get(key, "")
                if is_inactive:
                    color = "#9CA3AF"
                elif key == "opening_balance":
                    color = "#EF4444" if ob < 0 else ("#16A34A" if ob > 0 else "#333")
                elif key == "_ob_type":
                    color = "#EF4444" if ob < 0 else ("#1B4FD8" if ob > 0 else "#999")
                else:
                    color = "#333"
                ctk.CTkLabel(row, text=str(val)[:22], width=width,
                             font=ctk.CTkFont(size=12), text_color=color).pack(side="left", padx=4, pady=5)
            af = ctk.CTkFrame(row, fg_color="transparent")
            af.pack(side="left", padx=4)
            if is_inactive:
                ctk.CTkButton(af, text="Restore", width=62, height=26,
                              fg_color="#16A34A", hover_color="#15803D",
                              font=ctk.CTkFont(size=11),
                              command=lambda vendor=v: self._restore(vendor)).pack(side="left", padx=2)
            else:
                ctk.CTkButton(af, text="Edit", width=46, height=26,
                              fg_color="#6366F1", hover_color="#4F46E5",
                              font=ctk.CTkFont(size=11),
                              command=lambda vendor=v: self._open_edit(vendor)).pack(side="left", padx=2)
                ctk.CTkButton(af, text="Del", width=40, height=26,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=11),
                              command=lambda vendor=v: self._delete(vendor)).pack(side="left", padx=2)

    def _open_add(self):
        VendorDialog(self, title="Add Vendor", on_save=self._save_new)

    def _open_edit(self, vendor):
        VendorDialog(self, title="Edit Vendor", initial=vendor,
                     on_save=lambda d: self._save_edit(vendor["id"], d))

    def _save_new(self, data):
        try:
            create_vendor(self.db_path, **data)
            self._load_table()
        except ValueError as e:
            messagebox.showerror("Duplicate", str(e))

    def _save_edit(self, vid, data):
        try:
            update_vendor(self.db_path, vid, **data)
            self._load_table()
        except ValueError as e:
            messagebox.showerror("Duplicate", str(e))

    def _delete(self, vendor):
        if messagebox.askyesno("Delete", f"Delete vendor '{vendor['name']}'?\n\nThe vendor will be hidden but can be restored later."):
            delete_vendor(self.db_path, vendor["id"])
            self._load_table()

    def _restore(self, vendor):
        restore_vendor(self.db_path, vendor["id"])
        self._load_table()

    def _export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel", "*.xlsx")],
                                            title="Save Vendors as Excel")
        if not path:
            return
        vendors = get_vendors(self.db_path)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Vendors"
        export_cols = ["ID", "Name", "Opening Balance", "OB Type", "Phone", "Email",
                       "Contact Person", "Address"]
        ws.append(export_cols)
        for v in vendors:
            ob = float(v.get("opening_balance") or 0)
            ws.append([v["id"], v["name"], abs(ob), _ob_type_from_value(ob),
                       v.get("phone") or "", v.get("email") or "",
                       v.get("contact_person") or "", v.get("address") or ""])
        wb.save(path)
        messagebox.showinfo("Exported", f"Vendors exported:\n{path}")

    def refresh(self):
        self._load_table()


class VendorDialog(ctk.CTkToplevel):
    def __init__(self, master, title, on_save, initial=None):
        super().__init__(master)
        self.title(title)
        self.geometry("520x500")
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save
        self.initial = initial or {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)

        # Name
        ctk.CTkLabel(self, text="Vendor Name *",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self._name = tk.StringVar(value=self.initial.get("name", "") or "")
        ctk.CTkEntry(self, textvariable=self._name, width=300).grid(row=0, column=1, padx=20, pady=10, sticky="ew")

        # Opening Balance amount
        ctk.CTkLabel(self, text="Opening Balance",
                     font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        ob_val = self.initial.get("opening_balance", 0) or 0
        self._ob_amount = tk.StringVar(value=str(abs(float(ob_val))))
        ob_frame = ctk.CTkFrame(self, fg_color="transparent")
        ob_frame.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        ctk.CTkEntry(ob_frame, textvariable=self._ob_amount, width=180,
                     placeholder_text="0.00").pack(side="left")
        ctk.CTkLabel(ob_frame, text="\u20b9", text_color="#555",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(6, 0))

        # Opening Balance Type
        ctk.CTkLabel(self, text="OB Type *",
                     font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=6, sticky="w")
        # Determine initial type from sign
        init_type = "Debit (Advance)" if float(ob_val) < 0 else "Credit (Payable)"
        self._ob_type = tk.StringVar(value=init_type)
        ob_type_frame = ctk.CTkFrame(self, fg_color="#F0F4FF", corner_radius=8)
        ob_type_frame.grid(row=2, column=1, padx=20, pady=6, sticky="w")
        for lbl in ["Credit (Payable)", "Debit (Advance)"]:
            ctk.CTkRadioButton(ob_type_frame, text=lbl, variable=self._ob_type, value=lbl,
                               font=ctk.CTkFont(size=12)).pack(side="left", padx=14, pady=8)

        ob_hint = ctk.CTkFrame(self, fg_color="transparent")
        ob_hint.grid(row=3, column=1, padx=20, sticky="w")
        ctk.CTkLabel(ob_hint,
                     text="Credit = vendor owes us payable  |  Debit = advance already given",
                     font=ctk.CTkFont(size=10), text_color="#888").pack()

        # Contact Person
        ctk.CTkLabel(self, text="Contact Person").grid(row=4, column=0, padx=20, pady=8, sticky="w")
        self._contact = tk.StringVar(value=self.initial.get("contact_person", "") or "")
        ctk.CTkEntry(self, textvariable=self._contact).grid(row=4, column=1, padx=20, pady=8, sticky="ew")

        # Phone
        ctk.CTkLabel(self, text="Phone").grid(row=5, column=0, padx=20, pady=8, sticky="w")
        self._phone = tk.StringVar(value=self.initial.get("phone", "") or "")
        ctk.CTkEntry(self, textvariable=self._phone).grid(row=5, column=1, padx=20, pady=8, sticky="ew")

        # Email
        ctk.CTkLabel(self, text="Email").grid(row=6, column=0, padx=20, pady=8, sticky="w")
        self._email = tk.StringVar(value=self.initial.get("email", "") or "")
        ctk.CTkEntry(self, textvariable=self._email).grid(row=6, column=1, padx=20, pady=8, sticky="ew")

        # Address
        ctk.CTkLabel(self, text="Address").grid(row=7, column=0, padx=20, pady=8, sticky="w")
        self._address = tk.StringVar(value=self.initial.get("address", "") or "")
        ctk.CTkEntry(self, textvariable=self._address).grid(row=7, column=1, padx=20, pady=8, sticky="ew")

        # Buttons
        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.grid(row=8, column=0, columnspan=2, pady=16)
        ctk.CTkButton(btn, text="Cancel", fg_color="#6B7280",
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn, text="Save", fg_color="#1B4FD8",
                      command=self._save).pack(side="left", padx=8)

    def _save(self):
        name = self._name.get().strip()
        if not name:
            messagebox.showerror("Error", "Vendor name is required.", parent=self)
            return

        ob_str = self._ob_amount.get().strip()
        try:
            ob_abs = float(ob_str) if ob_str else 0.0
            if ob_abs < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Opening balance must be a valid positive number.", parent=self)
            return

        ob_type = self._ob_type.get()
        if not ob_type:
            messagebox.showerror("Error", "Please select Opening Balance type.", parent=self)
            return

        # Store as signed: Credit = positive (payable), Debit = negative (advance)
        ob_signed = ob_abs if ob_type == "Credit (Payable)" else -ob_abs

        data = {
            "name": name,
            "category": "creditor",
            "opening_balance": ob_signed,
            "contact_person": self._contact.get().strip(),
            "phone": self._phone.get().strip(),
            "email": self._email.get().strip(),
            "address": self._address.get().strip(),
        }
        self.on_save(data)
        self.destroy()
