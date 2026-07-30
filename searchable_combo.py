"""SearchableComboBox — drop-in replacement for CTkOptionMenu with live search.

API mirrors CTkOptionMenu:
    widget = SearchableComboBox(parent, values=[...], width=200,
                                textvariable=tk_var,   # optional
                                command=callback,      # called with selected str
                                placeholder="-- Select --")
    widget.get()                    -> currently selected string ("" if nothing chosen)
    widget.set("value")             -> programmatically select; "-- ..." prefix clears
    widget.configure(values=[...])  -> update option list
    widget.configure(state="disabled" | "normal")
    widget.grid(...) / widget.pack(...) work normally
"""

import tkinter as tk
import customtkinter as ctk

_PLACEHOLDER_PREFIX = "-- "


class SearchableComboBox(ctk.CTkFrame):
    def __init__(self, master, values=None, textvariable=None,
                 command=None, width=220, placeholder="-- Select --",
                 state="normal", **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, fg_color="transparent", **{
            k: v for k, v in kwargs.items()
            if k not in ("fg_color",)
        })

        self._all_values = [v for v in (values or [])
                            if not str(v).startswith(_PLACEHOLDER_PREFIX)]
        self._textvariable = textvariable
        self._command = command
        self._width = width
        self._placeholder = placeholder
        self._state = state
        self._popup = None
        self._filtered = []
        self._listbox = None
        self._selected = ""

        self._entry_var = tk.StringVar(value="")

        self._build(width)
        if state == "disabled":
            self._set_state("disabled")

    # ── Build ───────────────────────────────────────────────────────────────

    def _build(self, width):
        entry_w = max(width - 34, 40)
        self._entry = ctk.CTkEntry(
            self, textvariable=self._entry_var,
            width=entry_w, height=34,
            fg_color="white", border_color="#CBD5E1",
            text_color="#111827",
            font=ctk.CTkFont(size=12),
            placeholder_text="Type to search…"
        )
        self._entry.grid(row=0, column=0, sticky="ew")

        self._btn = ctk.CTkButton(
            self, text="▼", width=32, height=34,
            fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#374151", corner_radius=6,
            command=self._toggle_popup
        )
        self._btn.grid(row=0, column=1, padx=(2, 0))

        self._entry.bind("<FocusIn>",  lambda e: self._open_popup())
        self._entry_var.trace_add("write", self._on_type)
        self._entry.bind("<Down>",    self._kbd_down)
        self._entry.bind("<Up>",      self._kbd_up)
        self._entry.bind("<Return>",  self._kbd_enter)
        self._entry.bind("<Escape>",  lambda e: self._close_popup())

    # ── Public API ───────────────────────────────────────────────────────────

    def get(self):
        return self._selected

    def set(self, value):
        if not value or str(value).startswith(_PLACEHOLDER_PREFIX):
            self._selected = ""
            self._entry_var.set("")
            if self._textvariable:
                self._textvariable.set("")
        else:
            self._selected = value
            self._entry_var.set(value)
            if self._textvariable:
                self._textvariable.set(value)

    def configure(self, **kwargs):
        if "values" in kwargs:
            raw = list(kwargs.pop("values"))
            self._all_values = [v for v in raw
                                if not str(v).startswith(_PLACEHOLDER_PREFIX)]
            if self._popup and self._popup.winfo_exists():
                self._refresh_list()
        if "state" in kwargs:
            self._set_state(kwargs.pop("state"))
        if "width" in kwargs:
            self._width = kwargs.pop("width")
        if kwargs:
            try:
                super().configure(**kwargs)
            except Exception:
                pass

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _set_state(self, state):
        self._state = state
        entry_state = "disabled" if state == "disabled" else "normal"
        btn_state   = "disabled" if state == "disabled" else "normal"
        self._entry.configure(state=entry_state)
        self._btn.configure(state=btn_state)

    def _filtered_values(self):
        q = self._entry_var.get().lower().strip()
        if not q:
            return list(self._all_values)
        return [v for v in self._all_values if q in v.lower()]

    # ── Popup lifecycle ──────────────────────────────────────────────────────

    def _toggle_popup(self):
        if self._state == "disabled":
            return
        if self._popup and self._popup.winfo_exists():
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self):
        if self._state == "disabled":
            return
        items = self._filtered_values()
        if not items:
            return
        if self._popup and self._popup.winfo_exists():
            self._refresh_list()
            return

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        w = self._width

        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.configure(bg="#CBD5E1")
        self._popup.geometry(f"{w}x10+{x}+{y}")
        self._popup.lift()

        inner = tk.Frame(self._popup, bg="white")
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        sb = tk.Scrollbar(inner, orient="vertical")
        self._listbox = tk.Listbox(
            inner,
            yscrollcommand=sb.set,
            selectmode="single",
            font=("Segoe UI", 15),
            bg="white", fg="#111827",
            selectbackground="#1B4FD8",
            selectforeground="white",
            relief="flat", borderwidth=0,
            activestyle="none",
            highlightthickness=0,
            cursor="hand2"
        )
        sb.config(command=self._listbox.yview)
        self._listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._listbox.bind("<<ListboxSelect>>", self._on_lb_select)
        self._listbox.bind("<Return>",           self._kbd_enter)
        self._listbox.bind("<Escape>",           lambda e: self._close_popup())

        self._refresh_list()

        self._bind_id = self.winfo_toplevel().bind(
            "<Button-1>", self._on_outside_click, add="+"
        )

    def _refresh_list(self):
        if not self._popup or not self._popup.winfo_exists():
            return
        self._listbox.delete(0, "end")
        items = self._filtered_values()
        self._filtered = items
        for item in items:
            self._listbox.insert("end", f"  {item}")

        n   = min(len(items), 10)
        h   = max(n * 44 + 6, 50)
        w   = max(self._width, 280)
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        self._popup.geometry(f"{w}x{h}+{x}+{y}")

    def _close_popup(self):
        if self._popup and self._popup.winfo_exists():
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._bind_id)
            except Exception:
                pass
            self._popup.destroy()
        self._popup = None
        self._listbox = None

    # ── Event handlers ───────────────────────────────────────────────────────

    def _on_type(self, *_):
        if self._popup and self._popup.winfo_exists():
            self._refresh_list()
        else:
            self.after(50, lambda: (
                self._open_popup()
                if self._state != "disabled" else None
            ))

    def _on_lb_select(self, event):
        if not self._listbox:
            return
        sel = self._listbox.curselection()
        if sel:
            raw = self._listbox.get(sel[0]).strip()
            self._select(raw)

    def _select(self, value):
        self._selected = value
        self._entry_var.set(value)
        if self._textvariable:
            self._textvariable.set(value)
        if self._command:
            self._command(value)
        self._close_popup()

    def _on_outside_click(self, event):
        try:
            if not self._popup or not self._popup.winfo_exists():
                return
            px, py = self._popup.winfo_rootx(), self._popup.winfo_rooty()
            pw, ph = self._popup.winfo_width(), self._popup.winfo_height()
            wx, wy = self.winfo_rootx(), self.winfo_rooty()
            ww, wh = self.winfo_width(), self.winfo_height()
            ex, ey = event.x_root, event.y_root
            in_popup  = px <= ex <= px + pw and py <= ey <= py + ph
            in_widget = wx <= ex <= wx + ww and wy <= ey <= wy + wh
            if not in_popup and not in_widget:
                self._close_popup()
        except Exception:
            self._close_popup()

    def _kbd_down(self, event):
        if not self._popup or not self._popup.winfo_exists():
            self._open_popup()
            return "break"
        cur = self._listbox.curselection()
        nxt = (cur[0] + 1) if cur else 0
        nxt = min(nxt, self._listbox.size() - 1)
        self._listbox.selection_clear(0, "end")
        self._listbox.selection_set(nxt)
        self._listbox.see(nxt)
        return "break"

    def _kbd_up(self, event):
        if not self._popup or not self._popup.winfo_exists():
            return "break"
        cur = self._listbox.curselection()
        if cur:
            prv = max(cur[0] - 1, 0)
            self._listbox.selection_clear(0, "end")
            self._listbox.selection_set(prv)
            self._listbox.see(prv)
        return "break"

    def _kbd_enter(self, event):
        if not self._popup or not self._popup.winfo_exists():
            return
        sel = self._listbox.curselection()
        if sel:
            raw = self._listbox.get(sel[0]).strip()
            self._select(raw)
        return "break"
