import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import openpyxl
from date_utils import DateEntry, to_display
from database import (get_vendors, get_accounts, get_expense_heads,
                      get_vendor_ledger, get_account_ledger,
                      get_expense_ledger, get_vendor_balance,
                      get_vendor_outstanding_report, get_voucher, get_expense)
from searchable_combo import SearchableComboBox


def fmt(v):
    try:
        return f"\u20b9{float(v):,.2f}"
    except Exception:
        return str(v)


class LedgerFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self._entries = []
        self._out_rows = []
        self._ledger_name = ""
        self._ltype_val = "vendor"
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        ctk.CTkLabel(self, text="Ledger",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=24, pady=(20, 8))

        f = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        f.pack(fill="x", padx=24, pady=(0, 8))
        r1 = ctk.CTkFrame(f, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(r1, text="Type").pack(side="left", padx=(0, 4))
        self._ltype = tk.StringVar(value="vendor")
        ctk.CTkOptionMenu(r1, values=["vendor", "outstanding", "account", "expense"],
                          variable=self._ltype,
                          command=self._on_type_change, width=130).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(r1, text="Select").pack(side="left", padx=(0, 4))
        self._names = []
        self._ids = [None]
        self._sel_menu = SearchableComboBox(r1, values=self._names, width=240)
        self._sel_menu.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(r1, text="From").pack(side="left", padx=(0, 4))
        self._df_entry = DateEntry(r1, initial_date="")
        self._df_entry.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(r1, text="To").pack(side="left", padx=(0, 4))
        self._dt_entry = DateEntry(r1, initial_date="")
        self._dt_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(r1, text="Show", width=80, fg_color="#1B4FD8",
                      command=self._load).pack(side="left", padx=4)
        ctk.CTkButton(r1, text="Clear Dates", width=90, fg_color="#6B7280",
                      command=self._clear_dates).pack(side="left", padx=4)
        ctk.CTkButton(r1, text="Export Excel", width=100, fg_color="#16A34A",
                      command=self._export).pack(side="left", padx=4)
        ctk.CTkButton(r1, text="Print PDF", width=90, fg_color="#7C3AED",
                      command=self._print_ledger).pack(side="left", padx=4)

        self._payable_card = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        self._payable_card.pack(fill="x", padx=24, pady=(0, 6))
        self._payable_inner = ctk.CTkFrame(self._payable_card, fg_color="transparent")
        self._payable_inner.pack(fill="x", padx=12, pady=8)

        self._summary_lbl = ctk.CTkLabel(self, text="Select a ledger type and entity, then click Show",
                                          font=ctk.CTkFont(size=12), text_color="#888")
        self._summary_lbl.pack(anchor="w", padx=28, pady=(0, 4))

        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        self._hdr_frame = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        self._hdr_frame.pack(fill="x", padx=8, pady=(8, 0))

        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)

        self._on_type_change("vendor")

    def _on_type_change(self, val):
        self._ltype_val = val
        if val in ("vendor", "outstanding"):
            items = get_vendors(self.db_path, category="creditor")
            self._names = [v["name"] for v in items]
            self._ids = [v["id"] for v in items]
        elif val == "account":
            items = get_accounts(self.db_path)
            self._names = [a["name"] for a in items]
            self._ids = [a["id"] for a in items]
        else:
            items = get_expense_heads(self.db_path)
            self._names = [h["name"] for h in items]
            self._ids = [h["id"] for h in items]
        self._sel_menu.configure(values=self._names)
        self._sel_menu.set("")
        self._clear_table()
        for w in self._payable_inner.winfo_children():
            w.destroy()
        self._rebuild_headers(val)

    def _rebuild_headers(self, ltype):
        for w in self._hdr_frame.winfo_children():
            w.destroy()
        if ltype == "expense":
            headers = ["Voucher No", "Date", "Account", "Description", "Amount", "Running Total"]
            widths   = [90, 100, 130, 300, 120, 140]
        elif ltype == "outstanding":
            headers = ["Date", "Invoice / Ref", "Description",
                       "Debit (↓ Payable)", "Credit (↑ Payable)", "Balance"]
            widths   = [90, 120, 260, 130, 130, 120]
        elif ltype == "vendor":
            headers = ["Voucher No", "Date", "Inv Date", "Inv No.", "Type",
                       "Description", "Debit", "Credit", "Balance"]
            widths   = [90, 100, 100, 110, 90, 165, 110, 110, 120]
        else:
            headers = ["Voucher No", "Date", "Type", "Description", "Debit", "Credit", "Balance"]
            widths   = [90, 100, 100, 260, 110, 110, 120]
        self._widths = widths
        self._hdr_keys = headers
        for col, w in zip(headers, widths):
            ctk.CTkLabel(self._hdr_frame, text=col, width=w,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)
        if ltype not in ("expense", "outstanding"):
            ctk.CTkLabel(self._hdr_frame, text="Actions", width=100,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)

    def _get_sel_id(self):
        name = self._sel_menu.get()
        if name and name in self._names:
            idx = self._names.index(name)
            return self._ids[idx]
        return None

    def _load(self):
        sel_id = self._get_sel_id()
        if not sel_id:
            messagebox.showerror("Error", "Please select an entity.")
            return

        ltype = self._ltype.get()

        if ltype == "outstanding":
            data = get_vendor_outstanding_report(self.db_path, sel_id, self.fy_id)
            self._out_rows = data["rows"]
            self._entries = []
            self._ledger_name = data["name"]
            net = data["net_balance"]
            bal_tag = "PAYABLE" if net >= 0 else "ADVANCE"
            self._summary_lbl.configure(
                text=f"{data['name']}  |  Total Debit: {fmt(data['total_debit'])}  "
                     f"|  Total Credit: {fmt(data['total_credit'])}  "
                     f"|  {bal_tag}: {fmt(abs(net))}  |  {len(self._out_rows)} invoices",
                text_color="#1B2B6B"
            )
            self._show_outstanding_summary(data)
            self._draw_table(ltype)
            return

        df = self._df_entry.get() or None
        dt = self._dt_entry.get() or None

        if ltype == "vendor":
            data = get_vendor_ledger(self.db_path, sel_id, df, dt, self.fy_id)
            self._show_payable(sel_id)
            self._entries = data["entries"]
            self._out_rows = []
            self._ledger_name = data["name"]
            self._summary_lbl.configure(
                text=f"{data['name']}  |  Opening: {fmt(data['opening_balance'])}  "
                     f"|  Closing: {fmt(data['closing_balance'])}  |  {len(self._entries)} entries",
                text_color="#1B2B6B"
            )
        elif ltype == "account":
            data = get_account_ledger(self.db_path, sel_id, df, dt, self.fy_id)
            for w in self._payable_inner.winfo_children():
                w.destroy()
            self._entries = data["entries"]
            self._out_rows = []
            self._ledger_name = data["name"]
            self._summary_lbl.configure(
                text=f"{data['name']}  |  Opening: {fmt(data['opening_balance'])}  "
                     f"|  Closing: {fmt(data['closing_balance'])}  |  {len(self._entries)} entries",
                text_color="#1B2B6B"
            )
        else:
            data = get_expense_ledger(self.db_path, sel_id, df, dt, self.fy_id)
            for w in self._payable_inner.winfo_children():
                w.destroy()
            self._entries = data["entries"]
            self._out_rows = []
            self._ledger_name = data["name"]
            self._summary_lbl.configure(
                text=f"{data['name']}  |  Total Expense: {fmt(data['total'])}  "
                     f"|  {len(self._entries)} entries",
                text_color="#1B2B6B"
            )

        self._draw_table(ltype)

    def _show_outstanding_summary(self, data):
        for w in self._payable_inner.winfo_children():
            w.destroy()
        net = data["net_balance"]
        items = [
            ("Total Debit (↓)",  data["total_debit"],  "#D97706"),
            ("Total Credit (↑)", data["total_credit"], "#1B2B6B"),
        ]
        for label, value, color in items:
            frm = ctk.CTkFrame(self._payable_inner, fg_color="transparent")
            frm.pack(side="left", padx=16)
            ctk.CTkLabel(frm, text=label, font=ctk.CTkFont(size=11), text_color="#555").pack()
            ctk.CTkLabel(frm, text=fmt(value), font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color).pack()
        sep = ctk.CTkFrame(self._payable_inner, fg_color="#D0D8FF", width=2)
        sep.pack(side="left", fill="y", padx=16, pady=4)
        bal_color = "#EF4444" if net < 0 else "#1B4FD8"
        bal_text = f"NET PAYABLE: {fmt(net)}" if net >= 0 else f"NET ADVANCE: {fmt(abs(net))}"
        fb = ctk.CTkFrame(self._payable_inner, fg_color="transparent")
        fb.pack(side="left", padx=16)
        ctk.CTkLabel(fb, text="Net Balance", font=ctk.CTkFont(size=11), text_color="#555").pack()
        ctk.CTkLabel(fb, text=bal_text,
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=bal_color).pack()

    def _show_payable(self, vendor_id):
        for w in self._payable_inner.winfo_children():
            w.destroy()
        bal = get_vendor_balance(self.db_path, vendor_id, self.fy_id)
        items = [
            ("Opening Bal.", bal.get("opening", 0), "#6366F1"),
            ("+ Purchases",  bal["purchases"],     "#1B2B6B"),
            ("+ Credit Notes", bal["credit_notes"], "#7C3AED"),
            ("- Payments",   bal["payments"],      "#16A34A"),
            ("- Debit Notes",bal["debit_notes"],   "#D97706"),
        ]
        for label, value, color in items:
            frm = ctk.CTkFrame(self._payable_inner, fg_color="transparent")
            frm.pack(side="left", padx=12)
            ctk.CTkLabel(frm, text=label, font=ctk.CTkFont(size=11),
                         text_color="#555").pack()
            ctk.CTkLabel(frm, text=fmt(value), font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color).pack()

        sep = ctk.CTkFrame(self._payable_inner, fg_color="#D0D8FF", width=2)
        sep.pack(side="left", fill="y", padx=12, pady=4)

        balance = bal["balance"]
        bal_color = "#EF4444" if balance < 0 else "#1B4FD8"
        bal_text = f"PAYABLE: {fmt(balance)}" if balance >= 0 else f"ADVANCE: {fmt(abs(balance))}"
        fb = ctk.CTkFrame(self._payable_inner, fg_color="transparent")
        fb.pack(side="left", padx=16)
        ctk.CTkLabel(fb, text="Net Balance", font=ctk.CTkFont(size=11),
                     text_color="#555").pack()
        ctk.CTkLabel(fb, text=bal_text,
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=bal_color).pack()

    def _draw_table(self, ltype="vendor"):
        self._clear_table()

        if ltype == "outstanding":
            if not self._out_rows:
                ctk.CTkLabel(self._scroll, text="No invoices found.",
                             text_color="#999").pack(pady=20)
                return
            for i, e in enumerate(self._out_rows):
                is_ob = e.get("type") == "Opening Balance"
                bg = "#EEF2FF" if is_ob else ("#F8FAFF" if i % 2 == 0 else "white")
                row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
                row.pack(fill="x", pady=1)
                bal_color = "#EF4444" if e["balance"] < 0 else "#1B4FD8"
                date_str = to_display(e["date"]) if e.get("date") else "-"
                vals = [date_str,
                        str(e.get("ref") or "-")[:18],
                        str(e.get("description") or "-")[:38],
                        fmt(e["debit"]),
                        fmt(e["credit"]),
                        fmt(e["balance"])]
                for j, (val, width) in enumerate(zip(vals, self._widths)):
                    vc = bal_color if j == 5 else ("#1B4FD8" if is_ob else "#333")
                    ctk.CTkLabel(row, text=str(val), width=width,
                                 font=ctk.CTkFont(size=11), text_color=vc).pack(side="left", padx=4, pady=4)
            total_cr = sum(r["credit"] for r in self._out_rows)
            total_dr = sum(r["debit"] for r in self._out_rows)
            net = total_cr - total_dr
            foot = ctk.CTkFrame(self._scroll, fg_color="#1B2B6B", corner_radius=4)
            foot.pack(fill="x", pady=(4, 1))
            foot_vals = ["", "TOTAL", "", fmt(total_dr), fmt(total_cr), fmt(net)]
            foot_colors = ["white", "white", "white", "#FFA07A", "#7FFFD4",
                           "#EF4444" if net < 0 else "#7FFFD4"]
            for val, width, color in zip(foot_vals, self._widths, foot_colors):
                ctk.CTkLabel(foot, text=str(val), width=width,
                             font=ctk.CTkFont(size=11, weight="bold"),
                             text_color=color).pack(side="left", padx=4, pady=5)
            return

        if not self._entries:
            ctk.CTkLabel(self._scroll, text="No entries found for selected filters.",
                         text_color="#999").pack(pady=20)
            return

        if ltype == "expense":
            for i, e in enumerate(self._entries):
                bg = "#F8FAFF" if i % 2 == 0 else "white"
                row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
                row.pack(fill="x", pady=1)
                vals = [e["voucher_no"], to_display(e["date"]) if e["date"] else "-",
                        e.get("account") or "-",
                        str(e.get("description") or "-")[:40],
                        fmt(e["amount"]), fmt(e["running_total"])]
                for val, width in zip(vals, self._widths):
                    ctk.CTkLabel(row, text=str(val), width=width,
                                 font=ctk.CTkFont(size=11), text_color="#333").pack(side="left", padx=4, pady=4)
        else:
            for i, e in enumerate(self._entries):
                bg = "#F8FAFF" if i % 2 == 0 else "white"
                is_opening = e.get("type") == "Opening Balance"
                row = ctk.CTkFrame(self._scroll, fg_color="#EEF2FF" if is_opening else bg, corner_radius=4)
                row.pack(fill="x", pady=1)
                bal_color = "#EF4444" if e["balance"] < 0 else "#1B2B6B"
                date_display = to_display(e["date"]) if e["date"] else "-"
                desc = str(e.get("description") or "")
                ref = e.get("ref_number") or ""
                if ref and ref not in desc:
                    desc = f"[{ref}] {desc}"
                if ltype == "vendor":
                    inv_date = to_display(e.get("invoice_date")) if e.get("invoice_date") else "-"
                    inv_no   = str(e.get("invoice_number") or "-")[:16]
                    vals = [e["voucher_no"], date_display, inv_date, inv_no, e["type"],
                            desc[:22], fmt(e["debit"]), fmt(e["credit"]), fmt(e["balance"])]
                    bal_col_idx = 8
                else:
                    vals = [e["voucher_no"], date_display, e["type"],
                            desc[:38], fmt(e["debit"]), fmt(e["credit"]), fmt(e["balance"])]
                    bal_col_idx = 6
                for j, (val, width) in enumerate(zip(vals, self._widths)):
                    vc = bal_color if j == bal_col_idx else ("#1B4FD8" if is_opening else "#333")
                    ctk.CTkLabel(row, text=str(val), width=width,
                                 font=ctk.CTkFont(size=11), text_color=vc).pack(side="left", padx=4, pady=4)

                src_table = e.get("src_table")
                src_id = e.get("src_id")

                ctk.CTkButton(row, text="View", width=44, height=24,
                              fg_color="#0369A1", hover_color="#0284C7",
                              font=ctk.CTkFont(size=10),
                              command=lambda en=dict(e): self._view_entry(en)).pack(side="left", padx=2)

                if src_table == "vouchers":
                    ctk.CTkButton(row, text="Edit", width=44, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=src_id: self._edit_voucher(eid)).pack(side="left", padx=2)
                    ctk.CTkButton(row, text="Print", width=44, height=24,
                                  fg_color="#7C3AED", hover_color="#6D28D9",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=src_id: self._print_voucher(eid)).pack(side="left", padx=2)
                elif src_table == "purchases":
                    ctk.CTkButton(row, text="Edit", width=44, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=src_id: self._edit_purchase(eid)).pack(side="left", padx=2)
                elif src_table in ("credit_notes", "debit_notes"):
                    note_type = "credit" if src_table == "credit_notes" else "debit"
                    ctk.CTkButton(row, text="Edit", width=44, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=src_id, nt=note_type: self._edit_note(eid, nt)
                                  ).pack(side="left", padx=2)

    # ── View popup ────────────────────────────────────────────────────────────

    def _view_entry(self, e):
        src = e.get("src_table", "")
        src_id = e.get("src_id")
        win = tk.Toplevel(self)
        win.title(f"View — {e.get('voucher_no', '')}")
        win.configure(bg="#F4F6FB")
        win.grab_set()

        frm = ctk.CTkFrame(win, fg_color="white", corner_radius=12)
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        def lrow(label, value, r):
            ctk.CTkLabel(frm, text=label, font=ctk.CTkFont(weight="bold"),
                         text_color="#555", anchor="w").grid(row=r, column=0, sticky="w", padx=14, pady=4)
            ctk.CTkLabel(frm, text=str(value or "-"), text_color="#111",
                         anchor="w").grid(row=r, column=1, sticky="w", padx=14, pady=4)

        if src == "vouchers" and src_id:
            v = get_voucher(self.db_path, src_id)
            if v:
                lrow("Voucher No",   v.get("voucher_no"), 0)
                lrow("Date",         to_display(v.get("date")), 1)
                lrow("Type",         v.get("type", "").title(), 2)
                lrow("Vendor",       v.get("vendor_name") or "-", 3)
                lrow("From Account", v.get("from_account_name") or "-", 4)
                lrow("Payment Mode", v.get("payment_mode") or "-", 5)
                lrow("To Account",   v.get("to_account_name") or "-", 6)
                lrow("Amount",       fmt(v.get("amount")), 7)
                lrow("Narration",    v.get("narration") or "-", 8)
                lrow("Status",       v.get("status", "active"), 9)
        else:
            lrow("Voucher No", e.get("voucher_no"), 0)
            lrow("Date",       to_display(e.get("date", "")), 1)
            lrow("Type",       e.get("type", "").replace("_", " ").title(), 2)
            lrow("Description", e.get("description") or "-", 3)
            lrow("Debit",      fmt(e.get("debit", 0)), 4)
            lrow("Credit",     fmt(e.get("credit", 0)), 5)
            lrow("Balance",    fmt(e.get("balance", 0)), 6)

        btn_row = ctk.CTkFrame(frm, fg_color="transparent")
        btn_row.grid(row=20, column=0, columnspan=2, pady=14)

        def _close():
            win.destroy()

        if src == "vouchers" and src_id:
            ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                          command=lambda: (_close(), self._edit_voucher(src_id))
                          ).pack(side="left", padx=6)
            ctk.CTkButton(btn_row, text="Print", width=80, fg_color="#7C3AED",
                          command=lambda: self._print_voucher(src_id)
                          ).pack(side="left", padx=6)
        elif src == "purchases" and src_id:
            ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                          command=lambda: (_close(), self._edit_purchase(src_id))
                          ).pack(side="left", padx=6)

        ctk.CTkButton(btn_row, text="Close", width=80, fg_color="#6B7280",
                      command=_close).pack(side="left", padx=6)

        win.update_idletasks()
        w = max(win.winfo_reqwidth(), 460)
        h = win.winfo_reqheight()
        win.geometry(f"{w}x{h}")

    # ── Navigation helpers ────────────────────────────────────────────────────

    def _navigate(self, page_key, edit_fn_name, entity_id):
        top = self.winfo_toplevel()
        for w in top.winfo_children():
            if hasattr(w, "_page_frames"):
                w._show_page(page_key)
                frame = w._page_frames.get(page_key)
                if frame and hasattr(frame, edit_fn_name):
                    getattr(frame, edit_fn_name)(entity_id)
                return

    def _edit_voucher(self, vid):
        self._navigate("voucher", "load_for_edit", vid)

    def _edit_purchase(self, pid):
        self._navigate("purchase", "load_for_edit", pid)

    def _edit_note(self, nid, note_type):
        page = "credit_note" if note_type == "credit" else "debit_note"
        self._navigate(page, "load_for_edit", nid)

    def _print_voucher(self, voucher_id):
        v = get_voucher(self.db_path, voucher_id)
        if v:
            try:
                from database import get_meta
                entity_name = get_meta(self.db_path, "entity_name", "")
            except Exception:
                entity_name = ""
            from pdf_generator import print_voucher_pdf
            print_voucher_pdf(v, entity_name=entity_name)

    def _clear_table(self):
        for w in self._scroll.winfo_children():
            w.destroy()

    def _clear_dates(self):
        self._df_entry.set("")
        self._dt_entry.set("")

    def _export(self):
        ltype = self._ltype.get()
        no_data = (not self._out_rows) if ltype == "outstanding" else (not self._entries)
        if no_data:
            messagebox.showwarning("No Data", "Load a report first before exporting.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel", "*.xlsx")],
                                            title="Save Report")
        if not path:
            return
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Report"
            ws.append([f"{'Outstanding Report' if ltype == 'outstanding' else 'Ledger'}: {self._ledger_name}"])
            if ltype == "outstanding":
                ws.append(["Date", "Invoice / Ref", "Description",
                            "Debit (↓ Payable)", "Credit (↑ Payable)", "Balance"])
                for e in self._out_rows:
                    ws.append([
                        to_display(e["date"]) if e.get("date") else "-",
                        e.get("ref") or "-",
                        e.get("description") or "",
                        e["debit"], e["credit"], e["balance"]
                    ])
                total_dr = sum(r["debit"] for r in self._out_rows)
                total_cr = sum(r["credit"] for r in self._out_rows)
                ws.append(["", "TOTAL", "", total_dr, total_cr, total_cr - total_dr])
            elif ltype == "expense":
                ws.append(["Voucher No", "Date", "Account", "Description / Narration",
                            "Amount", "Running Total"])
                for e in self._entries:
                    ws.append([e["voucher_no"],
                                to_display(e["date"]) if e["date"] else "-",
                                e.get("account") or "-",
                                e.get("description") or "",
                                e["amount"], e["running_total"]])
            elif ltype == "vendor":
                ws.append(["Voucher No", "Date", "Inv Date", "Inv No.", "Type",
                            "Description / Narration", "Debit", "Credit", "Balance"])
                for e in self._entries:
                    ws.append([e.get("voucher_no") or "-",
                                to_display(e["date"]) if e.get("date") else "-",
                                to_display(e.get("invoice_date")) if e.get("invoice_date") else "-",
                                e.get("invoice_number") or "-",
                                e.get("type") or "-",
                                e.get("description") or "",
                                e.get("debit", 0), e.get("credit", 0), e.get("balance", 0)])
            else:
                ws.append(["Voucher No", "Date", "Type", "Description / Narration",
                            "Debit", "Credit", "Balance"])
                for e in self._entries:
                    ws.append([e["voucher_no"],
                                to_display(e["date"]) if e["date"] else "-",
                                e.get("type") or "-",
                                e.get("description") or "",
                                e.get("debit", 0), e.get("credit", 0), e.get("balance", 0)])
            wb.save(path)
            messagebox.showinfo("Exported", f"Report exported:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Error", f"Could not export:\n{ex}")

    def _print_ledger(self):
        ltype = self._ltype.get()
        no_data = (not self._out_rows) if ltype == "outstanding" else (not self._entries)
        if no_data:
            messagebox.showwarning("No Data", "Load a ledger first before printing.")
            return
        try:
            from database import get_meta
            entity_name = get_meta(self.db_path, "entity_name", "")
        except Exception:
            entity_name = ""
        from pdf_generator import print_ledger_pdf
        print_ledger_pdf(ltype, self._ledger_name, self._entries,
                         self._out_rows, entity_name)

    def refresh(self):
        self._on_type_change(self._ltype.get())
