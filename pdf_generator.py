import os
import subprocess
import sys
from tkinter import messagebox, filedialog


def _open_file(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception:
        pass


def _get_rl():
    try:
        from reportlab.lib.pagesizes import A5
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        return True, (A5, colors, mm, SimpleDocTemplate, Table, TableStyle,
                      Paragraph, Spacer, getSampleStyleSheet, ParagraphStyle,
                      TA_CENTER, TA_LEFT)
    except ImportError:
        messagebox.showerror("Missing Library",
                             "reportlab not installed.\nRun: pip install reportlab")
        return False, None


def print_voucher_pdf(voucher: dict, entity_name: str = ""):
    ok, mods = _get_rl()
    if not ok:
        return
    (A5, colors, mm, SimpleDocTemplate, Table, TableStyle,
     Paragraph, Spacer, getSS, PS, TA_CENTER, TA_LEFT) = mods

    vno = voucher["voucher_no"]
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
        initialfile=f"Voucher_{vno}.pdf", title="Save Voucher PDF"
    )
    if not path:
        return

    try:
        doc = SimpleDocTemplate(path, pagesize=A5,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=12*mm, bottomMargin=12*mm)
        styles = getSS()
        T = lambda text, style: Paragraph(text, style)

        def ps(name, **kw):
            return PS(name, parent=styles["Normal"], **kw)

        title_s = ps("t", fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=2*mm)
        sub_s   = ps("s", fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=5*mm)
        lbl_s   = ps("l", fontSize=9,  fontName="Helvetica-Bold")
        val_s   = ps("v", fontSize=9)
        ftr_s   = ps("f", fontSize=8,  alignment=TA_CENTER, textColor=colors.grey)

        story = []

        # Entity + title
        if entity_name:
            story.append(T(entity_name, ps("en", fontSize=12, fontName="Helvetica-Bold",
                                            alignment=TA_CENTER, spaceAfter=2*mm)))
        vtype = "PAYMENT VOUCHER" if voucher["type"] == "payment" else "INTERNAL TRANSFER"
        story.append(T(vtype, title_s))
        story.append(T(f"Voucher No: {vno}", sub_s))

        def row(lbl, val):
            return [T(lbl, lbl_s), T(str(val or "-"), val_s)]

        detail = [row("Date:", voucher["date"]),
                  row("Amount:", f"\u20b9{float(voucher['amount']):,.2f}")]

        if voucher["type"] == "payment":
            detail += [
                row("Vendor:", voucher.get("vendor_name") or "-"),
                row("Paid From:", voucher.get("from_account_name") or "-"),
                row("Payment Mode:", voucher.get("payment_mode") or "-"),
            ]
            if voucher.get("receiver_name"):
                detail.append(row("Receiver:", voucher["receiver_name"]))
        else:
            detail += [
                row("From Account:", voucher.get("from_account_name") or "-"),
                row("Payment Mode:", voucher.get("payment_mode") or "-"),
                row("To Account:", voucher.get("to_account_name") or "-"),
            ]

        if voucher.get("narration"):
            detail.append(row("Narration:", voucher["narration"]))

        dt = Table(detail, colWidths=[38*mm, None])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFF")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D8FF")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(dt)
        story.append(Spacer(1, 8*mm))

        # Signature block — name on top, line, then role label below
        sig_s  = ps("sg",  fontSize=9,  alignment=TA_CENTER, fontName="Helvetica-Bold")
        role_s = ps("rl",  fontSize=8,  alignment=TA_CENTER, textColor=colors.grey)
        line_s = ps("ln",  fontSize=9,  alignment=TA_CENTER)

        sig_cols = [
            (voucher.get("prepared_by") or "",   "Prepared By"),
            (voucher.get("processed_by") or "",  "Processed By"),
            (voucher.get("authorized_by") or "", "Authorized By"),
        ]
        if voucher["type"] == "payment":
            # Always include a dedicated line for the recipient to sign against,
            # regardless of whether a receiver name was entered on-screen.
            sig_cols.append((voucher.get("receiver_name") or "", "Receiver's Signature"))

        name_row = [T(name, sig_s)  for name, _ in sig_cols]
        line_row = [T("_" * 20, line_s) for _ in sig_cols]
        role_row = [T(role, role_s) for _, role in sig_cols]

        st = Table([name_row, line_row, role_row], colWidths=[None] * len(sig_cols))
        st.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "BOTTOM"),
            ("TOPPADDING",   (0, 1), (-1, 1),  10),
            ("BOTTOMPADDING",(0, 2), (-1, 2),  4),
        ]))
        story.append(st)
        story.append(Spacer(1, 5*mm))
        story.append(T("This is a computer-generated voucher.", ftr_s))

        doc.build(story)
        _open_file(path)
        messagebox.showinfo("PDF Saved", f"Voucher PDF saved:\n{path}")
    except Exception as ex:
        messagebox.showerror("PDF Error", f"Could not generate PDF:\n{ex}")


def print_expense_pdf(expense: dict, entity_name: str = ""):
    ok, mods = _get_rl()
    if not ok:
        return
    (A5, colors, mm, SimpleDocTemplate, Table, TableStyle,
     Paragraph, Spacer, getSS, PS, TA_CENTER, TA_LEFT) = mods

    vno = expense.get("voucher_no", "")
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
        initialfile=f"Expense_{vno}.pdf", title="Save Expense PDF"
    )
    if not path:
        return
    try:
        doc = SimpleDocTemplate(path, pagesize=A5,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=12*mm, bottomMargin=12*mm)
        styles = getSS()
        T = lambda text, style: Paragraph(text, style)

        def ps(name, **kw):
            return PS(name, parent=styles["Normal"], **kw)

        title_s = ps("t", fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=2*mm)
        sub_s   = ps("s", fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=5*mm)
        lbl_s   = ps("l", fontSize=9,  fontName="Helvetica-Bold")
        val_s   = ps("v", fontSize=9)
        ftr_s   = ps("f", fontSize=8,  alignment=TA_CENTER, textColor=colors.grey)

        def row(lbl, val):
            return [T(lbl, lbl_s), T(str(val or "-"), val_s)]

        story = []
        if entity_name:
            story.append(T(entity_name, ps("en", fontSize=12, fontName="Helvetica-Bold",
                                            alignment=TA_CENTER, spaceAfter=2*mm)))
        story.append(T("EXPENSE VOUCHER", title_s))
        story.append(T(f"Voucher No: {vno}", sub_s))

        raw_date = expense.get("date", "")
        if raw_date and len(raw_date) == 10:
            y, m, d = raw_date.split("-")
            disp_date = f"{d}/{m}/{y}"
        else:
            disp_date = raw_date

        detail = [
            row("Date:", disp_date),
            row("Expense Head:", expense.get("expense_head_name") or expense.get("to_account_name") or "-"),
            row("Paid From:", expense.get("account_name") or expense.get("from_account_name") or "-"),
            row("Payment Mode:", expense.get("payment_mode") or "-"),
            row("Amount:", f"\u20b9{float(expense.get('amount', 0)):,.2f}"),
        ]
        if expense.get("narration"):
            detail.append(row("Narration:", expense["narration"]))

        dt = Table(detail, colWidths=[38*mm, None])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFF")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D8FF")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(dt)
        story.append(Spacer(1, 8*mm))

        # Signature block — name on top, line, then role label below
        sig_s  = ps("sg",  fontSize=9,  alignment=TA_CENTER, fontName="Helvetica-Bold")
        role_s = ps("rl",  fontSize=8,  alignment=TA_CENTER, textColor=colors.grey)
        line_s = ps("ln",  fontSize=9,  alignment=TA_CENTER)

        sig_cols = [
            (expense.get("prepared_by") or "",  "Prepared By"),
            (expense.get("processed_by") or "", "Processed By"),
            (expense.get("authorized_by") or "", "Authorized By"),
        ]

        name_row = [T(name, sig_s)  for name, _ in sig_cols]
        line_row = [T("_" * 20, line_s) for _ in sig_cols]
        role_row = [T(role, role_s) for _, role in sig_cols]

        sig_tbl = Table([name_row, line_row, role_row],
                        colWidths=[None] * len(sig_cols))
        sig_tbl.setStyle(TableStyle([
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "BOTTOM"),
            ("TOPPADDING",  (0, 1), (-1, 1),  10),
            ("BOTTOMPADDING",(0, 2), (-1, 2), 4),
        ]))
        story.append(sig_tbl)
        story.append(Spacer(1, 5*mm))
        story.append(T("This is a computer-generated expense voucher.", ftr_s))

        doc.build(story)
        _open_file(path)
        messagebox.showinfo("PDF Saved", f"Expense PDF saved:\n{path}")
    except Exception as ex:
        messagebox.showerror("PDF Error", f"Could not generate PDF:\n{ex}")


def print_ledger_pdf(ltype: str, ledger_name: str, entries: list,
                     out_rows: list = None, entity_name: str = ""):
    ok, mods = _get_rl()
    if not ok:
        return
    (A5, colors, mm, SimpleDocTemplate, Table, TableStyle,
     Paragraph, Spacer, getSS, PS, TA_CENTER, TA_LEFT) = mods

    try:
        from reportlab.lib.pagesizes import A4, landscape as rl_landscape
    except ImportError:
        messagebox.showerror("Missing Library", "reportlab not installed.")
        return

    path = filedialog.asksaveasfilename(
        defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
        initialfile=f"Ledger_{ledger_name.replace(' ', '_')}.pdf",
        title="Save Ledger PDF"
    )
    if not path:
        return

    def disp(raw):
        if raw and len(str(raw)) == 10 and "-" in str(raw):
            y, m, d = str(raw).split("-")
            return f"{d}/{m}/{y}"
        return str(raw) if raw else "-"

    def money(v):
        try:
            return f"\u20b9{float(v):,.2f}" if float(v) else "-"
        except Exception:
            return str(v)

    try:
        page = rl_landscape(A4)
        doc = SimpleDocTemplate(path, pagesize=page,
                                leftMargin=12*mm, rightMargin=12*mm,
                                topMargin=10*mm, bottomMargin=10*mm)
        styles = getSS()

        def ps(name, **kw):
            return PS(name, parent=styles["Normal"], **kw)

        title_s = ps("t", fontSize=13, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=1*mm)
        sub_s   = ps("s", fontSize=9,  alignment=TA_CENTER, textColor=colors.grey, spaceAfter=4*mm)
        hdr_s   = ps("h", fontSize=8,  fontName="Helvetica-Bold")
        cel_s   = ps("c", fontSize=8)
        ftr_s   = ps("f", fontSize=7,  alignment=TA_CENTER, textColor=colors.grey)

        T = lambda text, style=cel_s: Paragraph(str(text or "-"), style)
        H = lambda text: Paragraph(text, hdr_s)

        story = []
        if entity_name:
            story.append(Paragraph(entity_name, ps("en", fontSize=11, fontName="Helvetica-Bold",
                                                    alignment=TA_CENTER, spaceAfter=1*mm)))
        story.append(Paragraph(f"LEDGER: {ledger_name}", title_s))

        usable_w = page[0] - 24*mm  # landscape A4 width minus margins

        if ltype == "outstanding" and out_rows:
            story.append(Paragraph("Outstanding Invoice Report", sub_s))
            cols = ["Date", "Invoice / Ref", "Description", "Debit", "Credit", "Balance"]
            cw   = [20*mm, 28*mm, None, 24*mm, 24*mm, 24*mm]
            cw[2] = usable_w - sum(c for c in cw if c)
            tdata = [[H(c) for c in cols]]
            for e in out_rows:
                tdata.append([T(disp(e.get("date"))), T(e.get("ref") or "-"),
                              T(e.get("description") or ""),
                              T(money(e["debit"])), T(money(e["credit"])), T(money(e["balance"]))])

        elif ltype == "expense":
            story.append(Paragraph("Expense Ledger", sub_s))
            cols = ["Voucher No", "Date", "Account", "Description / Narration", "Amount", "Running Total"]
            cw   = [24*mm, 20*mm, 36*mm, None, 24*mm, 24*mm]
            cw[3] = usable_w - sum(c for c in cw if c)
            tdata = [[H(c) for c in cols]]
            for e in entries:
                tdata.append([T(e.get("voucher_no") or "-"), T(disp(e.get("date"))),
                              T(e.get("account") or "-"), T(e.get("description") or ""),
                              T(money(e.get("amount"))), T(money(e.get("running_total")))])

        elif ltype == "vendor":
            story.append(Paragraph("Vendor Ledger", sub_s))
            cols = ["Voucher No", "Date", "Inv Date", "Inv No.", "Type",
                    "Description / Narration", "Debit", "Credit", "Balance"]
            cw   = [24*mm, 20*mm, 20*mm, 24*mm, 18*mm, None, 24*mm, 24*mm, 24*mm]
            cw[5] = usable_w - sum(c for c in cw if c)
            tdata = [[H(c) for c in cols]]
            for e in entries:
                tdata.append([T(e.get("voucher_no") or "-"), T(disp(e.get("date"))),
                              T(disp(e.get("invoice_date")) if e.get("invoice_date") else "-"),
                              T(e.get("invoice_number") or "-"),
                              T(e.get("type") or "-"), T(e.get("description") or ""),
                              T(money(e.get("debit"))), T(money(e.get("credit"))),
                              T(money(e.get("balance")))])
        else:
            story.append(Paragraph("Account Ledger", sub_s))
            cols = ["Voucher No", "Date", "Type", "Description / Narration",
                    "Debit", "Credit", "Balance"]
            cw   = [24*mm, 20*mm, 26*mm, None, 24*mm, 24*mm, 24*mm]
            cw[3] = usable_w - sum(c for c in cw if c)
            tdata = [[H(c) for c in cols]]
            for e in entries:
                tdata.append([T(e.get("voucher_no") or "-"), T(disp(e.get("date"))),
                              T(e.get("type") or "-"), T(e.get("description") or ""),
                              T(money(e.get("debit"))), T(money(e.get("credit"))),
                              T(money(e.get("balance")))])

        tbl = Table(tdata, colWidths=cw, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2B6B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFF")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D8FF")),
            ("PADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (-3, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph("This is a computer-generated ledger report.", ftr_s))

        doc.build(story)
        _open_file(path)
        messagebox.showinfo("PDF Saved", f"Ledger PDF saved:\n{path}")
    except Exception as ex:
        messagebox.showerror("PDF Error", f"Could not generate ledger PDF:\n{ex}")


def print_purchase_pdf(purchase: dict, entity_name: str = ""):
    ok, mods = _get_rl()
    if not ok:
        return
    (A5, colors, mm, SimpleDocTemplate, Table, TableStyle,
     Paragraph, Spacer, getSS, PS, TA_CENTER, TA_LEFT) = mods

    vno = purchase["voucher_no"]
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
        initialfile=f"Purchase_{vno}.pdf", title="Save Purchase PDF"
    )
    if not path:
        return
    try:
        doc = SimpleDocTemplate(path, pagesize=A5,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=12*mm, bottomMargin=12*mm)
        styles = getSS()

        def ps(name, **kw):
            return PS(name, parent=styles["Normal"], **kw)

        title_s = ps("t", fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=2*mm)
        sub_s   = ps("s", fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=5*mm)
        lbl_s   = ps("l", fontSize=9,  fontName="Helvetica-Bold")
        val_s   = ps("v", fontSize=9)
        ftr_s   = ps("f", fontSize=8,  alignment=TA_CENTER, textColor=colors.grey)

        story = []
        if entity_name:
            story.append(Paragraph(entity_name,
                                   ps("en", fontSize=12, fontName="Helvetica-Bold",
                                      alignment=TA_CENTER, spaceAfter=2*mm)))
        story.append(Paragraph("PURCHASE VOUCHER", title_s))
        story.append(Paragraph(f"Voucher No: {vno}", sub_s))

        def row(lbl, val):
            return [Paragraph(lbl, lbl_s), Paragraph(str(val or "-"), val_s)]

        detail = [
            row("Date:", purchase["date"]),
            row("Vendor:", purchase.get("vendor_name") or "-"),
            row("Invoice No:", purchase.get("invoice_number") or "-"),
            row("Purchase Value:", f"\u20b9{purchase['purchase_value']:,.2f}"),
            row("GST Amount:", f"\u20b9{purchase['gst_amount']:,.2f}"),
            row("Total Value:", f"\u20b9{purchase['total_value']:,.2f}"),
            row("Outstanding:", f"\u20b9{purchase['outstanding']:,.2f}"),
        ]
        if purchase.get("narration"):
            detail.append(row("Narration:", purchase["narration"]))

        dt = Table(detail, colWidths=[38*mm, None])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFF")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D8FF")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(dt)
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph("This is a computer-generated purchase voucher.", ftr_s))

        doc.build(story)
        _open_file(path)
        messagebox.showinfo("PDF Saved", f"Purchase PDF saved:\n{path}")
    except Exception as ex:
        messagebox.showerror("PDF Error", f"Could not generate PDF:\n{ex}")
