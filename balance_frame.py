import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import openpyxl
from date_utils import DateEntry, to_display, today_storage
from database import get_balance_report


def fmt(v):
    try:
        return f"\u20b9{float(v):,.2f}"
    except Exception:
        return "-"


class BalanceFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None, **kwargs):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self._all_rows = []
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(top, text="Balance",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(side="left")
        ctk.CTkButton(top, text="Export Excel", width=120, fg_color="#16A34A",
                      hover_color="#15803D",
                      command=self._export).pack(side="right", padx=6)

        f = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        f.pack(fill="x", padx=24, pady=(0, 8))
        r1 = ctk.CTkFrame(f, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(r1, text="As on Date").pack(side="left", padx=(0, 6))
        self._date_entry = DateEntry(r1, initial_date=today_storage())
        self._date_entry.pack(side="left", padx=(0, 10))
        ctk.CTkButton(r1, text="Show", width=80, fg_color="#1B4FD8",
                      command=self._load).pack(side="left", padx=4)
        ctk.CTkButton(r1, text="All Dates", width=90, fg_color="#6B7280",
                      command=self._load_all).pack(side="left", padx=4)

        self._summary_lbl = ctk.CTkLabel(self, text="Select a date and click Show",
                                          font=ctk.CTkFont(size=12), text_color="#888")
        self._summary_lbl.pack(anchor="w", padx=28, pady=(0, 4))

        card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        hdr = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=6)
        hdr.pack(fill="x", padx=8, pady=(8, 0))
        COLS = [("Name", 340), ("Debit", 160), ("Credit", 160)]
        for col, w in COLS:
            ctk.CTkLabel(hdr, text=col, width=w,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=6)

        self._scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)

    def _load(self):
        date_val = self._date_entry.get() or None
        self._fetch_and_draw(date_val)

    def _load_all(self):
        self._date_entry.set("")
        self._fetch_and_draw(None)

    def _fetch_and_draw(self, date_val):
        for w in self._scroll.winfo_children():
            w.destroy()

        data = get_balance_report(self.db_path, as_on_date=date_val, fy_id=self.fy_id)
        vendors  = data["vendors"]
        expenses = data["expenses"]
        self._all_rows = vendors + expenses

        if not self._all_rows:
            ctk.CTkLabel(self._scroll, text="No balances found.", text_color="#999").pack(pady=20)
            self._summary_lbl.configure(text="No balances to display.", text_color="#888")
            return

        total_debit  = sum(r["debit"]  for r in self._all_rows)
        total_credit = sum(r["credit"] for r in self._all_rows)
        date_display = to_display(date_val) if date_val else "All dates"
        self._summary_lbl.configure(
            text=f"As on: {date_display}  |  "
                 f"Total Debit: {fmt(total_debit)}  |  Total Credit: {fmt(total_credit)}  |  "
                 f"{len(vendors)} vendor(s), {len(expenses)} expense head(s)",
            text_color="#1B2B6B"
        )

        if vendors:
            self._section_header("Vendors")
            for i, r in enumerate(vendors):
                self._draw_row(r, i)

        if expenses:
            self._section_header("Expense Heads")
            for i, r in enumerate(expenses):
                self._draw_row(r, i)

        foot = ctk.CTkFrame(self._scroll, fg_color="#1B2B6B", corner_radius=4)
        foot.pack(fill="x", pady=(6, 2))
        for val, w, color in [
            ("TOTAL", 340, "white"),
            (fmt(total_debit),  160, "#FFA07A"),
            (fmt(total_credit), 160, "#7FFFD4"),
        ]:
            ctk.CTkLabel(foot, text=val, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=color).pack(side="left", padx=4, pady=5)

    def _section_header(self, text):
        sh = ctk.CTkFrame(self._scroll, fg_color="#243A8A", corner_radius=4)
        sh.pack(fill="x", pady=(8, 1))
        ctk.CTkLabel(sh, text=text, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="white").pack(side="left", padx=12, pady=4)

    def _draw_row(self, r, i):
        bg = "#F8FAFF" if i % 2 == 0 else "white"
        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
        row.pack(fill="x", pady=1)
        dr_color = "#D97706" if r["debit"]  > 0 else "#BBBBBB"
        cr_color = "#1B4FD8" if r["credit"] > 0 else "#BBBBBB"
        dr_text = fmt(r["debit"])  if r["debit"]  > 0 else "-"
        cr_text = fmt(r["credit"]) if r["credit"] > 0 else "-"
        for val, w, color in [
            (r["name"], 340, "#333"),
            (dr_text,   160, dr_color),
            (cr_text,   160, cr_color),
        ]:
            ctk.CTkLabel(row, text=str(val), width=w,
                         font=ctk.CTkFont(size=11),
                         text_color=color).pack(side="left", padx=4, pady=4)

    def _export(self):
        if not self._all_rows:
            messagebox.showwarning("No Data", "Load a balance report first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Save Balance Report")
        if not path:
            return
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Balance"
            ws.append(["Name", "Debit", "Credit"])
            for r in self._all_rows:
                ws.append([r["name"],
                           r["debit"]  if r["debit"]  > 0 else "",
                           r["credit"] if r["credit"] > 0 else ""])
            wb.save(path)
            messagebox.showinfo("Exported", f"Balance report exported:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Error", f"Could not export:\n{ex}")

    def refresh(self):
        pass
