import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import openpyxl
from date_utils import DateEntry, to_display
from database import (get_daybook_entries, get_voucher,
                      cancel_voucher, cancel_purchase, cancel_note,
                      restore_voucher, restore_purchase, restore_note)


REGISTER_DEFS = [
    ("Purchase",    "purchase"),
    ("Payment",     "payment"),
    ("Credit Note", "credit_note"),
    ("Debit Note",  "debit_note"),
]
REG_LABELS  = [r[0] for r in REGISTER_DEFS]
REG_VTYPES  = {r[0]: r[1] for r in REGISTER_DEFS}

COLS   = ["Date", "Voucher No", "Vendor / Account", "Amount", "Narration", "Status"]
WIDTHS = [100, 110, 190, 115, 220, 75]


def fmt(v):
    try:
        return f"\u20b9{float(v):,.2f}"
    except Exception:
        return str(v)


class RegisterFrame(ctk.CTkFrame):
    """
    Structure intentionally mirrors DaybookFrame so the layout is proven
    to work: title-row → filter-card → summary-label → scroll-card.
    The only addition is a register-type OptionMenu inside the filter row
    and a search entry on a second row of the same filter card.
    """

    def __init__(self, master, db_path, fy_id=None, **kwargs):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id   = fy_id
        self._entries = []
        self._build()

    # ── Build (mirrors DaybookFrame layout) ──────────────────────────────────

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        # 1. Title row  (same as DaybookFrame)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(top, text="Register",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(side="left")
        ctk.CTkButton(top, text="Export Excel", width=120, fg_color="#16A34A",
                      hover_color="#15803D",
                      command=self._export).pack(side="right", padx=6)

        # 2. Filter card  (same outer frame as DaybookFrame)
        f = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        f.pack(fill="x", padx=24, pady=(0, 8))

        r1 = ctk.CTkFrame(f, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(r1, text="From").pack(side="left", padx=(0, 4))
        self._df_entry = DateEntry(r1, initial_date="")
        self._df_entry.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(r1, text="To").pack(side="left", padx=(0, 4))
        self._dt_entry = DateEntry(r1, initial_date="")
        self._dt_entry.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(r1, text="Type").pack(side="left", padx=(0, 4))
        self._type_var = tk.StringVar(value=REG_LABELS[0])
        ctk.CTkOptionMenu(r1, values=REG_LABELS,
                          variable=self._type_var, width=140,
                          command=lambda _: self._load()
                          ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(r1, text="Show", width=80, fg_color="#1B4FD8",
                      command=self._load).pack(side="left", padx=4)
        ctk.CTkButton(r1, text="Clear", width=70, fg_color="#6B7280",
                      command=self._clear_filters).pack(side="left", padx=4)

        self._show_cancelled_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(r1, text="Show Cancelled",
                        variable=self._show_cancelled_var,
                        command=self._load).pack(side="left", padx=10)

        # Search row inside the same filter card
        r2 = ctk.CTkFrame(f, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(r2, text="Search").pack(side="left", padx=(0, 4))
        self._search_var = tk.StringVar()
        ctk.CTkEntry(r2, textvariable=self._search_var, width=360,
                     placeholder_text="Filter by vendor, voucher no, amount, narration…"
                     ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(r2, text="Clear Search", width=100, fg_color="#6B7280",
                      command=lambda: self._search_var.set("")
                      ).pack(side="left", padx=4)
        self._search_var.trace_add("write", lambda *_: self._apply_filter())

        # 3. Summary label  (same as DaybookFrame)
        self._summary_lbl = ctk.CTkLabel(self, text="",
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          text_color="#1B2B6B")
        self._summary_lbl.pack(anchor="e", padx=28)

        # 4. Scroll card  (same as DaybookFrame — gets all remaining height)
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(4, 24))

        h = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        h.pack(fill="x", padx=8, pady=(8, 0))
        for col, w in zip(COLS, WIDTHS):
            ctk.CTkLabel(h, text=col, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=3, pady=6)
        ctk.CTkLabel(h, text="Actions", width=220,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=3, pady=6)

        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)

        self._load()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load(self):
        vtype = REG_VTYPES.get(self._type_var.get(), "purchase")
        self._entries = get_daybook_entries(
            self.db_path,
            date_from=self._df_entry.get() or None,
            date_to=self._dt_entry.get() or None,
            vtype=vtype,
            include_cancelled=self._show_cancelled_var.get(),
            fy_id=self.fy_id,
        )
        self._apply_filter()

    def _apply_filter(self):
        q = self._search_var.get().strip().lower()
        rows = self._entries
        if q:
            def match(e):
                return any(q in str(e.get(k) or "").lower()
                           for k in ("vendor_name", "from_account_name",
                                     "voucher_no", "amount", "narration"))
            rows = [e for e in rows if match(e)]

        active = [e for e in rows if e.get("status") != "cancelled"]
        total  = sum(e["amount"] for e in active)
        self._summary_lbl.configure(
            text=f"Total: {fmt(total)}   ({len(rows)} entries, {len(active)} active)"
        )
        self._draw(rows)

    # ── Table drawing ─────────────────────────────────────────────────────────

    def _draw(self, entries):
        for w in self._scroll.winfo_children():
            w.destroy()

        if not entries:
            ctk.CTkLabel(self._scroll, text="No entries found.",
                         text_color="#999").pack(pady=20)
            return

        for i, e in enumerate(entries):
            is_cancelled = e.get("status") == "cancelled"
            bg    = "#FFF0F0" if is_cancelled else ("#F8FAFF" if i % 2 == 0 else "white")
            color = "#888"   if is_cancelled else "#333"
            row   = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)

            party = e.get("vendor_name") or e.get("from_account_name") or "-"
            narr  = str(e.get("narration") or "-")

            for val, width in zip(
                [to_display(e["date"]), e["voucher_no"], party[:26],
                 fmt(e["amount"]), narr[:32], e.get("status", "active")],
                WIDTHS
            ):
                ctk.CTkLabel(row, text=str(val), width=width,
                             font=ctk.CTkFont(size=11),
                             text_color=color).pack(side="left", padx=3, pady=4)

            af  = ctk.CTkFrame(row, fg_color="transparent")
            af.pack(side="left", padx=3)
            src = e["src_table"]

            ctk.CTkButton(af, text="View", width=44, height=24,
                          fg_color="#0369A1", hover_color="#0284C7",
                          font=ctk.CTkFont(size=10),
                          command=lambda en=dict(e): self._view(en)
                          ).pack(side="left", padx=2)

            if not is_cancelled:
                if src == "payment_transfer":
                    ctk.CTkButton(af, text="Edit", width=44, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=e["id"]: self._navigate("voucher", "load_for_edit", eid)
                                  ).pack(side="left", padx=2)
                elif src == "purchases":
                    ctk.CTkButton(af, text="Edit", width=44, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=e["id"]: self._navigate("purchase", "load_for_edit", eid)
                                  ).pack(side="left", padx=2)
                elif src in ("credit_notes", "debit_notes"):
                    pg = "credit_note" if src == "credit_notes" else "debit_note"
                    ctk.CTkButton(af, text="Edit", width=44, height=24,
                                  fg_color="#6366F1", hover_color="#4F46E5",
                                  font=ctk.CTkFont(size=10),
                                  command=lambda eid=e["id"], p=pg: self._navigate(p, "load_for_edit", eid)
                                  ).pack(side="left", padx=2)

                ctk.CTkButton(af, text="Cancel", width=56, height=24,
                              fg_color="#EF4444", hover_color="#DC2626",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"], tbl=src,
                                             vno=e["voucher_no"]: self._cancel(eid, tbl, vno)
                              ).pack(side="left", padx=2)
            else:
                ctk.CTkButton(af, text="Restore", width=60, height=24,
                              fg_color="#16A34A", hover_color="#15803D",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"], tbl=src,
                                             vno=e["voucher_no"]: self._restore(eid, tbl, vno)
                              ).pack(side="left", padx=2)

            if src == "payment_transfer":
                ctk.CTkButton(af, text="Print", width=48, height=24,
                              fg_color="#7C3AED", hover_color="#6D28D9",
                              font=ctk.CTkFont(size=10),
                              command=lambda eid=e["id"]: self._print(eid)
                              ).pack(side="left", padx=2)

    # ── View popup ────────────────────────────────────────────────────────────

    def _view(self, e):
        src = e.get("src_table", "")
        eid = e["id"]
        win = tk.Toplevel(self)
        win.title(f"View — {e['voucher_no']}")
        win.configure(bg="#F4F6FB")
        win.grab_set()

        frm = ctk.CTkFrame(win, fg_color="white", corner_radius=12)
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        def lrow(label, value, r):
            ctk.CTkLabel(frm, text=label, font=ctk.CTkFont(weight="bold"),
                         text_color="#555", anchor="w"
                         ).grid(row=r, column=0, sticky="w", padx=14, pady=4)
            ctk.CTkLabel(frm, text=str(value or "-"), text_color="#111",
                         anchor="w").grid(row=r, column=1, sticky="w", padx=14, pady=4)

        if src == "payment_transfer":
            v = get_voucher(self.db_path, eid)
            if v:
                lrow("Voucher No",   v.get("voucher_no"), 0)
                lrow("Date",         to_display(v.get("date")), 1)
                lrow("Type",         v.get("type", "").title(), 2)
                lrow("Vendor",       v.get("vendor_name") or "-", 3)
                lrow("From Account", v.get("from_account_name") or "-", 4)
                lrow("Amount",       fmt(v.get("amount")), 5)
                lrow("Narration",    v.get("narration") or "-", 6)
                lrow("Status",       v.get("status", "active"), 7)
        else:
            lrow("Voucher No", e["voucher_no"], 0)
            lrow("Date",       to_display(e["date"]), 1)
            lrow("Type",       e["type"].replace("_", " ").title(), 2)
            lrow("Vendor",     e.get("vendor_name") or "-", 3)
            lrow("Amount",     fmt(e["amount"]), 4)
            lrow("Narration",  e.get("narration") or "-", 5)
            lrow("Status",     e.get("status", "active"), 6)

        btn_row = ctk.CTkFrame(frm, fg_color="transparent")
        btn_row.grid(row=20, column=0, columnspan=2, pady=14)

        def _close():
            win.destroy()

        is_cancelled = e.get("status") == "cancelled"
        if not is_cancelled:
            if src == "payment_transfer":
                ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                              command=lambda: (_close(), self._navigate("voucher", "load_for_edit", eid))
                              ).pack(side="left", padx=6)
                ctk.CTkButton(btn_row, text="Print", width=80, fg_color="#7C3AED",
                              command=lambda: self._print(eid)
                              ).pack(side="left", padx=6)
            elif src == "purchases":
                ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                              command=lambda: (_close(), self._navigate("purchase", "load_for_edit", eid))
                              ).pack(side="left", padx=6)
            elif src in ("credit_notes", "debit_notes"):
                pg = "credit_note" if src == "credit_notes" else "debit_note"
                ctk.CTkButton(btn_row, text="Edit", width=80, fg_color="#6366F1",
                              command=lambda: (_close(), self._navigate(pg, "load_for_edit", eid))
                              ).pack(side="left", padx=6)

        ctk.CTkButton(btn_row, text="Close", width=80, fg_color="#6B7280",
                      command=_close).pack(side="left", padx=6)

        win.update_idletasks()
        win.geometry(f"{max(win.winfo_reqwidth(), 460)}x{win.winfo_reqheight()}")

    # ── Actions ───────────────────────────────────────────────────────────────

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
            self._load()

    def _restore(self, eid, table, vno):
        if messagebox.askyesno("Restore",
                               f"Restore voucher {vno} to Active?\n\n"
                               "It will reappear in Day Book, Ledger and Registers."):
            if table == "payment_transfer":
                restore_voucher(self.db_path, eid)
            elif table == "purchases":
                restore_purchase(self.db_path, eid)
            elif table == "credit_notes":
                restore_note(self.db_path, "credit_notes", eid)
            elif table == "debit_notes":
                restore_note(self.db_path, "debit_notes", eid)
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

    def _navigate(self, page_key, edit_fn_name, entity_id):
        top = self.winfo_toplevel()
        for w in top.winfo_children():
            if hasattr(w, "_page_frames"):
                w._show_page(page_key)
                frame = w._page_frames.get(page_key)
                if frame and hasattr(frame, edit_fn_name):
                    getattr(frame, edit_fn_name)(entity_id)
                return

    def _clear_filters(self):
        self._df_entry.set("")
        self._dt_entry.set("")
        self._show_cancelled_var.set(False)
        self._search_var.set("")
        self._load()

    def _export(self):
        if not self._entries:
            messagebox.showwarning("No Data", "Load data first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Save Register")
        if not path:
            return
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Register"
            ws.append(["Date", "Voucher No", "Vendor / Account",
                       "Amount", "Narration", "Status"])
            for e in self._entries:
                party = e.get("vendor_name") or e.get("from_account_name") or "-"
                ws.append([
                    to_display(e["date"]), e["voucher_no"], party,
                    e["amount"], e.get("narration") or "",
                    e.get("status", "active"),
                ])
            wb.save(path)
            messagebox.showinfo("Exported", f"Register exported:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Error", f"Could not export:\n{ex}")

    def refresh(self):
        self._load()
