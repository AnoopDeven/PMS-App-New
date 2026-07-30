import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from date_utils import DateEntry, to_display, today_storage
from searchable_combo import SearchableComboBox
from database import (get_vendors, get_accounts, get_expense_heads,
                      create_voucher, get_voucher, update_voucher,
                      create_expense, get_pending_invoices, validate_fy_date,
                      get_vendor_remaining_ob, get_voucher_adjustments)
from pdf_generator import print_voucher_pdf


class VoucherEntryFrame(ctk.CTkFrame):
    def __init__(self, master, db_path, fy_id=None):
        super().__init__(master, fg_color="#F4F6FB")
        self.db_path = db_path
        self.fy_id = fy_id
        self._editing_id = None
        self._last_voucher_id = None
        self._last_expense_id = None
        self._adj_rows = []
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self._adj_rows = []

        ctk.CTkLabel(self, text="Payment",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=24, pady=(20, 4))

        # ── Top-level type row (Payment / Transfer) ────────────────────────
        type_row = ctk.CTkFrame(self, fg_color="transparent")
        type_row.pack(fill="x", padx=24, pady=(0, 4))
        self._vtype = tk.StringVar(value="payment")
        for lbl, val in [("Payment Voucher", "payment"), ("Internal Transfer", "transfer")]:
            ctk.CTkRadioButton(type_row, text=lbl, variable=self._vtype, value=val,
                               command=self._toggle_vtype,
                               font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 24))

        # ── Payee-type sub-row (Vendor / Expense Head) — only for Payment ──
        self._payee_row = ctk.CTkFrame(self, fg_color="#EEF2FF", corner_radius=8)
        self._payee_type = tk.StringVar(value="vendor")
        ctk.CTkLabel(self._payee_row, text="Pay To:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=(14, 8), pady=6)
        for lbl, val in [("Vendor", "vendor"), ("Expense Head", "expense_head")]:
            ctk.CTkRadioButton(self._payee_row, text=lbl, variable=self._payee_type, value=val,
                               command=self._toggle_payee,
                               font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 20), pady=6)
        self._payee_row.pack(fill="x", padx=24, pady=(0, 6))

        # ── Scrollable form area ───────────────────────────────────────────
        self._scroll_form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll_form.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        form = ctk.CTkFrame(self._scroll_form, fg_color="white", corner_radius=14)
        form.pack(fill="x")
        form.grid_columnconfigure((1, 3), weight=1)
        self._form = form
        kw = {"padx": 14, "pady": 8}

        # Row 0: Date, Amount
        ctk.CTkLabel(form, text="Date *",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", **kw)
        self._date_entry = DateEntry(form)
        self._date_entry.grid(row=0, column=1, sticky="w", **kw)

        ctk.CTkLabel(form, text="Amount *",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, sticky="w", **kw)
        self._amount_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._amount_var,
                     placeholder_text="0.00").grid(row=0, column=3, sticky="ew", **kw)

        # Row 1: Payee (vendor OR expense head) + From Account
        self._payee_lbl = ctk.CTkLabel(form, text="Vendor *",
                                        font=ctk.CTkFont(weight="bold"))
        self._payee_lbl.grid(row=1, column=0, sticky="w", **kw)

        # Vendor dropdown
        vendors = get_vendors(self.db_path, category="creditor")
        self._vendor_names = ["-- Select Vendor --"] + [v["name"] for v in vendors]
        self._vendor_ids   = [None] + [v["id"] for v in vendors]
        self._vendor_obs   = [None] + [v.get("opening_balance", 0) or 0 for v in vendors]
        self._vendor_var   = tk.StringVar(value="-- Select Vendor --")
        self._vendor_menu  = SearchableComboBox(form, values=self._vendor_names,
                                                textvariable=self._vendor_var,
                                                command=self._on_vendor_change, width=220)
        self._vendor_menu.grid(row=1, column=1, sticky="ew", **kw)

        # Expense Head dropdown (same grid cell — hidden initially)
        heads = get_expense_heads(self.db_path)
        self._head_names = ["-- Select Expense Head --"] + [h["name"] for h in heads]
        self._head_ids   = [None] + [h["id"] for h in heads]
        self._head_var   = tk.StringVar(value="-- Select Expense Head --")
        self._head_menu  = SearchableComboBox(form, values=self._head_names,
                                              textvariable=self._head_var, width=220)
        # initially hidden — will be grid/grid_remove toggled
        self._head_menu.grid(row=1, column=1, sticky="ew", **kw)
        self._head_menu.grid_remove()

        ctk.CTkLabel(form, text="From Account *",
                     font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, sticky="w", **kw)
        accounts = get_accounts(self.db_path)
        self._account_names = ["-- Select Account --"] + [a["name"] for a in accounts]
        self._account_ids   = [None] + [a["id"] for a in accounts]
        self._from_acc_var  = tk.StringVar(value="-- Select Account --")
        self._from_acc_menu = SearchableComboBox(form, values=self._account_names,
                                                 textvariable=self._from_acc_var, width=220)
        self._from_acc_menu.grid(row=1, column=3, sticky="ew", **kw)

        # Row 2: To Account (transfer only) + Payment Mode
        self._to_lbl = ctk.CTkLabel(form, text="To Account *",
                                     font=ctk.CTkFont(weight="bold"))
        self._to_lbl.grid(row=2, column=0, sticky="w", **kw)
        self._to_acc_var  = tk.StringVar(value="-- Select Account --")
        self._to_acc_menu = SearchableComboBox(form, values=self._account_names,
                                               textvariable=self._to_acc_var, width=220)
        self._to_acc_menu.grid(row=2, column=1, sticky="ew", **kw)

        self._pm_lbl = ctk.CTkLabel(form, text="Payment Mode",
                                     font=ctk.CTkFont(weight="bold"))
        self._pm_lbl.grid(row=2, column=2, sticky="w", **kw)
        self._pm_var  = tk.StringVar(value="Cash")
        self._pm_menu = ctk.CTkOptionMenu(form,
                                           values=["Cash", "Cheque", "NEFT", "RTGS", "UPI", "Other"],
                                           variable=self._pm_var)
        self._pm_menu.grid(row=2, column=3, sticky="ew", **kw)

        # Row 3: Narration
        ctk.CTkLabel(form, text="Narration",
                     font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", **kw)
        self._narration_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._narration_var).grid(
            row=3, column=1, columnspan=3, sticky="ew", **kw)

        # Row 4: Receiver Name (vendor payments only)
        self._recv_lbl = ctk.CTkLabel(form, text="Receiver Name")
        self._recv_lbl.grid(row=4, column=0, sticky="w", **kw)
        self._receiver_var = tk.StringVar()
        self._recv_entry = ctk.CTkEntry(form, textvariable=self._receiver_var)
        self._recv_entry.grid(row=4, column=1, sticky="ew", **kw)

        # Row 5-6: Signature fields (vendor payments only)
        self._sig_widgets = []
        for r, (lbl1, v1, lbl2, v2) in enumerate([
            ("Prepared By",  "_prepared_var",  "Processed By", "_processed_var"),
            ("Authorized By","_authorized_var", "",             None),
        ], start=5):
            l = ctk.CTkLabel(form, text=lbl1)
            l.grid(row=r, column=0, sticky="w", **kw)
            setattr(self, v1, tk.StringVar())
            e = ctk.CTkEntry(form, textvariable=getattr(self, v1))
            e.grid(row=r, column=1, sticky="ew", **kw)
            self._sig_widgets += [l, e]
            if lbl2:
                l2 = ctk.CTkLabel(form, text=lbl2)
                l2.grid(row=r, column=2, sticky="w", **kw)
                self._sig_widgets.append(l2)
            if v2:
                setattr(self, v2, tk.StringVar())
                e2 = ctk.CTkEntry(form, textvariable=getattr(self, v2))
                e2.grid(row=r, column=3, sticky="ew", **kw)
                self._sig_widgets.append(e2)

        # ── Invoice + Opening Balance adjustment panel ────────────────────
        self._adj_panel = ctk.CTkFrame(self._scroll_form, fg_color="white", corner_radius=14)
        self._adj_panel_visible = False
        ctk.CTkLabel(self._adj_panel,
                     text="Adjust Against Pending Invoices / Opening Balance",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=14, pady=(12, 4))
        self._adj_info = ctk.CTkLabel(self._adj_panel, text="",
                                       text_color="#555", font=ctk.CTkFont(size=12))
        self._adj_info.pack(anchor="w", padx=14)
        self._adj_scroll = ctk.CTkScrollableFrame(self._adj_panel, fg_color="transparent", height=160)
        self._adj_scroll.pack(fill="x", padx=12, pady=(4, 12))

        # Buttons
        btn_row = ctk.CTkFrame(self._scroll_form, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="Clear", width=90, fg_color="#6B7280",
                      command=self._clear_form).pack(side="left", padx=8)
        self._submit_btn = ctk.CTkButton(btn_row, text="Save Payment", width=130,
                                          fg_color="#1B4FD8", hover_color="#1440B0",
                                          command=self._submit)
        self._submit_btn.pack(side="left", padx=8)
        self._print_btn = ctk.CTkButton(btn_row, text="Print PDF", width=110,
                                         fg_color="#7C3AED", hover_color="#6D28D9",
                                         command=self._print_pdf, state="disabled")
        self._print_btn.pack(side="left", padx=8)

        self._saved_label = ctk.CTkLabel(self._scroll_form, text="",
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          text_color="#16A34A")
        self._saved_label.pack(pady=4)

        self._toggle_vtype()

    # ── Toggle helpers ────────────────────────────────────────────────────────
    def _toggle_vtype(self):
        vtype = self._vtype.get()
        if vtype == "payment":
            self._payee_row.pack(fill="x", padx=24, pady=(0, 6))
            self._to_acc_menu.configure(state="disabled")
            self._pm_menu.configure(state="normal")
            self._toggle_payee()
        else:
            # Internal transfer — hide payee row and adj panel
            self._payee_row.pack_forget()
            self._vendor_menu.configure(state="disabled")
            self._head_menu.configure(state="disabled")
            self._to_acc_menu.configure(state="normal")
            self._pm_menu.configure(state="normal")
            self._hide_adj_panel()
            self._payee_lbl.configure(text="To Account *")
            self._show_sig_widgets(True)

    def _toggle_payee(self):
        ptype = self._payee_type.get()
        if ptype == "vendor":
            self._vendor_menu.grid()
            self._head_menu.grid_remove()
            self._vendor_menu.configure(state="normal")
            self._head_menu.configure(state="disabled")
            self._payee_lbl.configure(text="Vendor *")
            self._show_sig_widgets(True)
            # re-trigger vendor adj panel if vendor already selected
            if self._get_vendor_id():
                self._show_adj_panel(self._get_vendor_id())
        else:
            self._head_menu.grid()
            self._vendor_menu.grid_remove()
            self._head_menu.configure(state="normal")
            self._vendor_menu.configure(state="disabled")
            self._payee_lbl.configure(text="Expense Head *")
            self._hide_adj_panel()
            self._vendor_menu.set("-- Select Vendor --")
            self._show_sig_widgets(False)

    def _show_sig_widgets(self, show):
        for w in self._sig_widgets:
            if show:
                try:
                    w.grid()
                except Exception:
                    pass
            else:
                try:
                    w.grid_remove()
                except Exception:
                    pass
        if show:
            self._recv_lbl.grid()
            self._recv_entry.grid()
        else:
            self._recv_lbl.grid_remove()
            self._recv_entry.grid_remove()

    # ── Vendor / adj panel ────────────────────────────────────────────────────
    def _on_vendor_change(self, val):
        vid = self._get_vendor_id()
        if not vid:
            self._hide_adj_panel()
        else:
            self._show_adj_panel(vid)

    def _show_adj_panel(self, vendor_id, prev_inv_adjs=None, prev_ob_adj=0):
        """Show adjustment panel.
        prev_inv_adjs: dict {purchase_id: amount} of already-applied adjustments (for edit mode).
        prev_ob_adj: OB amount previously applied (for edit mode).
        """
        if not self._adj_panel_visible:
            self._adj_panel.pack(fill="x", pady=(8, 0))
            self._adj_panel_visible = True
        for w in self._adj_scroll.winfo_children():
            w.destroy()
        self._adj_rows = []
        prev_inv_adjs = prev_inv_adjs or {}

        # Remaining OB from DB (does not include already-reversed amounts from the edit)
        ob = get_vendor_remaining_ob(self.db_path, vendor_id) + prev_ob_adj

        # Pending invoices; for edited voucher, add back previously applied amounts
        invoices = get_pending_invoices(self.db_path, vendor_id)
        # Restore outstanding for invoices that had prior adjustments (already reversed in DB)
        inv_map = {inv["id"]: inv for inv in invoices}
        # Also include invoices that were fully paid (outstanding=0) if they had prior adj
        for pid, amt in prev_inv_adjs.items():
            if pid in inv_map:
                inv_map[pid]["outstanding"] += amt
            else:
                # Fetch the purchase to show it even if outstanding is 0
                from database import get_purchase
                p = get_purchase(self.db_path, pid)
                if p:
                    p["outstanding"] = amt
                    p["display_label"] = p.get("invoice_number") or p["voucher_no"]
                    inv_map[pid] = p
                    invoices.append(p)

        has_items = bool(invoices) or ob > 0
        if not has_items:
            self._adj_info.configure(
                text="No pending invoices or opening balance — payment treated as Advance.")
            return

        self._adj_info.configure(text="Check items to adjust. Unchecked amounts treated as Advance.")

        h = ctk.CTkFrame(self._adj_scroll, fg_color="#EEF2FF", corner_radius=4)
        h.pack(fill="x", pady=2)
        for width, lbl in zip([16, 210, 120, 130],
                               ["", "Invoice / Ref  [Inv Date]", "Outstanding", "Adjust Amt"]):
            ctk.CTkLabel(h, text=lbl, width=width,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#1B2B6B").pack(side="left", padx=4, pady=4)

        if ob > 0:
            row_f = ctk.CTkFrame(self._adj_scroll, fg_color="#FFF8E7", corner_radius=4)
            row_f.pack(fill="x", pady=1)
            pre_checked = prev_ob_adj > 0
            check_var = tk.BooleanVar(value=pre_checked)
            amt_var = tk.StringVar(value=str(prev_ob_adj if pre_checked else ob))
            ctk.CTkCheckBox(row_f, text="", variable=check_var, width=16).pack(side="left", padx=4)
            ctk.CTkLabel(row_f, text="Opening Balance", width=150,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#D97706").pack(side="left", padx=4, pady=4)
            ctk.CTkLabel(row_f, text=f"\u20b9{ob:,.2f}", width=120,
                         font=ctk.CTkFont(size=11), text_color="#D97706").pack(side="left", padx=4, pady=4)
            ctk.CTkEntry(row_f, textvariable=amt_var, width=120).pack(side="left", padx=4)
            self._adj_rows.append({"purchase_id": None, "is_opening_balance": True,
                                   "check_var": check_var, "amt_var": amt_var})

        for inv in invoices:
            row_f = ctk.CTkFrame(self._adj_scroll, fg_color="white", corner_radius=4)
            row_f.pack(fill="x", pady=1)
            pid = inv["id"]
            pre_amt = prev_inv_adjs.get(pid, 0)
            pre_checked = pre_amt > 0
            check_var = tk.BooleanVar(value=pre_checked)
            amt_var = tk.StringVar(value=str(pre_amt if pre_checked else inv["outstanding"]))
            ctk.CTkCheckBox(row_f, text="", variable=check_var, width=16).pack(side="left", padx=4)
            label = inv.get("display_label") or inv.get("voucher_no", "")
            ctk.CTkLabel(row_f, text=label[:30], width=210,
                         font=ctk.CTkFont(size=11)).pack(side="left", padx=4, pady=4)
            ctk.CTkLabel(row_f, text=f"\u20b9{inv['outstanding']:,.2f}", width=120,
                         font=ctk.CTkFont(size=11), text_color="#D97706").pack(side="left", padx=4, pady=4)
            ctk.CTkEntry(row_f, textvariable=amt_var, width=120).pack(side="left", padx=4)
            self._adj_rows.append({"purchase_id": pid, "is_opening_balance": False,
                                   "check_var": check_var, "amt_var": amt_var})

    def _hide_adj_panel(self):
        if self._adj_panel_visible:
            self._adj_panel.pack_forget()
            self._adj_panel_visible = False
        self._adj_rows = []

    # ── Getters ───────────────────────────────────────────────────────────────
    def _get_vendor_id(self):
        name = self._vendor_var.get()
        try:
            idx = self._vendor_names.index(name)
            return self._vendor_ids[idx]
        except ValueError:
            return None

    def _get_vendor_ob(self, vendor_id):
        try:
            idx = self._vendor_ids.index(vendor_id)
            return self._vendor_obs[idx] or 0
        except (ValueError, IndexError):
            return 0

    def _get_head_id(self):
        name = self._head_var.get()
        try:
            idx = self._head_names.index(name)
            return self._head_ids[idx]
        except ValueError:
            return None

    def _get_account_id(self, var):
        name = var.get()
        try:
            idx = self._account_names.index(name)
            return self._account_ids[idx]
        except ValueError:
            return None

    def _get_adjustments(self):
        result = []
        for row in self._adj_rows:
            if row["check_var"].get():
                try:
                    amt = float(row["amt_var"].get() or 0)
                    if amt > 0:
                        result.append({
                            "purchase_id": row.get("purchase_id"),
                            "is_opening_balance": row.get("is_opening_balance", False),
                            "amount": amt,
                        })
                except ValueError:
                    pass
        return result

    # ── Submit ────────────────────────────────────────────────────────────────
    def _submit(self):
        vtype = self._vtype.get()
        date_str = self._date_entry.get()
        if not date_str:
            messagebox.showerror("Error", "Date is required.")
            return
        valid, err = validate_fy_date(self.db_path, date_str, self.fy_id)
        if not valid:
            messagebox.showerror("Date Out of Range", err)
            return
        try:
            amount = float(self._amount_var.get() or 0)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid positive amount.")
            return

        from_acc_id = self._get_account_id(self._from_acc_var)
        if not from_acc_id:
            messagebox.showerror("Error", "Select a From Account.")
            return

        # ── Expense Head payment ─────────────────────────────────────────
        if vtype == "payment" and self._payee_type.get() == "expense_head":
            head_id = self._get_head_id()
            if not head_id:
                messagebox.showerror("Error", "Select an Expense Head.")
                return
            narration = self._narration_var.get().strip()
            eid, vno = create_expense(self.db_path, date_str, head_id, from_acc_id,
                                      amount, narration, self._pm_var.get())
            self._last_expense_id = eid
            self._last_voucher_id = None
            self._saved_label.configure(text=f"Expense #{vno} saved successfully!")
            self._print_btn.configure(state="disabled")
            self._clear_form(keep_type=True)
            return

        # ── Vendor payment / Internal Transfer ──────────────────────────
        vendor_id = to_acc_id = None
        if vtype == "payment":
            vendor_id = self._get_vendor_id()
            if not vendor_id:
                messagebox.showerror("Error", "Select a Vendor.")
                return
        else:
            to_acc_id = self._get_account_id(self._to_acc_var)
            if not to_acc_id:
                messagebox.showerror("Error", "Select a To Account.")
                return
            if from_acc_id == to_acc_id:
                messagebox.showerror("Error", "From and To accounts must differ.")
                return

        adjustments = self._get_adjustments() if vtype == "payment" else None

        kwargs = dict(
            vtype=vtype, date_str=date_str, vendor_id=vendor_id,
            from_account_id=from_acc_id, to_account_id=to_acc_id,
            payment_mode=self._pm_var.get(),
            amount=amount,
            narration=self._narration_var.get().strip(),
            receiver_name=self._receiver_var.get().strip(),
            prepared_by=self._prepared_var.get().strip(),
            processed_by=self._processed_var.get().strip(),
            authorized_by=self._authorized_var.get().strip(),
            adjustments=adjustments,
        )

        if self._editing_id:
            update_voucher(self.db_path, self._editing_id,
                           date=date_str, vendor_id=vendor_id,
                           from_account_id=from_acc_id, to_account_id=to_acc_id,
                           payment_mode=self._pm_var.get(), amount=amount,
                           narration=kwargs["narration"], receiver_name=kwargs["receiver_name"],
                           prepared_by=kwargs["prepared_by"],
                           processed_by=kwargs["processed_by"],
                           authorized_by=kwargs["authorized_by"],
                           adjustments=adjustments)
            vid = self._editing_id
            self._editing_id = None
            self._submit_btn.configure(text="Save Payment")
            v = get_voucher(self.db_path, vid)
            voucher_no = v["voucher_no"]
        else:
            vid, voucher_no = create_voucher(self.db_path, **kwargs)

        self._last_voucher_id = vid
        self._last_expense_id = None
        self._saved_label.configure(text=f"Voucher #{voucher_no} saved successfully!")
        self._print_btn.configure(state="normal")
        self._clear_form(keep_type=True)

    # ── Print PDF ─────────────────────────────────────────────────────────────
    def _print_pdf(self):
        if self._last_voucher_id:
            v = get_voucher(self.db_path, self._last_voucher_id)
            if v:
                entity_name = ""
                try:
                    from database import get_meta
                    entity_name = get_meta(self.db_path, "entity_name", "")
                except Exception:
                    pass
                print_voucher_pdf(v, entity_name=entity_name)

    # ── Clear ─────────────────────────────────────────────────────────────────
    def _clear_form(self, keep_type=False):
        self._date_entry.set(today_storage())
        self._amount_var.set("")
        self._vendor_menu.set("-- Select Vendor --")
        self._head_menu.set("-- Select Expense Head --")
        self._from_acc_menu.set("-- Select Account --")
        self._to_acc_menu.set("-- Select Account --")
        self._pm_var.set("Cash")
        self._narration_var.set("")
        self._receiver_var.set("")
        self._prepared_var.set("")
        self._processed_var.set("")
        self._authorized_var.set("")
        self._editing_id = None
        self._submit_btn.configure(text="Save Payment")
        self._saved_label.configure(text="")
        self._hide_adj_panel()

    # ── Load for edit (vendor vouchers only) ─────────────────────────────────
    def load_for_edit(self, voucher_id):
        v = get_voucher(self.db_path, voucher_id)
        if not v:
            return
        self._editing_id = voucher_id
        self._vtype.set(v["type"])
        self._payee_type.set("vendor")
        self._toggle_vtype()
        self._date_entry.set(v["date"])
        self._amount_var.set(str(v["amount"]))
        self._narration_var.set(v["narration"] or "")
        self._receiver_var.set(v["receiver_name"] or "")
        self._prepared_var.set(v["prepared_by"] or "")
        self._processed_var.set(v["processed_by"] or "")
        self._authorized_var.set(v["authorized_by"] or "")
        self._pm_var.set(v["payment_mode"] or "Cash")
        if v.get("vendor_id"):
            idx = next((i for i, x in enumerate(self._vendor_ids) if x == v["vendor_id"]), -1)
            if idx >= 0:
                self._vendor_menu.set(self._vendor_names[idx])
        if v.get("from_account_id"):
            idx = next((i for i, x in enumerate(self._account_ids) if x == v["from_account_id"]), -1)
            if idx >= 0:
                self._from_acc_menu.set(self._account_names[idx])
        if v.get("to_account_id"):
            idx = next((i for i, x in enumerate(self._account_ids) if x == v["to_account_id"]), -1)
            if idx >= 0:
                self._to_acc_menu.set(self._account_names[idx])
        self._submit_btn.configure(text="Update Voucher")
        # Pre-populate adjustment panel with previous adjustments
        if v.get("vendor_id") and v.get("type") == "payment":
            adjs = get_voucher_adjustments(self.db_path, voucher_id)
            self._show_adj_panel(v["vendor_id"],
                                 prev_inv_adjs=adjs["invoice_adjustments"],
                                 prev_ob_adj=adjs["ob_adjustment"])

    def refresh(self):
        self._build()
