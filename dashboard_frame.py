import tkinter as tk
import customtkinter as ctk
from database import get_dashboard_stats
from date_utils import to_display


def fmt(v):
    return f"\u20b9{float(v):,.2f}"


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, value, color, sub=""):
        super().__init__(master, fg_color=color, corner_radius=14)
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=11),
                     text_color="white").pack(anchor="w", padx=14, pady=(12, 1))
        ctk.CTkLabel(self, text=value, font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="white").pack(anchor="w", padx=14, pady=(0, 2))
        if sub:
            ctk.CTkLabel(self, text=sub, font=ctk.CTkFont(size=10),
                         text_color="#FFFFFFAA").pack(anchor="w", padx=14, pady=(0, 10))


class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        ctk.CTkLabel(self, text="Dashboard",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=28, pady=(22, 6))

        stats = get_dashboard_stats(self.db_path, self.fy_id)

        # ── Stat cards ─────────────────────────────────────────
        cards_row = ctk.CTkFrame(self, fg_color="transparent")
        cards_row.pack(fill="x", padx=24, pady=8)
        cards_row.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        card_data = [
            ("Total Vouchers",   str(stats["total_vouchers"]),    "#1B4FD8", ""),
            ("Payments",         fmt(stats["total_payments"]),     "#16A34A", ""),
            ("Purchases",        fmt(stats["total_purchases"]),    "#D97706", ""),
            ("Transfers",        fmt(stats["total_transfers"]),    "#7C3AED", ""),
            ("Vendors",          str(stats["vendor_count"]),       "#0891B2", ""),
            ("Accounts",         str(stats["account_count"]),      "#6366F1", ""),
        ]
        for col, (title, value, color, sub) in enumerate(card_data):
            c = StatCard(cards_row, title, value, color, sub)
            c.grid(row=0, column=col, padx=6, sticky="ew")

        # ── Bar chart ──────────────────────────────────────────
        chart_card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        chart_card.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(chart_card, text="Monthly Payments",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=16, pady=(14, 6))

        monthly = stats.get("monthly_payments", [])
        if monthly:
            self._draw_chart(chart_card, monthly)
        else:
            ctk.CTkLabel(chart_card, text="No payment data yet.",
                         text_color="#999").pack(pady=20)

        # ── Recent transactions ────────────────────────────────
        rec_card = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        rec_card.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        ctk.CTkLabel(rec_card, text="Recent Vouchers",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=16, pady=(14, 4))

        headers = ["Voucher No", "Date", "Type", "Vendor / Account", "Amount"]
        widths = [100, 100, 100, 260, 130]
        h_row = ctk.CTkFrame(rec_card, fg_color="#EEF2FF", corner_radius=6)
        h_row.pack(fill="x", padx=12)
        for w, h in zip(widths, headers):
            ctk.CTkLabel(h_row, text=h, width=w,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=6, pady=6)

        scroll = ctk.CTkScrollableFrame(rec_card, fg_color="transparent", height=150)
        scroll.pack(fill="both", expand=True, padx=12, pady=4)

        recent = stats.get("recent_vouchers", [])
        if not recent:
            ctk.CTkLabel(scroll, text="No vouchers yet.", text_color="#999").pack(pady=12)
        for i, v in enumerate(recent):
            bg = "#F8FAFF" if i % 2 == 0 else "white"
            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            party = v.get("vendor_name") or v.get("from_account_name") or "-"
            vals = [v["voucher_no"], to_display(v["date"]), v["type"].title(), party, fmt(v["amount"])]
            for w, val in zip(widths, vals):
                ctk.CTkLabel(row, text=str(val), width=w,
                             font=ctk.CTkFont(size=12),
                             text_color="#333").pack(side="left", padx=6, pady=5)

    def _draw_chart(self, parent, monthly):
        canvas = tk.Canvas(parent, height=120, bg="white", highlightthickness=0, bd=0)
        canvas.pack(fill="x", padx=16, pady=(0, 14))

        def draw(event=None):
            canvas.delete("all")
            cw = canvas.winfo_width() or 700
            max_val = max(m["total"] for m in monthly) or 1
            n = len(monthly)
            bar_top, bar_bottom = 10, 95
            bar_h_max = bar_bottom - bar_top
            slot_w = cw / max(n, 1)
            bar_w = max(slot_w * 0.55, 12)
            for i, m in enumerate(monthly):
                bh = max((m["total"] / max_val) * bar_h_max, 2)
                x0 = i * slot_w + (slot_w - bar_w) / 2
                x1 = x0 + bar_w
                canvas.create_rectangle(x0, bar_bottom - bh, x1, bar_bottom,
                                        fill="#1B4FD8", outline="")
                label = m["month"][5:] if len(m["month"]) >= 7 else m["month"]
                canvas.create_text((x0 + x1) / 2, bar_bottom + 10,
                                   text=label, font=("Helvetica", 8), fill="#555")

        canvas.bind("<Configure>", draw)
        canvas.after(60, draw)

    def refresh(self):
        self._build()
