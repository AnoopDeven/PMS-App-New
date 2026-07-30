import tkinter as tk
import customtkinter as ctk
from database import get_financial_years, get_active_fy, set_active_fy

NAV_ITEMS = [
    ("Dashboard",      "dashboard"),
    ("Payment",        "voucher"),
    ("Purchase",       "purchase"),
    ("Credit Note",    "credit_note"),
    ("Debit Note",     "debit_note"),
    ("Expense",        "expense"),
    ("Day Book",       "daybook"),
    ("Ledger",         "ledger"),
    ("Balance",        "balance"),
    ("Vendors",        "vendors"),
    ("Cash/Bank",      "accounts"),
    ("Expense Heads",  "expense_heads"),
]

SIDEBAR_W = 210


class MainWindow(ctk.CTkFrame):
    def __init__(self, master, entity_name, db_path, on_back):
        super().__init__(master, fg_color="#F4F6FB")
        self.pack(fill="both", expand=True)
        self.entity_name = entity_name
        self.db_path = db_path
        self.on_back = on_back
        self._page_frames = {}
        self._active_fy = get_active_fy(db_path)
        self._build_ui()
        self._show_page("dashboard")

    def get_fy_id(self):
        if self._active_fy:
            return self._active_fy["id"]
        return None

    def _build_ui(self):
        sidebar = ctk.CTkFrame(self, fg_color="#1B2B6B", width=SIDEBAR_W, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="PMS",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="white").pack(pady=(20, 2))
        ctk.CTkLabel(sidebar, text=self.entity_name,
                     font=ctk.CTkFont(size=11), text_color="#8BAFD4",
                     wraplength=SIDEBAR_W - 20).pack(pady=(0, 4))

        fys = get_financial_years(self.db_path)
        fy_labels = [f["label"] for f in fys]
        active = self._active_fy
        active_label = active["label"] if active else (fy_labels[0] if fy_labels else "No FY")

        self._fy_var = tk.StringVar(value=active_label)
        if fy_labels:
            fy_menu = ctk.CTkOptionMenu(sidebar, values=fy_labels,
                                         variable=self._fy_var,
                                         fg_color="#243A8A", button_color="#1B4FD8",
                                         text_color="white", font=ctk.CTkFont(size=11),
                                         command=self._change_fy)
            fy_menu.pack(fill="x", padx=12, pady=(0, 14))

        self._nav_buttons = {}
        for label, key in NAV_ITEMS:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w",
                fg_color="transparent", hover_color="#243A8A",
                text_color="white", font=ctk.CTkFont(size=13),
                height=38, corner_radius=8,
                command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[key] = btn

        ctk.CTkButton(sidebar, text="\u2190 Switch Entity",
                      fg_color="transparent", hover_color="#243A8A",
                      text_color="#8BAFD4", font=ctk.CTkFont(size=12),
                      height=34, command=self.on_back).pack(side="bottom", fill="x", padx=12, pady=14)

        self.content = ctk.CTkFrame(self, fg_color="#F4F6FB", corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

    def _change_fy(self, label):
        fys = get_financial_years(self.db_path)
        for fy in fys:
            if fy["label"] == label:
                set_active_fy(self.db_path, fy["id"])
                self._active_fy = fy
                self._page_frames.clear()
                self._show_page(self._active_key if hasattr(self, "_active_key") else "dashboard")
                break

    def _show_page(self, key):
        self._active_key = key
        for k, btn in self._nav_buttons.items():
            btn.configure(fg_color="#1B4FD8" if k == key else "transparent")
        for frame in self.content.winfo_children():
            frame.pack_forget()
        if key not in self._page_frames:
            self._page_frames[key] = self._make_frame(key)
        frame = self._page_frames[key]
        frame.pack(fill="both", expand=True)
        if hasattr(frame, "refresh"):
            frame.refresh()

    def _make_frame(self, key):
        from dashboard_frame import DashboardFrame
        from voucher_entry_frame import VoucherEntryFrame
        from purchase_voucher_frame import PurchaseVoucherFrame
        from credit_debit_note_frame import CreditDebitNoteFrame
        from daybook_frame import DaybookFrame
        from ledger_frame import LedgerFrame
        from balance_frame import BalanceFrame
        from register_frame import RegisterFrame
        from vendor_master_frame import VendorMasterFrame
        from accounts_master_frame import AccountsMasterFrame
        from expense_head_frame import ExpenseHeadFrame
        from expense_frame import ExpenseFrame
        from report_frame import ReportFrame
        kw = dict(master=self.content, db_path=self.db_path, fy_id=self.get_fy_id())
        master_kw = dict(master=self.content, db_path=self.db_path)
        mapping = {
            "dashboard":     (DashboardFrame, kw),
            "voucher":       (VoucherEntryFrame, kw),
            "purchase":      (PurchaseVoucherFrame, kw),
            "credit_note":   (CreditDebitNoteFrame, {**kw, "note_type": "credit"}),
            "debit_note":    (CreditDebitNoteFrame, {**kw, "note_type": "debit"}),
            "expense":       (ExpenseFrame, kw),   # not in sidebar; reached via Day Book edit
            "daybook":       (DaybookFrame, kw),
            "ledger":        (LedgerFrame, kw),
            "balance":       (BalanceFrame, kw),
            "register":      (RegisterFrame, kw),
            "reports":       (ReportFrame, kw),
            "vendors":       (VendorMasterFrame, master_kw),
            "accounts":      (AccountsMasterFrame, master_kw),
            "expense_heads": (ExpenseHeadFrame, master_kw),
        }
        cls, kwargs = mapping[key]
        return cls(**kwargs)
