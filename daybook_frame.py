import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import openpyxl
from date_utils import DateEntry, to_display
from database import (get_daybook_entries, cancel_voucher, cancel_purchase,
                      cancel_note, cancel_expense, get_voucher, get_expense,
                      restore_voucher, restore_purchase, restore_note, restore_expense)

COLS = ["Voucher No", "Date", "Type", "Vendor / Account", "From", "To", "Amount", "Status"]
WIDTHS = [90, 100, 100, 155, 125, 125, 100, 80]
TYPE_OPTIONS = ["All", "payment", "transfer", "purchase", "credit_note", "debit_note", "expense"]


def fmt(v):
    try:
        return f"\u20b9{float(v):,.2f}"
    except Exception:
        return str(v)


class DaybookFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self._entries = []
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(top, text="Day Book",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(side="left")
        ctk.CTkButton(top, text="Export Excel", width=120, fg_color="#16A34A",
                      hover_color="#15803D", command=self._export).pack(side="right", padx=6)

        f = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        f.pack(fill="x", padx=24, pady=(0, 8))
        r1 = ctk.CTkFrame(f, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(10, 2))

        ctk.CTkLabel(r1, text="From").pack(side="left", padx=(0, 4))
        self._df_entry = DateEntry(r1, initial_date="")
        self._df_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(r1, text="To").pack(side="left", padx=(0, 4))
        self._dt_entry = DateEntry(r1, initial_date="")
        self._dt_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(r1, text="Type").pack(side="left", padx=(0, 4))
        self._type_var = tk.StringVar(value="All")
        ctk.CTkOptionMenu(r1, values=TYPE_OPTIONS,
                          variable=self._type_var, width=130).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(r1, text="Voucher#").pack(side="left", padx=(0, 4))
        self._vno_var = tk.StringVar()
        ctk.CTkEntry(r1, textvariable=self._vno_var, width=90).pack(side="left", padx=(0, 10))

        self._show_cancelled_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(r1, text="Show Cancelled",
                        variable=self._show_cancelled_var,
                        command=self._load).pack(side="left", padx=10)

        r2 = ctk.CTkFrame(f, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(2, 8))

        ctk.CTkLabel(r2, text="Name").pack(side="left", padx=(0, 4))
        self._name_var = tk.StringVar()
        ctk.CTkEntry(r2, textvariable=self._name_var, width=170,
                     placeholder_text="vendor / account / expense").pack(side="left", padx=(0, 10))

        ctk.CTkLabel(r2, text="Invoice No").pack(side="left", padx=(0, 4))
        self._invno_var = tk.StringVar()
        ctk.CTkEntry(r2, textvariable=self._invno_var, width=110).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(r2, text="Amt From").pack(side="left", padx=(0, 4))
        self._amt_from_var = tk.StringVar()
        ctk.CTkEntry(r2, textvariable=self._amt_from_var, width=90).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(r2, text="To").pack(side="left", padx=(0, 4))
        self._amt_to_var = tk.StringVar()
        ctk.CTkEntry(r2, textvariable=self._amt_to_var, width=90).pack(side="left", padx=(0, 10))

        ctk.CTkButton(r2, text="Search", width=80, fg_color="#1B4FD8",
                      command=self._load).pack(side="left", padx=4)
        ctk.CTkButton(r2, text="Clear", width=70, fg_color="#6B7280",
                      command=self._clear_filters).pack(side="left", padx=4)

        self._summary_lbl = ctk.CTkLabel(self, text="",
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          text_color="#1B2B6B")
        self._summary_lbl.pack(anchor="e", padx=28)

        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(4, 24))

        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(COLS, WIDTHS):
            ctk.CTkLabel(h, text=col, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=3, pady=6)
        ctk.CTkLabel(h, text="Actions", width=200,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=3, pady=6)

        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._load()

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        tp = self._type_var.get()
        df = self._df_entry.get() or None
        dt = self._dt_entry.get() or None

        amt_from_s = self._amt_from_var.get().strip()
        amt_to_s   = self._amt_to_var.get().strip()
        try:
            amt_from = float(amt_from_s) if amt_from_s else None
        except ValueError:
            amt_from = None
        try:
            amt_to = float(amt_to_s) if amt_to_s else None
        except ValueError:
            amt_to = None

        entries = get_daybook_entries(
            self.db_path,
            date_from=df,
            date_to=dt,
            voucher_no_filter=self._vno_var.get().strip() or None,
            name_filter=self._name_var.get().strip() or None,
            invoice_no_filter=self._invno_var.get().strip() or None,
            amount_min=amt_from,
            amount_max=amt_to,
            vtype=None if tp == "All" else tp,
            include_cancelled=self._show_cancelled_var.get(),
            fy_id=self.fy_id,
        )
        self._entries = entries
        active = [e for e in entries if e.get("status") != "cancelled"]
        total = sum(e["amount"] for e in active)
        self._summary_lbl.configure(
            text=f"Total: {fmt(total)}   ({len(entries)} entries, {len(active)} active)")

        if not entries:
            ctk.CTkLabel(self._scroll, text="No entries found.",
                         text_color="#999").pack(pady=20)
            return

        for i, e in enumerate(entries):
            is_cancelled = e.get("status") == "cancelled"
            bg = "#FFF0F0" if is_cancelled else ("#F8FAFF" if i % 2 == 0 else "white")
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)

            vendor = e.get("vendor_name") or "-"
            frm = e.get("from_account_name") or "-"
            to = e.get("to_account_name") or "-"
            vtype_display = e["type"].replace("_", " ").title()
            status = e.get("status", "active")
            color = "#888" if is_cancelled else "#333"

            row_vals = [e["voucher_no"], to_display(e["date"]), vtype_display,
                        vendor, frm, to, fmt(e["amount"]), status]
            for val, width in zip(row_vals, WIDTHS):
                ctk.CTkLabel(row, text=str(val)[:20], width=width,
                             font=ctk.CTkFont(size=11), text_color=color).pack(side="left", padx=3, pady=4)

            af = ctk.CTkFrame(row, fg_color="transparent")
            af.pack(side="left", padx=3)

            src = e["src_table"]

            ctk.CTkButton(af, text="View", width=42, height=24,
                          fg_color="#0369A1", hover_color="#0284C7",
                          font=ctk.CTkFont(size=10),
                          command=lambda en=dict(e): self._view_entry(en)).pack(side="left", padx=2)

            if not is_cancelled:
                if src == "payment_transfer":
                    ctk.CTkButton(af, text="Edit", width=42, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=e["id"]: self._edit_voucher(eid)).pack(side="left", padx=2)
                elif src == "purchases":
                    ctk.CTkButton(af, text="Edit", width=42, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=e["id"]: self._edit_purchase(eid)).pack(side="left", padx=2)
                elif src in ("credit_notes", "debit_notes"):
                    nt = "credit" if src == "credit_notes" else "debit"
                    ctk.CTkButton(af, text="Edit", width=42, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=e["id"], t=nt: self._edit_note(eid, t)).pack(side="left", padx=2)
                elif src == "expenses":
                    ctk.CTkButton(af, text="Edit", width=42, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=e["id"]: self._edit_expense(eid)).pack(side="left", padx=2)

                ctk.CTkButton(af, text="Cancel", width=54, height=24,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"], tbl=src,
                                             vno=e["voucher_no"]: self._cancel(eid, tbl, vno)
                              ).pack(side="left", padx=2)
            else:
                ctk.CTkButton(af, text="Restore", width=58, height=24,
                              fg_color="#16A34A", hover_color="#15803D",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"], tbl=src,
                                             vno=e["voucher_no"]: self._restore(eid, tbl, vno)
                              ).pack(side="left", padx=2)

            if src == "payment_transfer":
                ctk.CTkButton(af, text="Print", width=46, height=24,
                              fg_color="#7C3AED", hover_color="#6D28D9",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"]: self._print(eid)).pack(side="left", padx=2)
            elif src == "expenses":
                ctk.CTkButton(af, text="Print", width=46, height=24,
                              fg_color="#7C3AED", hover_color="#6D28D9",
                              font=ctk.CTkFont(size=10),
                              command=lambda en=dict(e): self._print_expense(en)).pack(side="left", padx=2)

    # ── View popup ────────────────────────────────────────────────────────────

    def _view_entry(self, e):
        src = e.get("src_table", "")
        eid = e["id"]
        win = tk.Toplevel(self)
        win.title(f"View — {e['voucher_no']}")
        win.configure(bg="#F4F6FB")
        win.grab_set()

        frm = ctk.CTkFrame(win, fg_color="white", corner_radius=12)
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        def row(label, value, r):
            ctk.CTkLabel(frm, text=label, font=ctk.CTkFont(weight="bold"),
                         text_color="#555", anchor="w").grid(row=r, column=0, sticky="w", padx=14, pady=4)
            ctk.CTkLabel(frm, text=str(value or "-"), text_color="#111",
                         anchor="w").grid(row=r, column=1, sticky="w", padx=14, pady=4)

        if src == "expenses":
            exp = get_expense(self.db_path, eid)
            if exp:
                row("Voucher No",   exp.get("voucher_no", e["voucher_no"]), 0)
                row("Date",         to_display(exp.get("date", e["date"])), 1)
                row("Expense Head", exp.get("expense_head_name") or exp.get("to_account_name") or "-", 2)
                row("Paid From",    exp.get("account_name") or exp.get("from_account_name") or "-", 3)
                row("Payment Mode", exp.get("payment_mode") or "-", 4)
                row("Amount",       fmt(exp.get("amount", e["amount"])), 5)
                row("Narration",    exp.get("narration") or "-", 6)
                row("Status",       exp.get("status", "active"), 7)
        elif src == "payment_transfer":
            v = get_voucher(self.db_path, eid)
            if v:
                row("Voucher No",    v.get("voucher_no"), 0)
                row("Date",          to_display(v.get("date")), 1)
                row("Type",          v.get("type", "").title(), 2)
                row("Vendor",        v.get("vendor_name") or "-", 3)
                row("From Account",  v.get("from_account_name") or "-", 4)
                row("Payment Mode",  v.get("payment_mode") or "-", 5)
                row("To Account",    v.get("to_account_name") or "-", 6)
                row("Amount",        fmt(v.get("amount")), 7)
                row("Narration",     v.get("narration") or "-", 8)
                row("Status",        v.get("status", "active"), 9)
        else:
            row("Voucher No",   e["voucher_no"], 0)
            row("Date",         to_display(e["date"]), 1)
            row("Type",         e["type"].replace("_", " ").title(), 2)
            row("Vendor",       e.get("vendor_name") or "-", 3)
            row("From",         e.get("from_account_name") or "-", 4)
            row("To",           e.get("to_account_name") or "-", 5)
            row("Amount",       fmt(e["amount"]), 6)
            row("Narration",    e.get("narration") or "-", 7)
            row("Status",       e.get("status", "active"), 8)

        btn_row = ctk.CTkFrame(frm, fg_color="transparent")
        btn_row.grid(row=20, column=0, columnspan=2, pady=14)

        is_cancelled = e.get("status") == "cancelled"

        if not is_cancelled:
            if src == "payment_transfer":
                ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                              command=lambda: (_close(), self._edit_voucher(eid))
                              ).pack(side="left", padx=6)
                ctk.CTkButton(btn_row, text="Print", width=80, fg_color="#7C3AED",
                              command=lambda: self._print(eid)
                              ).pack(side="left", padx=6)
            elif src == "purchases":
                ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                              command=lambda: (_close(), self._edit_purchase(eid))
                              ).pack(side="left", padx=6)
            elif src in ("credit_notes", "debit_notes"):
                nt = "credit" if src == "credit_notes" else "debit"
                ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                              command=lambda: (_close(), self._edit_note(eid, nt))
                              ).pack(side="left", padx=6)
            elif src == "expenses":
                ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                              command=lambda: (_close(), self._edit_expense(eid))
                              ).pack(side="left", padx=6)
                ctk.CTkButton(btn_row, text="Print", width=80, fg_color="#7C3AED",
                              command=lambda: self._print_expense(e)
                              ).pack(side="left", padx=6)

        def _close():
            win.destroy()

        ctk.CTkButton(btn_row, text="Close", width=80, fg_color="#6B7280",
                      command=_close).pack(side="left", padx=6)

        win.update_idletasks()
        w = max(win.winfo_reqwidth(), 480)
        h = win.winfo_reqheight()
        win.geometry(f"{w}x{h}")

    # ── Navigation ────────────────────────────────────────────────────────────

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

    def _edit_expense(self, eid):
        self._navigate("expense", "load_for_edit", eid)

    def _cancel(self, eid, table, vno):
        if messagebox.askyesno("Cancel",
                               f"Cancel voucher {vno}?\n\nMarked cancelled — NOT deleted."):
            if table == "payment_transfer":
                cancel_voucher(self.db_path, eid)
            elif table == "purchases":
                cancel_purchase(self.db_path, eid)
            elif table == "credit_notes":
                cancel_note(self.db_path, "credit_notes", eid)
            elif table == "debit_notes":
                cancel_note(self.db_path, "debit_notes", eid)
            elif table == "expenses":
                cancel_expense(self.db_path, eid)
            self._load()

    def _restore(self, eid, table, vno):
        if messagebox.askyesno("Restore",
                               f"Restore voucher {vno} to Active?\n\n"
                               "It will reappear in Day Book, Ledger and Reports."):
            if table == "payment_transfer":
                restore_voucher(self.db_path, eid)
            elif table == "purchases":
                restore_purchase(self.db_path, eid)
            elif table == "credit_notes":
                restore_note(self.db_path, "credit_notes", eid)
            elif table == "debit_notes":
                restore_note(self.db_path, "debit_notes", eid)
            elif table == "expenses":
                restore_expense(self.db_path, eid)
            self._load()

    def _print(self, voucher_id):
        v = get_voucher(self.db_path, voucher_id)
        if v:
            try:
                from database import get_meta
                entity_name = get_meta(self.db_path, "entity_name", "")
            except Exception:
                entity_name = ""
            from pdf_generator import print_voucher_pdf
            print_voucher_pdf(v, entity_name=entity_name)

    def _print_expense(self, e):
        try:
            from database import get_meta
            entity_name = get_meta(self.db_path, "entity_name", "")
        except Exception:
            entity_name = ""
        exp = get_expense(self.db_path, e["id"]) if e.get("id") else None
        from pdf_generator import print_expense_pdf
        print_expense_pdf(exp or e, entity_name=entity_name)

    def _clear_filters(self):
        self._df_entry.set("")
        self._dt_entry.set("")
        self._type_var.set("All")
        self._vno_var.set("")
        self._name_var.set("")
        self._invno_var.set("")
        self._amt_from_var.set("")
        self._amt_to_var.set("")
        self._show_cancelled_var.set(False)
        self._load()

    def _export(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel", "*.xlsx")],
                                            title="Save Day Book")
        if not path:
            return
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Day Book"
            ws.append(COLS + ["Narration"])
            for e in self._entries:
                party = e.get("vendor_name") or "-"
                frm = e.get("from_account_name") or "-"
                to = e.get("to_account_name") or "-"
                ws.append([e["voucher_no"], to_display(e["date"]),
                           e["type"].replace("_", " ").title(),
                           party, frm, to, e["amount"],
                           e.get("status", "active"), e.get("narration") or ""])
            wb.save(path)
            messagebox.showinfo("Exported", f"Day Book exported:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Error", f"Could not export:\n{ex}")

    def refresh(self):
        self._load()
