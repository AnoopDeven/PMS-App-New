"""Date utilities: DD-MM-YYYY display format, YYYY-MM-DD storage format."""
import tkinter as tk
import customtkinter as ctk
from datetime import date, timedelta
import calendar as cal_mod


def to_display(date_str):
    """YYYY-MM-DD  →  DD-MM-YYYY"""
    if not date_str:
        return ""
    try:
        d = date.fromisoformat(str(date_str))
        return d.strftime("%d-%m-%Y")
    except Exception:
        return str(date_str)


def to_storage(display_str):
    """DD-MM-YYYY  →  YYYY-MM-DD (for DB). Also accepts YYYY-MM-DD."""
    if not display_str:
        return ""
    s = display_str.strip()
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return s  # already YYYY-MM-DD
            if len(parts[2]) == 4:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return s


def today_display():
    return date.today().strftime("%d-%m-%Y")


def today_storage():
    return date.today().strftime("%Y-%m-%d")


class DateEntry(ctk.CTkFrame):
    """An entry widget with a calendar picker button.

    initial_date: YYYY-MM-DD or DD-MM-YYYY.  Pass "" for blank (no default).
                  Pass None to default to today.
    """
    def __init__(self, master, initial_date=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        if initial_date is None:
            display_val = today_display()
        elif initial_date == "":
            display_val = ""
        else:
            display_val = to_display(initial_date) if len(initial_date.split("-")[0]) == 4 else initial_date
        self._var = tk.StringVar(value=display_val)
        self._entry = ctk.CTkEntry(self, textvariable=self._var, width=110,
                                    placeholder_text="DD-MM-YYYY")
        self._entry.pack(side="left")
        ctk.CTkButton(self, text="\U0001F4C5", width=32, height=28,
                      fg_color="#1B4FD8", hover_color="#1440B0",
                      font=ctk.CTkFont(size=13),
                      command=self._open_picker).pack(side="left", padx=(4, 0))

    def get(self):
        """Return value in storage format YYYY-MM-DD, or '' if blank."""
        val = self._var.get().strip()
        if not val:
            return ""
        return to_storage(val)

    def get_display(self):
        return self._var.get().strip()

    def set(self, date_str):
        """Accept YYYY-MM-DD or DD-MM-YYYY or '' to clear."""
        if not date_str:
            self._var.set("")
            return
        self._var.set(to_display(date_str) if len(date_str.split("-")[0]) == 4 else date_str)

    def _open_picker(self):
        CalendarDialog(self, callback=lambda d: self._var.set(d))


class CalendarDialog(ctk.CTkToplevel):
    """Lightweight calendar popup. Returns date as DD-MM-YYYY to callback."""
    def __init__(self, master, callback):
        super().__init__(master)
        self.title("Pick Date")
        self.resizable(False, False)
        self.grab_set()
        self.callback = callback
        today = date.today()
        self._year = today.year
        self._month = today.month
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkButton(nav, text="◀", width=32, command=self._prev_month).pack(side="left")
        self._hdr = ctk.CTkLabel(nav, text="",
                                  font=ctk.CTkFont(size=13, weight="bold"),
                                  text_color="#1B2B6B", width=160)
        self._hdr.pack(side="left", expand=True)
        ctk.CTkButton(nav, text="▶", width=32, command=self._next_month).pack(side="right")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(padx=10, pady=(0, 10))

        for col, day in enumerate(["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]):
            ctk.CTkLabel(grid, text=day, width=36,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#1B4FD8").grid(row=0, column=col, padx=1, pady=2)

        self._hdr.configure(text=date(self._year, self._month, 1).strftime("%B %Y"))
        m_cal = cal_mod.monthcalendar(self._year, self._month)
        today = date.today()
        for r, week in enumerate(m_cal):
            for c, day_num in enumerate(week):
                if day_num == 0:
                    ctk.CTkLabel(grid, text="", width=36).grid(row=r + 1, column=c, padx=1, pady=1)
                else:
                    is_today = (day_num == today.day and
                                self._month == today.month and
                                self._year == today.year)
                    btn = ctk.CTkButton(
                        grid, text=str(day_num), width=36, height=30,
                        fg_color="#1B4FD8" if is_today else "white",
                        hover_color="#EEF2FF",
                        text_color="white" if is_today else "#333",
                        border_width=0,
                        font=ctk.CTkFont(size=11),
                        command=lambda d=day_num: self._pick(d)
                    )
                    btn.grid(row=r + 1, column=c, padx=1, pady=1)

    def _prev_month(self):
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._build()

    def _next_month(self):
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._build()

    def _pick(self, day_num):
        picked = date(self._year, self._month, day_num)
        self.callback(picked.strftime("%d-%m-%Y"))
        self.destroy()
