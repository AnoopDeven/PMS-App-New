import sqlite3
import os
from datetime import date


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db(db_path):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS entity_meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS financial_years (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            label      TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date   TEXT NOT NULL,
            fy_type    TEXT NOT NULL DEFAULT 'april_march',
            is_active  INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS vendors (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL UNIQUE,
            category        TEXT NOT NULL DEFAULT 'creditor',
            contact_person  TEXT,
            phone           TEXT,
            email           TEXT,
            address         TEXT,
            opening_balance REAL NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL UNIQUE,
            type            TEXT NOT NULL CHECK(type IN ('cash','bank')),
            bank_name       TEXT,
            account_number  TEXT,
            opening_balance REAL NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expense_heads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS vouchers (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no       TEXT NOT NULL,
            type             TEXT NOT NULL
                                 CHECK(type IN ('payment','transfer')),
            status           TEXT NOT NULL DEFAULT 'active'
                                 CHECK(status IN ('active','cancelled')),
            date             TEXT NOT NULL,
            financial_year_id INTEGER REFERENCES financial_years(id),
            vendor_id        INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
            from_account_id  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            to_account_id    INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            payment_mode     TEXT,
            amount           REAL NOT NULL DEFAULT 0,
            narration        TEXT,
            receiver_name    TEXT,
            receiver_sig     TEXT,
            prepared_by      TEXT,
            processed_by     TEXT,
            authorized_by    TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no       TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'active'
                                 CHECK(status IN ('active','cancelled')),
            date             TEXT NOT NULL,
            financial_year_id INTEGER REFERENCES financial_years(id),
            expense_head_id  INTEGER REFERENCES expense_heads(id),
            from_account_id  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            amount           REAL NOT NULL DEFAULT 0,
            narration        TEXT,
            payment_mode     TEXT DEFAULT 'Cash',
            prepared_by      TEXT,
            processed_by     TEXT,
            authorized_by    TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no       TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'active'
                                 CHECK(status IN ('active','cancelled')),
            date             TEXT NOT NULL,
            invoice_date     TEXT,
            financial_year_id INTEGER REFERENCES financial_years(id),
            vendor_id        INTEGER NOT NULL REFERENCES vendors(id),
            invoice_number   TEXT,
            purchase_value   REAL NOT NULL DEFAULT 0,
            gst_amount       REAL NOT NULL DEFAULT 0,
            total_value      REAL NOT NULL DEFAULT 0,
            narration        TEXT,
            outstanding      REAL NOT NULL DEFAULT 0,
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS credit_notes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no       TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'active'
                                 CHECK(status IN ('active','cancelled')),
            date             TEXT NOT NULL,
            financial_year_id INTEGER REFERENCES financial_years(id),
            vendor_id        INTEGER NOT NULL REFERENCES vendors(id),
            ref_purchase_id  INTEGER REFERENCES purchases(id),
            value            REAL NOT NULL DEFAULT 0,
            gst_amount       REAL NOT NULL DEFAULT 0,
            total_value      REAL NOT NULL DEFAULT 0,
            narration        TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS debit_notes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no       TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'active'
                                 CHECK(status IN ('active','cancelled')),
            date             TEXT NOT NULL,
            financial_year_id INTEGER REFERENCES financial_years(id),
            vendor_id        INTEGER NOT NULL REFERENCES vendors(id),
            ref_purchase_id  INTEGER REFERENCES purchases(id),
            value            REAL NOT NULL DEFAULT 0,
            gst_amount       REAL NOT NULL DEFAULT 0,
            total_value      REAL NOT NULL DEFAULT 0,
            narration        TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS payment_adjustments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_id  INTEGER NOT NULL REFERENCES vouchers(id) ON DELETE CASCADE,
            purchase_id INTEGER REFERENCES purchases(id),
            amount      REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS opening_bal_payments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_id INTEGER NOT NULL REFERENCES vouchers(id) ON DELETE CASCADE,
            vendor_id  INTEGER NOT NULL REFERENCES vendors(id),
            amount     REAL NOT NULL DEFAULT 0
        );
    """)
    conn.commit()

    # ── Migrations for existing databases ─────────────────────────────────────
    migrations = [
        "ALTER TABLE vendors ADD COLUMN opening_balance REAL NOT NULL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN invoice_date TEXT",
        "CREATE TABLE IF NOT EXISTS expense_heads (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')))",
        "CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_no TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', date TEXT NOT NULL, financial_year_id INTEGER REFERENCES financial_years(id), expense_head_id INTEGER REFERENCES expense_heads(id), from_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL, amount REAL NOT NULL DEFAULT 0, narration TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')))",
        "CREATE TABLE IF NOT EXISTS opening_bal_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_id INTEGER NOT NULL REFERENCES vouchers(id) ON DELETE CASCADE, vendor_id INTEGER NOT NULL REFERENCES vendors(id), amount REAL NOT NULL DEFAULT 0)",
        "ALTER TABLE expenses ADD COLUMN payment_mode TEXT DEFAULT 'Cash'",
        "ALTER TABLE expenses ADD COLUMN prepared_by TEXT",
        "ALTER TABLE expenses ADD COLUMN processed_by TEXT",
        "ALTER TABLE expenses ADD COLUMN authorized_by TEXT",
        "ALTER TABLE vendors ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
        "ALTER TABLE accounts ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
        "ALTER TABLE expense_heads ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
    ]
    cur2 = conn.cursor()
    for m in migrations:
        try:
            cur2.execute(m)
            conn.commit()
        except Exception:
            pass

    conn.close()


# ── Entity Meta ───────────────────────────────────────────────────────────────

def set_meta(db_path, key, value):
    conn = get_connection(db_path)
    conn.execute("INSERT OR REPLACE INTO entity_meta(key,value) VALUES(?,?)", (key, str(value)))
    conn.commit()
    conn.close()


def get_meta(db_path, key, default=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT value FROM entity_meta WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default


# ── Financial Years ───────────────────────────────────────────────────────────

def create_financial_year(db_path, label, start_date, end_date, fy_type="april_march"):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO financial_years(label,start_date,end_date,fy_type) VALUES(?,?,?,?)",
        (label, start_date, end_date, fy_type)
    )
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    return fid


def get_financial_years(db_path):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM financial_years ORDER BY start_date DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_active_fy(db_path):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM financial_years WHERE is_active=1 ORDER BY start_date DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def set_active_fy(db_path, fy_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE financial_years SET is_active=0")
    conn.execute("UPDATE financial_years SET is_active=1 WHERE id=?", (fy_id,))
    conn.commit()
    conn.close()


def ensure_financial_year(db_path, fy_type="april_march"):
    """Create FY for current date if none exists."""
    existing = get_financial_years(db_path)
    if existing:
        return
    today = date.today()
    if fy_type == "april_march":
        if today.month >= 4:
            start = date(today.year, 4, 1)
            end = date(today.year + 1, 3, 31)
        else:
            start = date(today.year - 1, 4, 1)
            end = date(today.year, 3, 31)
        label = f"FY {start.year}-{str(end.year)[2:]}"
    else:
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
        label = f"FY {today.year}"
    create_financial_year(db_path, label, str(start), str(end), fy_type)


def get_fy_for_date(db_path, d):
    """Return FY id for a given date string."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM financial_years WHERE start_date<=? AND end_date>=? ORDER BY start_date DESC LIMIT 1",
        (d, d)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ── Vendors ───────────────────────────────────────────────────────────────────

def get_vendors(db_path, search="", category=None, include_inactive=False):
    conn = get_connection(db_path)
    cur = conn.cursor()
    q = "SELECT * FROM vendors WHERE 1=1"
    p = []
    if not include_inactive:
        q += " AND (status IS NULL OR status='active')"
    if search:
        q += " AND name LIKE ?"
        p.append(f"%{search}%")
    if category:
        q += " AND category=?"
        p.append(category)
    q += " ORDER BY name"
    cur.execute(q, p)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_vendor(db_path, vendor_id):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM vendors WHERE id=?", (vendor_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_vendor(db_path, name, category="creditor", contact_person="",
                  phone="", email="", address="", opening_balance=0):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM vendors WHERE LOWER(name)=LOWER(?)", (name,))
    if cur.fetchone():
        conn.close()
        raise ValueError(f"Vendor '{name}' already exists.")
    cur.execute(
        "INSERT INTO vendors(name,category,contact_person,phone,email,address,opening_balance) VALUES(?,?,?,?,?,?,?)",
        (name, category, contact_person or None, phone or None, email or None, address or None, opening_balance or 0)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def update_vendor(db_path, vendor_id, name, category="creditor", contact_person="",
                  phone="", email="", address="", opening_balance=0):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM vendors WHERE LOWER(name)=LOWER(?) AND id!=?", (name, vendor_id))
    if cur.fetchone():
        conn.close()
        raise ValueError(f"Another vendor named '{name}' already exists.")
    cur.execute(
        "UPDATE vendors SET name=?,category=?,contact_person=?,phone=?,email=?,address=?,opening_balance=? WHERE id=?",
        (name, category, contact_person or None, phone or None, email or None, address or None, opening_balance or 0, vendor_id)
    )
    conn.commit()
    conn.close()


def delete_vendor(db_path, vendor_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE vendors SET status='inactive' WHERE id=?", (vendor_id,))
    conn.commit()
    conn.close()


def restore_vendor(db_path, vendor_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE vendors SET status='active' WHERE id=?", (vendor_id,))
    conn.commit()
    conn.close()


# ── Accounts ──────────────────────────────────────────────────────────────────

def get_accounts(db_path, search="", type_filter=None, include_inactive=False):
    conn = get_connection(db_path)
    cur = conn.cursor()
    q = "SELECT * FROM accounts WHERE 1=1"
    p = []
    if not include_inactive:
        q += " AND (status IS NULL OR status='active')"
    if search:
        q += " AND name LIKE ?"
        p.append(f"%{search}%")
    if type_filter:
        q += " AND type=?"
        p.append(type_filter)
    q += " ORDER BY name"
    cur.execute(q, p)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_account(db_path, account_id):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (account_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_account(db_path, name, acc_type, bank_name="", account_number="", opening_balance=0):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE LOWER(name)=LOWER(?)", (name,))
    if cur.fetchone():
        conn.close()
        raise ValueError(f"Account '{name}' already exists.")
    cur.execute(
        "INSERT INTO accounts(name,type,bank_name,account_number,opening_balance) VALUES(?,?,?,?,?)",
        (name, acc_type, bank_name or None, account_number or None, opening_balance)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def update_account(db_path, account_id, name, acc_type, bank_name="", account_number="", opening_balance=0):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE LOWER(name)=LOWER(?) AND id!=?", (name, account_id))
    if cur.fetchone():
        conn.close()
        raise ValueError(f"Another account named '{name}' already exists.")
    cur.execute(
        "UPDATE accounts SET name=?,type=?,bank_name=?,account_number=?,opening_balance=? WHERE id=?",
        (name, acc_type, bank_name or None, account_number or None, opening_balance, account_id)
    )
    conn.commit()
    conn.close()


def delete_account(db_path, account_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE accounts SET status='inactive' WHERE id=?", (account_id,))
    conn.commit()
    conn.close()


def restore_account(db_path, account_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE accounts SET status='active' WHERE id=?", (account_id,))
    conn.commit()
    conn.close()


# ── Voucher Numbering ─────────────────────────────────────────────────────────

def _pym_num(vno):
    """Extract the leading integer from a PYM voucher number string."""
    s = vno[3:] if vno.startswith("PYM") else vno
    return s.split(".")[0]


def _next_payment_no(conn, date_str, fy_id):
    """Generate next payment voucher number with PYM prefix.
    Forward entry  → PYM1, PYM2, PYM3 …
    Backdated entry → PYM5.1, PYM5.2 …
    Resets per financial year.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT voucher_no, date FROM vouchers WHERE type='payment' AND financial_year_id=? AND status!='cancelled' ORDER BY date DESC, created_at DESC",
        (fy_id,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    if not rows:
        return "PYM1"
    latest_date = rows[0]["date"]
    if date_str >= latest_date:
        max_num = 0
        for r in rows:
            try:
                n = int(_pym_num(r["voucher_no"]))
                if n > max_num:
                    max_num = n
            except ValueError:
                pass
        return f"PYM{max_num + 1}"
    else:
        same = [r for r in rows if r["date"] == date_str]
        before = sorted([r for r in rows if r["date"] < date_str],
                        key=lambda x: x["date"], reverse=True)
        base_vno = (same[-1] if same else before[0])["voucher_no"] if (same or before) else "PYM1"
        base_num = _pym_num(base_vno)
        max_sub = 0
        for r in rows:
            num_part = _pym_num(r["voucher_no"])
            raw = r["voucher_no"][3:] if r["voucher_no"].startswith("PYM") else r["voucher_no"]
            parts = raw.split(".")
            if parts[0] == base_num and len(parts) > 1:
                try:
                    s = int(parts[1])
                    if s > max_sub:
                        max_sub = s
                except ValueError:
                    pass
        return f"PYM{base_num}.{max_sub + 1}"


def _next_prefix_no(conn, prefix, table, fy_id):
    cur = conn.cursor()
    if table == "vouchers":
        cur.execute(
            "SELECT COUNT(*) as c FROM vouchers WHERE type='transfer' AND financial_year_id=? AND status!='cancelled'",
            (fy_id,)
        )
    elif table == "purchases":
        cur.execute(
            "SELECT COUNT(*) as c FROM purchases WHERE financial_year_id=? AND status!='cancelled'",
            (fy_id,)
        )
    elif table == "credit_notes":
        cur.execute(
            "SELECT COUNT(*) as c FROM credit_notes WHERE financial_year_id=? AND status!='cancelled'",
            (fy_id,)
        )
    elif table == "debit_notes":
        cur.execute(
            "SELECT COUNT(*) as c FROM debit_notes WHERE financial_year_id=? AND status!='cancelled'",
            (fy_id,)
        )
    elif table == "expenses":
        cur.execute(
            "SELECT COUNT(*) as c FROM expenses WHERE financial_year_id=? AND status!='cancelled'",
            (fy_id,)
        )
    cnt = cur.fetchone()["c"]
    return f"{prefix}{cnt + 1}"


# ── FY Date Validation ────────────────────────────────────────────────────────

def validate_fy_date(db_path, date_str, fy_id=None):
    """Returns (is_valid, error_message). Validates date is within the active FY."""
    if not date_str:
        return False, "Date is required."
    fy = None
    if fy_id:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM financial_years WHERE id=?", (fy_id,))
        row = cur.fetchone()
        conn.close()
        fy = dict(row) if row else None
    if not fy:
        fy = get_active_fy(db_path)
    if not fy:
        return True, ""
    if date_str < fy["start_date"] or date_str > fy["end_date"]:
        from date_utils import to_display
        return False, (
            f"Date must be within the active Financial Year:\n"
            f"{to_display(fy['start_date'])}  to  {to_display(fy['end_date'])}"
        )
    return True, ""


# ── Expense Heads ─────────────────────────────────────────────────────────────

def get_expense_heads(db_path, search="", include_inactive=False):
    conn = get_connection(db_path)
    cur = conn.cursor()
    q = "SELECT * FROM expense_heads WHERE 1=1"
    p = []
    if not include_inactive:
        q += " AND (status IS NULL OR status='active')"
    if search:
        q += " AND name LIKE ?"
        p.append(f"%{search}%")
    q += " ORDER BY name ASC"
    cur.execute(q, p)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def create_expense_head(db_path, name, description=""):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM expense_heads WHERE LOWER(name)=LOWER(?)", (name,))
    if cur.fetchone():
        conn.close()
        raise ValueError(f"Expense head '{name}' already exists.")
    cur.execute(
        "INSERT INTO expense_heads(name,description) VALUES(?,?)",
        (name, description or None)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def update_expense_head(db_path, head_id, name, description=""):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM expense_heads WHERE LOWER(name)=LOWER(?) AND id!=?", (name, head_id))
    if cur.fetchone():
        conn.close()
        raise ValueError(f"Expense head '{name}' already exists.")
    cur.execute(
        "UPDATE expense_heads SET name=?,description=? WHERE id=?",
        (name, description or None, head_id)
    )
    conn.commit()
    conn.close()


def delete_expense_head(db_path, head_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE expense_heads SET status='inactive' WHERE id=?", (head_id,))
    conn.commit()
    conn.close()


def restore_expense_head(db_path, head_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE expense_heads SET status='active' WHERE id=?", (head_id,))
    conn.commit()
    conn.close()


# ── Expenses ──────────────────────────────────────────────────────────────────

def create_expense(db_path, date_str, expense_head_id, from_account_id,
                   amount, narration="", payment_mode="Cash",
                   prepared_by="", processed_by="", authorized_by=""):
    conn = get_connection(db_path)
    cur = conn.cursor()
    fy = get_fy_for_date(db_path, date_str)
    fy_id = fy["id"] if fy else None
    voucher_no = _next_prefix_no(conn, "EX", "expenses", fy_id)
    cur.execute("""
        INSERT INTO expenses(voucher_no,date,financial_year_id,expense_head_id,
            from_account_id,amount,narration,payment_mode,
            prepared_by,processed_by,authorized_by)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (voucher_no, date_str, fy_id, expense_head_id, from_account_id,
          amount, narration or None, payment_mode or "Cash",
          prepared_by or None, processed_by or None, authorized_by or None))
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid, voucher_no


def get_expenses(db_path, expense_head_id=None, date_from=None, date_to=None,
                 include_cancelled=False, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    q = """SELECT e.*, eh.name as expense_head_name, a.name as account_name
           FROM expenses e
           LEFT JOIN expense_heads eh ON e.expense_head_id=eh.id
           LEFT JOIN accounts a ON e.from_account_id=a.id
           WHERE 1=1"""
    p = []
    if not include_cancelled:
        q += " AND e.status='active'"
    if expense_head_id:
        q += " AND e.expense_head_id=?"
        p.append(expense_head_id)
    if fy_id:
        q += " AND e.financial_year_id=?"
        p.append(fy_id)
    if date_from:
        q += " AND e.date>=?"
        p.append(date_from)
    if date_to:
        q += " AND e.date<=?"
        p.append(date_to)
    q += " ORDER BY e.date ASC, e.voucher_no ASC"
    cur.execute(q, p)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_expense(db_path, expense_id):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""SELECT e.*, eh.name as expense_head_name, a.name as account_name
                   FROM expenses e
                   LEFT JOIN expense_heads eh ON e.expense_head_id=eh.id
                   LEFT JOIN accounts a ON e.from_account_id=a.id
                   WHERE e.id=?""", (expense_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_expense(db_path, expense_id, date_str, expense_head_id,
                   from_account_id, amount, narration="", payment_mode="Cash",
                   prepared_by="", processed_by="", authorized_by=""):
    conn = get_connection(db_path)
    cur = conn.cursor()
    fy = get_fy_for_date(db_path, date_str)
    if not fy:
        cur.execute("SELECT financial_year_id FROM expenses WHERE id=?", (expense_id,))
        row = cur.fetchone()
        fy_id = row["financial_year_id"] if row else None
    else:
        fy_id = fy["id"]
    cur.execute("""UPDATE expenses SET date=?,financial_year_id=?,expense_head_id=?,
                   from_account_id=?,amount=?,narration=?,payment_mode=?,
                   prepared_by=?,processed_by=?,authorized_by=? WHERE id=?""",
                (date_str, fy_id, expense_head_id, from_account_id,
                 amount, narration or None, payment_mode or "Cash",
                 prepared_by or None, processed_by or None, authorized_by or None,
                 expense_id))
    conn.commit()
    conn.close()


def cancel_expense(db_path, expense_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE expenses SET status='cancelled' WHERE id=?", (expense_id,))
    conn.commit()
    conn.close()


def get_expense_ledger(db_path, expense_head_id, date_from=None, date_to=None, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM expense_heads WHERE id=?", (expense_head_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"name": "Unknown", "entries": [], "total": 0}
    head = dict(row)
    entries_raw = get_expenses(db_path, expense_head_id=expense_head_id,
                               date_from=date_from, date_to=date_to, fy_id=fy_id)
    total = 0
    entries = []
    for e in entries_raw:
        total += e["amount"]
        entries.append({
            "voucher_no": e["voucher_no"],
            "date": e["date"],
            "account": e.get("account_name") or "-",
            "description": e.get("narration") or f"Expense: {head['name']}",
            "amount": e["amount"],
            "running_total": total,
            "src_id": e["id"],
        })
    return {"name": head["name"], "entries": entries, "total": total}


# ── Payment Vouchers ──────────────────────────────────────────────────────────

def create_voucher(db_path, vtype, date_str, vendor_id=None, from_account_id=None,
                   to_account_id=None, payment_mode=None, amount=0,
                   narration="", receiver_name="", receiver_sig="",
                   prepared_by="", processed_by="", authorized_by="",
                   adjustments=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    fy = get_fy_for_date(db_path, date_str)
    fy_id = fy["id"] if fy else None

    if vtype == "transfer":
        voucher_no = _next_prefix_no(conn, "IT", "vouchers", fy_id)
    else:
        voucher_no = _next_payment_no(conn, date_str, fy_id)

    cur.execute("""
        INSERT INTO vouchers(voucher_no,type,date,financial_year_id,vendor_id,
            from_account_id,to_account_id,payment_mode,amount,narration,
            receiver_name,receiver_sig,prepared_by,processed_by,authorized_by)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (voucher_no, vtype, date_str, fy_id, vendor_id, from_account_id, to_account_id,
          payment_mode, amount, narration or None, receiver_name or None, receiver_sig or None,
          prepared_by or None, processed_by or None, authorized_by or None))
    vid = cur.lastrowid

    # Handle adjustments against purchase invoices
    if adjustments:
        for adj in adjustments:
            purchase_id = adj.get("purchase_id")
            adj_amount = adj["amount"]
            is_ob = adj.get("is_opening_balance", False)
            if is_ob and vendor_id:
                # Adjustment against vendor opening balance — record only, do NOT mutate vendors.opening_balance
                cur.execute(
                    "INSERT INTO opening_bal_payments(voucher_id,vendor_id,amount) VALUES(?,?,?)",
                    (vid, vendor_id, adj_amount)
                )
            elif purchase_id:
                cur.execute(
                    "INSERT INTO payment_adjustments(voucher_id,purchase_id,amount) VALUES(?,?,?)",
                    (vid, purchase_id, adj_amount)
                )
                cur.execute(
                    "UPDATE purchases SET outstanding=MAX(0,outstanding-?) WHERE id=?",
                    (adj_amount, purchase_id)
                )

    conn.commit()
    conn.close()
    return vid, voucher_no


def get_vouchers(db_path, date_from=None, date_to=None, vendor_id=None,
                 account_id=None, voucher_no_filter=None, amount_min=None,
                 amount_max=None, vtype=None, include_cancelled=False, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    q = """
        SELECT v.*, vn.name as vendor_name, vn.category as vendor_category,
               fa.name as from_account_name, ta.name as to_account_name
        FROM vouchers v
        LEFT JOIN vendors vn ON v.vendor_id=vn.id
        LEFT JOIN accounts fa ON v.from_account_id=fa.id
        LEFT JOIN accounts ta ON v.to_account_id=ta.id
        WHERE 1=1
    """
    p = []
    if not include_cancelled:
        q += " AND v.status='active'"
    if fy_id:
        q += " AND v.financial_year_id=?"
        p.append(fy_id)
    if date_from:
        q += " AND v.date>=?"
        p.append(date_from)
    if date_to:
        q += " AND v.date<=?"
        p.append(date_to)
    if vendor_id:
        q += " AND v.vendor_id=?"
        p.append(vendor_id)
    if account_id:
        q += " AND (v.from_account_id=? OR v.to_account_id=?)"
        p.extend([account_id, account_id])
    if voucher_no_filter:
        q += " AND v.voucher_no LIKE ?"
        p.append(f"%{voucher_no_filter}%")
    if amount_min is not None:
        q += " AND v.amount>=?"
        p.append(amount_min)
    if amount_max is not None:
        q += " AND v.amount<=?"
        p.append(amount_max)
    if vtype:
        q += " AND v.type=?"
        p.append(vtype)
    q += " ORDER BY v.date ASC, v.voucher_no ASC"
    cur.execute(q, p)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_voucher(db_path, voucher_id):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT v.*, vn.name as vendor_name, fa.name as from_account_name, ta.name as to_account_name
        FROM vouchers v
        LEFT JOIN vendors vn ON v.vendor_id=vn.id
        LEFT JOIN accounts fa ON v.from_account_id=fa.id
        LEFT JOIN accounts ta ON v.to_account_id=ta.id
        WHERE v.id=?
    """, (voucher_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_voucher_adjustments(db_path, voucher_id):
    """Return existing adjustments for a voucher so the edit UI can pre-populate them."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT purchase_id, amount FROM payment_adjustments WHERE voucher_id=?",
                (voucher_id,))
    inv_adjs = {r["purchase_id"]: r["amount"] for r in cur.fetchall()}
    cur.execute("SELECT COALESCE(SUM(amount),0) as t FROM opening_bal_payments WHERE voucher_id=?",
                (voucher_id,))
    ob_adj = (cur.fetchone()["t"] or 0)
    conn.close()
    return {"invoice_adjustments": inv_adjs, "ob_adjustment": ob_adj}


def update_voucher(db_path, voucher_id, **kwargs):
    """Update voucher fields; reverse old adjustments and apply new ones."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM vouchers WHERE id=?", (voucher_id,))
    ex = dict(cur.fetchone())

    # Step 1: Reverse old invoice adjustments (restore outstanding)
    cur.execute("SELECT * FROM payment_adjustments WHERE voucher_id=?", (voucher_id,))
    for adj in [dict(r) for r in cur.fetchall()]:
        if adj.get("purchase_id"):
            cur.execute("UPDATE purchases SET outstanding=outstanding+? WHERE id=?",
                        (adj["amount"], adj["purchase_id"]))
    cur.execute("DELETE FROM payment_adjustments WHERE voucher_id=?", (voucher_id,))
    # OB payments: delete records so they no longer reduce effective OB
    cur.execute("DELETE FROM opening_bal_payments WHERE voucher_id=?", (voucher_id,))

    # Step 2: Update voucher fields
    fields = ["date", "vendor_id", "from_account_id", "to_account_id",
              "payment_mode", "amount", "narration", "receiver_name",
              "receiver_sig", "prepared_by", "processed_by", "authorized_by"]
    vals = [kwargs.get(f, ex[f]) for f in fields]
    vals.append(voucher_id)
    cur.execute(f"""
        UPDATE vouchers SET date=?,vendor_id=?,from_account_id=?,to_account_id=?,
        payment_mode=?,amount=?,narration=?,receiver_name=?,receiver_sig=?,
        prepared_by=?,processed_by=?,authorized_by=? WHERE id=?
    """, vals)

    # Step 3: Apply new adjustments (if provided)
    new_vendor_id = kwargs.get("vendor_id", ex["vendor_id"])
    adjustments = kwargs.get("adjustments") or []
    for adj in adjustments:
        purchase_id = adj.get("purchase_id")
        adj_amount = adj["amount"]
        is_ob = adj.get("is_opening_balance", False)
        if is_ob and new_vendor_id:
            cur.execute(
                "INSERT INTO opening_bal_payments(voucher_id,vendor_id,amount) VALUES(?,?,?)",
                (voucher_id, new_vendor_id, adj_amount)
            )
        elif purchase_id:
            cur.execute(
                "INSERT INTO payment_adjustments(voucher_id,purchase_id,amount) VALUES(?,?,?)",
                (voucher_id, purchase_id, adj_amount)
            )
            cur.execute(
                "UPDATE purchases SET outstanding=MAX(0,outstanding-?) WHERE id=?",
                (adj_amount, purchase_id)
            )

    conn.commit()
    conn.close()


def cancel_voucher(db_path, voucher_id):
    conn = get_connection(db_path)
    cur = conn.cursor()
    # Reverse invoice adjustments (restore outstanding)
    cur.execute("SELECT * FROM payment_adjustments WHERE voucher_id=?", (voucher_id,))
    for adj in [dict(r) for r in cur.fetchall()]:
        if adj.get("purchase_id"):
            cur.execute(
                "UPDATE purchases SET outstanding=outstanding+? WHERE id=?",
                (adj["amount"], adj["purchase_id"])
            )
    # Opening balance payments: do NOT mutate vendors.opening_balance — records stay
    # but are excluded from balance calculations by joining on vouchers.status='active'
    cur.execute("UPDATE vouchers SET status='cancelled' WHERE id=?", (voucher_id,))
    conn.commit()
    conn.close()


def restore_voucher(db_path, voucher_id):
    """Restore a cancelled voucher back to active, re-applying its adjustments."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    # Re-apply invoice adjustments (reduce outstanding again)
    cur.execute("SELECT * FROM payment_adjustments WHERE voucher_id=?", (voucher_id,))
    for adj in [dict(r) for r in cur.fetchall()]:
        if adj.get("purchase_id"):
            cur.execute(
                "UPDATE purchases SET outstanding=MAX(0,outstanding-?) WHERE id=?",
                (adj["amount"], adj["purchase_id"])
            )
    # Opening-balance payments automatically re-activate because we join on vouchers.status='active'
    cur.execute("UPDATE vouchers SET status='active' WHERE id=?", (voucher_id,))
    conn.commit()
    conn.close()


def restore_purchase(db_path, purchase_id):
    """Restore a cancelled purchase back to active."""
    conn = get_connection(db_path)
    conn.execute("UPDATE purchases SET status='active' WHERE id=?", (purchase_id,))
    conn.commit()
    conn.close()


def restore_note(db_path, table, note_id):
    """Restore a cancelled credit/debit note back to active."""
    conn = get_connection(db_path)
    conn.execute(f"UPDATE {table} SET status='active' WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


def restore_expense(db_path, expense_id):
    """Restore a cancelled expense back to active."""
    conn = get_connection(db_path)
    conn.execute("UPDATE expenses SET status='active' WHERE id=?", (expense_id,))
    conn.commit()
    conn.close()


# ── Purchases ─────────────────────────────────────────────────────────────────

def create_purchase(db_path, date_str, vendor_id, invoice_number="",
                    purchase_value=0, gst_amount=0, narration="", invoice_date=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    fy = get_fy_for_date(db_path, date_str)
    fy_id = fy["id"] if fy else None
    voucher_no = _next_prefix_no(conn, "PV", "purchases", fy_id)
    total = purchase_value + gst_amount
    cur.execute("""
        INSERT INTO purchases(voucher_no,date,invoice_date,financial_year_id,vendor_id,invoice_number,
            purchase_value,gst_amount,total_value,narration,outstanding)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (voucher_no, date_str, invoice_date or None, fy_id, vendor_id, invoice_number or None,
          purchase_value, gst_amount, total, narration or None, total))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid, voucher_no


def get_purchases(db_path, vendor_id=None, date_from=None, date_to=None,
                  include_cancelled=False, fy_id=None, outstanding_only=False):
    conn = get_connection(db_path)
    cur = conn.cursor()
    q = """SELECT p.*, v.name as vendor_name FROM purchases p
           LEFT JOIN vendors v ON p.vendor_id=v.id WHERE 1=1"""
    params = []
    if not include_cancelled:
        q += " AND p.status='active'"
    if vendor_id:
        q += " AND p.vendor_id=?"
        params.append(vendor_id)
    if fy_id:
        q += " AND p.financial_year_id=?"
        params.append(fy_id)
    if date_from:
        q += " AND p.date>=?"
        params.append(date_from)
    if date_to:
        q += " AND p.date<=?"
        params.append(date_to)
    if outstanding_only:
        q += " AND p.outstanding>0"
    q += " ORDER BY p.date ASC, p.voucher_no ASC"
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_purchase(db_path, purchase_id):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""SELECT p.*, v.name as vendor_name FROM purchases p
                   LEFT JOIN vendors v ON p.vendor_id=v.id WHERE p.id=?""", (purchase_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_purchase(db_path, purchase_id, date_str=None, vendor_id=None,
                    invoice_number=None, purchase_value=None, gst_amount=None,
                    narration=None, invoice_date=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM purchases WHERE id=?", (purchase_id,))
    ex = dict(cur.fetchone())
    pv = purchase_value if purchase_value is not None else ex["purchase_value"]
    ga = gst_amount if gst_amount is not None else ex["gst_amount"]
    total = pv + ga
    inv_date = invoice_date if invoice_date is not None else ex.get("invoice_date")
    cur.execute("""UPDATE purchases SET date=?,invoice_date=?,vendor_id=?,invoice_number=?,
                   purchase_value=?,gst_amount=?,total_value=?,narration=?,outstanding=?
                   WHERE id=?""",
                (date_str or ex["date"], inv_date,
                 vendor_id or ex["vendor_id"],
                 invoice_number if invoice_number is not None else ex["invoice_number"],
                 pv, ga, total, narration if narration is not None else ex["narration"],
                 total, purchase_id))
    conn.commit()
    conn.close()


def cancel_purchase(db_path, purchase_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE purchases SET status='cancelled' WHERE id=?", (purchase_id,))
    conn.commit()
    conn.close()


# ── Credit / Debit Notes ──────────────────────────────────────────────────────

def _create_note(db_path, table, prefix, date_str, vendor_id, ref_purchase_id=None,
                 value=0, gst_amount=0, narration=""):
    conn = get_connection(db_path)
    cur = conn.cursor()
    fy = get_fy_for_date(db_path, date_str)
    fy_id = fy["id"] if fy else None
    voucher_no = _next_prefix_no(conn, prefix, table, fy_id)
    total = value + gst_amount
    cur.execute(f"""
        INSERT INTO {table}(voucher_no,date,financial_year_id,vendor_id,ref_purchase_id,
            value,gst_amount,total_value,narration)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (voucher_no, date_str, fy_id, vendor_id, ref_purchase_id,
          value, gst_amount, total, narration or None))
    if ref_purchase_id:
        if table == "credit_notes":
            # Credit note = Credit → increases payable → increases outstanding
            cur.execute(
                "UPDATE purchases SET outstanding=outstanding+? WHERE id=?",
                (total, ref_purchase_id)
            )
        elif table == "debit_notes":
            # Debit note = Debit → reduces payable → reduces outstanding
            cur.execute(
                "UPDATE purchases SET outstanding=MAX(0,outstanding-?) WHERE id=?",
                (total, ref_purchase_id)
            )
    conn.commit()
    nid = cur.lastrowid
    conn.close()
    return nid, voucher_no


def create_credit_note(db_path, date_str, vendor_id, ref_purchase_id=None,
                       value=0, gst_amount=0, narration=""):
    return _create_note(db_path, "credit_notes", "CN", date_str, vendor_id,
                        ref_purchase_id, value, gst_amount, narration)


def create_debit_note(db_path, date_str, vendor_id, ref_purchase_id=None,
                      value=0, gst_amount=0, narration=""):
    return _create_note(db_path, "debit_notes", "DN", date_str, vendor_id,
                        ref_purchase_id, value, gst_amount, narration)


def get_notes(db_path, table, vendor_id=None, date_from=None, date_to=None,
              include_cancelled=False, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    q = f"""SELECT n.*, v.name as vendor_name FROM {table} n
            LEFT JOIN vendors v ON n.vendor_id=v.id WHERE 1=1"""
    p = []
    if not include_cancelled:
        q += " AND n.status='active'"
    if vendor_id:
        q += " AND n.vendor_id=?"
        p.append(vendor_id)
    if fy_id:
        q += " AND n.financial_year_id=?"
        p.append(fy_id)
    if date_from:
        q += " AND n.date>=?"
        p.append(date_from)
    if date_to:
        q += " AND n.date<=?"
        p.append(date_to)
    q += " ORDER BY n.date ASC, n.voucher_no ASC"
    cur.execute(q, p)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def cancel_note(db_path, table, note_id):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(f"SELECT ref_purchase_id, total_value FROM {table} WHERE id=?", (note_id,))
    row = cur.fetchone()
    if row:
        ref_id, total = row["ref_purchase_id"], row["total_value"] or 0
        if ref_id and total:
            if table == "credit_notes":
                # Reverse credit note effect: undo the outstanding increase
                cur.execute(
                    "UPDATE purchases SET outstanding=MAX(0,outstanding-?) WHERE id=?",
                    (total, ref_id)
                )
            elif table == "debit_notes":
                # Reverse debit note effect: undo the outstanding decrease
                cur.execute(
                    "UPDATE purchases SET outstanding=outstanding+? WHERE id=?",
                    (total, ref_id)
                )
    cur.execute(f"UPDATE {table} SET status='cancelled' WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


# ── Vendor Payable Balance ────────────────────────────────────────────────────

def get_vendor_balance(db_path, vendor_id, fy_id=None):
    """Balance = Opening + Purchases + Debit Notes - Payments - Credit Notes"""
    conn = get_connection(db_path)
    cur = conn.cursor()
    fy_cond = "AND financial_year_id=?" if fy_id else ""
    p = [vendor_id] + ([fy_id] if fy_id else [])

    cur.execute("SELECT COALESCE(opening_balance,0) as ob FROM vendors WHERE id=?", (vendor_id,))
    row = cur.fetchone()
    opening = row["ob"] if row else 0

    cur.execute(f"SELECT COALESCE(SUM(total_value),0) as t FROM purchases WHERE vendor_id=? {fy_cond} AND status='active'", p)
    purchases = cur.fetchone()["t"]

    cur.execute(f"SELECT COALESCE(SUM(total_value),0) as t FROM debit_notes WHERE vendor_id=? {fy_cond} AND status='active'", p)
    debit_notes = cur.fetchone()["t"]

    cur.execute(f"SELECT COALESCE(SUM(amount),0) as t FROM vouchers WHERE vendor_id=? {fy_cond} AND type='payment' AND status='active'", p)
    payments = cur.fetchone()["t"]

    cur.execute(f"SELECT COALESCE(SUM(total_value),0) as t FROM credit_notes WHERE vendor_id=? {fy_cond} AND status='active'", p)
    credit_notes = cur.fetchone()["t"]

    conn.close()
    # Credits (Purchase + Credit Notes) increase payable
    # Debits (Payments + Debit Notes) reduce payable
    balance = opening + purchases + credit_notes - payments - debit_notes
    return {
        "opening": opening,
        "purchases": purchases,
        "debit_notes": debit_notes,
        "payments": payments,
        "credit_notes": credit_notes,
        "balance": balance,
    }


def get_vendor_outstanding_report(db_path, vendor_id, fy_id=None):
    """Invoice-level outstanding report consistent with ledger debit/credit logic.

    For every purchase invoice:
      Credit side  → Purchase amount + Credit Notes linked to invoice
      Debit side   → Payments adjusted + Debit Notes linked to invoice
      Balance      → Credit − Debit  (positive = payable, negative = advance)

    The vendor opening balance is shown as the first row (credit if positive,
    debit if negative) so the running total always reconciles with the ledger.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM vendors WHERE id=?", (vendor_id,))
    vendor = dict(cur.fetchone())

    fy_cond = "AND financial_year_id=?" if fy_id else ""
    p = [vendor_id] + ([fy_id] if fy_id else [])

    cur.execute(f"""SELECT id, voucher_no, date, invoice_number, total_value, narration
                    FROM purchases WHERE vendor_id=? {fy_cond} AND status='active'
                    ORDER BY date ASC, voucher_no ASC""", p)
    purchases = [dict(r) for r in cur.fetchall()]

    rows = []
    total_credit = 0
    total_debit = 0
    running = 0

    # Effective opening balance = original OB minus active OB payments for this vendor
    original_ob = vendor.get("opening_balance", 0) or 0
    cur.execute("""SELECT COALESCE(SUM(obp.amount),0) as paid
                   FROM opening_bal_payments obp
                   JOIN vouchers v ON v.id=obp.voucher_id
                   WHERE obp.vendor_id=? AND v.status='active'""", (vendor_id,))
    ob_paid = cur.fetchone()["paid"] or 0
    ob = original_ob - ob_paid

    if ob != 0:
        ob_cr = ob if ob > 0 else 0
        ob_dr = abs(ob) if ob < 0 else 0
        running += ob_cr - ob_dr
        total_credit += ob_cr
        total_debit += ob_dr
        rows.append({"date": "", "ref": "Opening Balance",
                     "description": "Opening Balance b/f",
                     "credit": ob_cr, "debit": ob_dr,
                     "balance": running, "type": "Opening Balance"})

    for purch in purchases:
        pid = purch["id"]
        inv_ref = purch.get("invoice_number") or purch["voucher_no"]

        # Credit notes linked to this invoice (credit → increases payable)
        cur.execute("""SELECT COALESCE(SUM(total_value),0) as t
                       FROM credit_notes WHERE ref_purchase_id=? AND status='active'""", (pid,))
        cn = cur.fetchone()["t"]

        # Debit notes linked to this invoice (debit → reduces payable)
        cur.execute("""SELECT COALESCE(SUM(total_value),0) as t
                       FROM debit_notes WHERE ref_purchase_id=? AND status='active'""", (pid,))
        dn = cur.fetchone()["t"]

        # Payments adjusted against this invoice (debit → reduces payable)
        cur.execute("""SELECT COALESCE(SUM(pa.amount),0) as t
                       FROM payment_adjustments pa
                       JOIN vouchers v ON pa.voucher_id=v.id
                       WHERE pa.purchase_id=? AND v.status='active'""", (pid,))
        pay = cur.fetchone()["t"]

        cr = purch["total_value"] + cn
        dr = pay + dn
        running += cr - dr
        total_credit += cr
        total_debit += dr
        rows.append({"date": purch["date"], "ref": inv_ref,
                     "description": purch.get("narration") or f"Purchase | Inv: {inv_ref}",
                     "credit": cr, "debit": dr,
                     "balance": running, "type": "Invoice"})

    conn.close()
    return {
        "name": vendor["name"],
        "opening_balance": ob,
        "rows": rows,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "net_balance": total_credit - total_debit,
    }


def get_vendor_remaining_ob(db_path, vendor_id):
    """Remaining opening balance = original OB minus amount already paid by active OB payments."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(opening_balance,0) as ob FROM vendors WHERE id=?", (vendor_id,))
    row = cur.fetchone()
    original_ob = (row["ob"] if row else 0) or 0
    cur.execute("""SELECT COALESCE(SUM(obp.amount),0) as paid
                   FROM opening_bal_payments obp
                   JOIN vouchers v ON v.id=obp.voucher_id
                   WHERE obp.vendor_id=? AND v.status='active'""", (vendor_id,))
    ob_paid = (cur.fetchone()["paid"] or 0)
    conn.close()
    remaining = original_ob - ob_paid
    return max(0.0, remaining) if original_ob >= 0 else min(0.0, remaining)


def get_vendor_advance_balance(db_path, vendor_id):
    """Return advance balance (positive = advance given to vendor).
    Advance exists when payments exceed purchases+credits+OB.
    """
    bal = get_vendor_balance(db_path, vendor_id)
    net = bal["balance"]
    return max(0.0, -net)  # negative net balance means vendor owes us → advance


def get_unapplied_payments(db_path, vendor_id):
    """Return list of payment vouchers with unapplied amounts (potential advances)."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""SELECT v.id, v.voucher_no, v.date, v.amount
                   FROM vouchers v
                   WHERE v.vendor_id=? AND v.type='payment' AND v.status='active'
                   ORDER BY v.date ASC, v.voucher_no ASC""", (vendor_id,))
    vouchers = [dict(r) for r in cur.fetchall()]
    result = []
    for v in vouchers:
        cur.execute("SELECT COALESCE(SUM(amount),0) as t FROM payment_adjustments WHERE voucher_id=?",
                    (v["id"],))
        inv_applied = cur.fetchone()["t"] or 0
        cur.execute("SELECT COALESCE(SUM(amount),0) as t FROM opening_bal_payments WHERE voucher_id=?",
                    (v["id"],))
        ob_applied = cur.fetchone()["t"] or 0
        unapplied = v["amount"] - inv_applied - ob_applied
        if unapplied > 0.001:
            result.append({**v, "unapplied": round(unapplied, 2)})
    conn.close()
    return result


def apply_advance_to_purchase(db_path, purchase_id, vendor_id):
    """Auto-apply any unapplied advance payments against a newly created purchase.
    Returns total advance amount applied.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT outstanding FROM purchases WHERE id=?", (purchase_id,))
    row = cur.fetchone()
    remaining_outstanding = row["outstanding"] if row else 0
    if remaining_outstanding <= 0:
        conn.close()
        return 0

    # Get unapplied payments in order (oldest first)
    cur.execute("""SELECT v.id, v.amount FROM vouchers v
                   WHERE v.vendor_id=? AND v.type='payment' AND v.status='active'
                   ORDER BY v.date ASC, v.id ASC""", (vendor_id,))
    payments = [dict(r) for r in cur.fetchall()]
    total_applied = 0

    for pmt in payments:
        vid = pmt["id"]
        cur.execute("SELECT COALESCE(SUM(amount),0) as t FROM payment_adjustments WHERE voucher_id=?",
                    (vid,))
        inv_used = cur.fetchone()["t"] or 0
        cur.execute("SELECT COALESCE(SUM(amount),0) as t FROM opening_bal_payments WHERE voucher_id=?",
                    (vid,))
        ob_used = cur.fetchone()["t"] or 0
        unapplied = pmt["amount"] - inv_used - ob_used
        if unapplied <= 0.001:
            continue
        apply = min(unapplied, remaining_outstanding)
        cur.execute(
            "INSERT INTO payment_adjustments(voucher_id,purchase_id,amount) VALUES(?,?,?)",
            (vid, purchase_id, apply)
        )
        cur.execute(
            "UPDATE purchases SET outstanding=MAX(0,outstanding-?) WHERE id=?",
            (apply, purchase_id)
        )
        remaining_outstanding -= apply
        total_applied += apply
        if remaining_outstanding <= 0.001:
            break

    conn.commit()
    conn.close()
    return round(total_applied, 2)


def get_pending_invoices(db_path, vendor_id, fy_id=None):
    """Returns pending invoices. Each row has 'display_label' = vendor invoice no or PV no + inv date."""
    rows = get_purchases(db_path, vendor_id=vendor_id, outstanding_only=True)
    for r in rows:
        inv_ref  = r.get("invoice_number") or r["voucher_no"]
        inv_date = r.get("invoice_date") or ""
        r["display_label"] = f"{inv_ref}  {inv_date}" if inv_date else inv_ref
    return rows


# ── Balance Report ────────────────────────────────────────────────────────────

def get_balance_report(db_path, as_on_date=None, fy_id=None):
    """Trial-balance-style report: all vendors and expense heads as of a given date.

    Balance logic follows get_vendor_balance / get_vendor_ledger:
      Vendor balance = effective_OB + purchases + credit_notes - payments - debit_notes
      Positive → Credit column (payable to vendor)
      Negative → Debit column (advance paid / vendor owes us)

    Expense heads are always Debit (expense is a debit).
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    dc = "AND date<=?" if as_on_date else ""
    dp = [as_on_date] if as_on_date else []

    cur.execute("SELECT id, name, opening_balance FROM vendors WHERE category='creditor' ORDER BY name")
    vendors_raw = [dict(r) for r in cur.fetchall()]

    vendor_rows = []
    for v in vendors_raw:
        vid = v["id"]
        ob = v["opening_balance"] or 0

        # Effective OB = original OB minus active OB-payments up to as_on_date
        ob_dc = "AND v2.date<=?" if as_on_date else ""
        ob_dp = [vid] + ([as_on_date] if as_on_date else [])
        cur.execute(f"""SELECT COALESCE(SUM(obp.amount),0) as paid
                        FROM opening_bal_payments obp
                        JOIN vouchers v2 ON v2.id=obp.voucher_id
                        WHERE obp.vendor_id=? AND v2.status='active' {ob_dc}""", ob_dp)
        ob_paid = (cur.fetchone()["paid"] or 0)
        effective_ob = ob - ob_paid

        cur.execute(f"SELECT COALESCE(SUM(total_value),0) as t FROM purchases WHERE vendor_id=? AND status='active' {dc}", [vid] + dp)
        purchases = cur.fetchone()["t"]

        cur.execute(f"SELECT COALESCE(SUM(total_value),0) as t FROM credit_notes WHERE vendor_id=? AND status='active' {dc}", [vid] + dp)
        credit_notes = cur.fetchone()["t"]

        cur.execute(f"SELECT COALESCE(SUM(amount),0) as t FROM vouchers WHERE vendor_id=? AND type='payment' AND status='active' {dc}", [vid] + dp)
        payments = cur.fetchone()["t"]

        cur.execute(f"SELECT COALESCE(SUM(total_value),0) as t FROM debit_notes WHERE vendor_id=? AND status='active' {dc}", [vid] + dp)
        debit_notes = cur.fetchone()["t"]

        balance = effective_ob + purchases + credit_notes - payments - debit_notes
        if abs(balance) < 0.001:
            continue

        debit  = round(abs(balance), 2) if balance < 0 else 0
        credit = round(balance, 2)      if balance > 0 else 0
        vendor_rows.append({"name": v["name"], "debit": debit, "credit": credit})

    cur.execute("SELECT id, name FROM expense_heads ORDER BY name")
    heads_raw = [dict(r) for r in cur.fetchall()]

    expense_rows = []
    for h in heads_raw:
        hid = h["id"]
        exp_dc = "AND date<=?" if as_on_date else ""
        cur.execute(f"SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE expense_head_id=? AND status='active' {exp_dc}",
                    [hid] + dp)
        total = cur.fetchone()["t"]
        if total < 0.001:
            continue
        expense_rows.append({"name": h["name"], "debit": round(total, 2), "credit": 0})

    conn.close()
    return {"vendors": vendor_rows, "expenses": expense_rows}


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard_stats(db_path, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    fy_cond = "AND financial_year_id=?" if fy_id else ""
    p = [fy_id] if fy_id else []

    cur.execute(f"SELECT COUNT(*) as c FROM vouchers WHERE status='active' {fy_cond}", p)
    total_v = cur.fetchone()["c"]

    cur.execute(f"SELECT COALESCE(SUM(amount),0) as t FROM vouchers WHERE type='payment' AND status='active' {fy_cond}", p)
    total_p = cur.fetchone()["t"]

    cur.execute(f"SELECT COALESCE(SUM(amount),0) as t FROM vouchers WHERE type='transfer' AND status='active' {fy_cond}", p)
    total_t = cur.fetchone()["t"]

    cur.execute(f"SELECT COALESCE(SUM(total_value),0) as t FROM purchases WHERE status='active' {fy_cond}", p)
    total_purchases = cur.fetchone()["t"]

    cur.execute("SELECT COUNT(*) as c FROM vendors")
    vc = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM accounts")
    ac = cur.fetchone()["c"]

    cur.execute(f"""
        SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
        FROM vouchers WHERE type='payment' AND status='active' {fy_cond}
        GROUP BY month ORDER BY month ASC LIMIT 12
    """, p)
    monthly = [dict(r) for r in cur.fetchall()]

    cur.execute(f"""
        SELECT v.*, vn.name as vendor_name, fa.name as from_account_name, ta.name as to_account_name
        FROM vouchers v
        LEFT JOIN vendors vn ON v.vendor_id=vn.id
        LEFT JOIN accounts fa ON v.from_account_id=fa.id
        LEFT JOIN accounts ta ON v.to_account_id=ta.id
        WHERE v.status='active' {fy_cond}
        ORDER BY v.created_at DESC LIMIT 8
    """, p)
    recent = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"total_vouchers": total_v, "total_payments": total_p,
            "total_transfers": total_t, "total_purchases": total_purchases,
            "vendor_count": vc, "account_count": ac,
            "monthly_payments": monthly, "recent_vouchers": recent}


# ── Day Book (all voucher types) ──────────────────────────────────────────────

def get_daybook_entries(db_path, date_from=None, date_to=None, vendor_id=None,
                        account_id=None, voucher_no_filter=None,
                        amount_min=None, amount_max=None,
                        name_filter=None, invoice_no_filter=None,
                        vtype=None, include_cancelled=False, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    results = []

    status_cond = "" if include_cancelled else "AND v.status='active'"
    fy_cond = "AND v.financial_year_id=?" if fy_id else ""
    nf = f"%{name_filter}%" if name_filter else None

    def date_conditions():
        c, p = "", []
        if date_from:
            c += " AND v.date>=?"
            p.append(date_from)
        if date_to:
            c += " AND v.date<=?"
            p.append(date_to)
        return c, p

    dc, dp = date_conditions()

    # Payment & Transfer vouchers
    if not vtype or vtype in ("payment", "transfer"):
        q = f"""
            SELECT v.id, v.voucher_no, 'payment_transfer' as src_table, v.type,
                   v.status, v.date, v.amount, v.narration,
                   vn.name as vendor_name, fa.name as from_account_name, ta.name as to_account_name
            FROM vouchers v
            LEFT JOIN vendors vn ON v.vendor_id=vn.id
            LEFT JOIN accounts fa ON v.from_account_id=fa.id
            LEFT JOIN accounts ta ON v.to_account_id=ta.id
            WHERE 1=1 {status_cond} {fy_cond} {dc}
        """
        p = (([fy_id] if fy_id else []) + dp)
        if vtype in ("payment", "transfer"):
            q += f" AND v.type='{vtype}'"
        if vendor_id:
            q += " AND v.vendor_id=?"
            p.append(vendor_id)
        if account_id:
            q += " AND (v.from_account_id=? OR v.to_account_id=?)"
            p.extend([account_id, account_id])
        if voucher_no_filter:
            q += " AND v.voucher_no LIKE ?"
            p.append(f"%{voucher_no_filter}%")
        if amount_min is not None:
            q += " AND v.amount>=?"
            p.append(amount_min)
        if amount_max is not None:
            q += " AND v.amount<=?"
            p.append(amount_max)
        if nf:
            q += " AND (LOWER(vn.name) LIKE LOWER(?) OR LOWER(fa.name) LIKE LOWER(?) OR LOWER(ta.name) LIKE LOWER(?))"
            p.extend([nf, nf, nf])
        cur.execute(q, p)
        results += [dict(r) for r in cur.fetchall()]

    # Purchase vouchers
    if not vtype or vtype == "purchase":
        sc = "" if include_cancelled else "AND p.status='active'"
        fyc = "AND p.financial_year_id=?" if fy_id else ""
        q = f"""
            SELECT p.id, p.voucher_no, 'purchases' as src_table, 'purchase' as type,
                   p.status, p.date, p.total_value as amount, p.narration,
                   v.name as vendor_name, NULL as from_account_name, NULL as to_account_name
            FROM purchases p LEFT JOIN vendors v ON p.vendor_id=v.id
            WHERE 1=1 {sc} {fyc} {dc}
        """
        pp = (([fy_id] if fy_id else []) + dp)
        if vendor_id:
            q += " AND p.vendor_id=?"
            pp.append(vendor_id)
        if voucher_no_filter:
            q += " AND p.voucher_no LIKE ?"
            pp.append(f"%{voucher_no_filter}%")
        if amount_min is not None:
            q += " AND p.total_value>=?"
            pp.append(amount_min)
        if amount_max is not None:
            q += " AND p.total_value<=?"
            pp.append(amount_max)
        if invoice_no_filter:
            q += " AND p.invoice_number LIKE ?"
            pp.append(f"%{invoice_no_filter}%")
        if nf:
            q += " AND LOWER(v.name) LIKE LOWER(?)"
            pp.append(nf)
        cur.execute(q, pp)
        results += [dict(r) for r in cur.fetchall()]

    # Credit Notes
    if not vtype or vtype == "credit_note":
        sc = "" if include_cancelled else "AND cn.status='active'"
        fyc = "AND cn.financial_year_id=?" if fy_id else ""
        q = f"""
            SELECT cn.id, cn.voucher_no, 'credit_notes' as src_table, 'credit_note' as type,
                   cn.status, cn.date, cn.total_value as amount, cn.narration,
                   v.name as vendor_name, NULL as from_account_name, NULL as to_account_name
            FROM credit_notes cn LEFT JOIN vendors v ON cn.vendor_id=v.id
            WHERE 1=1 {sc} {fyc} {dc}
        """
        pp = (([fy_id] if fy_id else []) + dp)
        if vendor_id:
            q += " AND cn.vendor_id=?"
            pp.append(vendor_id)
        if voucher_no_filter:
            q += " AND cn.voucher_no LIKE ?"
            pp.append(f"%{voucher_no_filter}%")
        if invoice_no_filter:
            q += " AND cn.ref_invoice_no LIKE ?"
            pp.append(f"%{invoice_no_filter}%")
        if amount_min is not None:
            q += " AND cn.total_value>=?"
            pp.append(amount_min)
        if amount_max is not None:
            q += " AND cn.total_value<=?"
            pp.append(amount_max)
        if nf:
            q += " AND LOWER(v.name) LIKE LOWER(?)"
            pp.append(nf)
        cur.execute(q, pp)
        results += [dict(r) for r in cur.fetchall()]

    # Debit Notes
    if not vtype or vtype == "debit_note":
        sc = "" if include_cancelled else "AND dn.status='active'"
        fyc = "AND dn.financial_year_id=?" if fy_id else ""
        q = f"""
            SELECT dn.id, dn.voucher_no, 'debit_notes' as src_table, 'debit_note' as type,
                   dn.status, dn.date, dn.total_value as amount, dn.narration,
                   v.name as vendor_name, NULL as from_account_name, NULL as to_account_name
            FROM debit_notes dn LEFT JOIN vendors v ON dn.vendor_id=v.id
            WHERE 1=1 {sc} {fyc} {dc}
        """
        pp = (([fy_id] if fy_id else []) + dp)
        if vendor_id:
            q += " AND dn.vendor_id=?"
            pp.append(vendor_id)
        if voucher_no_filter:
            q += " AND dn.voucher_no LIKE ?"
            pp.append(f"%{voucher_no_filter}%")
        if invoice_no_filter:
            q += " AND dn.ref_invoice_no LIKE ?"
            pp.append(f"%{invoice_no_filter}%")
        if amount_min is not None:
            q += " AND dn.total_value>=?"
            pp.append(amount_min)
        if amount_max is not None:
            q += " AND dn.total_value<=?"
            pp.append(amount_max)
        if nf:
            q += " AND LOWER(v.name) LIKE LOWER(?)"
            pp.append(nf)
        cur.execute(q, pp)
        results += [dict(r) for r in cur.fetchall()]

    # Expenses
    if not vtype or vtype == "expense":
        sc = "" if include_cancelled else "AND e.status='active'"
        fyc = "AND e.financial_year_id=?" if fy_id else ""
        dc_e, dp_e = "", []
        if date_from:
            dc_e += " AND e.date>=?"
            dp_e.append(date_from)
        if date_to:
            dc_e += " AND e.date<=?"
            dp_e.append(date_to)
        q = f"""
            SELECT e.id, e.voucher_no, 'expenses' as src_table, 'expense' as type,
                   e.status, e.date, e.amount, e.narration,
                   NULL as vendor_name, a.name as from_account_name,
                   eh.name as to_account_name
            FROM expenses e
            LEFT JOIN accounts a ON e.from_account_id=a.id
            LEFT JOIN expense_heads eh ON e.expense_head_id=eh.id
            WHERE 1=1 {sc} {fyc} {dc_e}
        """
        pp = (([fy_id] if fy_id else []) + dp_e)
        if voucher_no_filter:
            q += " AND e.voucher_no LIKE ?"
            pp.append(f"%{voucher_no_filter}%")
        if amount_min is not None:
            q += " AND e.amount>=?"
            pp.append(amount_min)
        if amount_max is not None:
            q += " AND e.amount<=?"
            pp.append(amount_max)
        if nf:
            q += " AND (LOWER(a.name) LIKE LOWER(?) OR LOWER(eh.name) LIKE LOWER(?))"
            pp.extend([nf, nf])
        cur.execute(q, pp)
        results += [dict(r) for r in cur.fetchall()]

    conn.close()
    results.sort(key=lambda x: (x["date"], x["voucher_no"]))
    return results


# ── Ledger ────────────────────────────────────────────────────────────────────

def get_vendor_ledger(db_path, vendor_id, date_from=None, date_to=None, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM vendors WHERE id=?", (vendor_id,))
    vendor = dict(cur.fetchone())

    fy_cond = "AND financial_year_id=?" if fy_id else ""
    dc = ""
    dp_base = ([fy_id] if fy_id else [])
    if date_from:
        dc += " AND date>=?"
    if date_to:
        dc += " AND date<=?"
    dp = dp_base + ([date_from] if date_from else []) + ([date_to] if date_to else [])

    cur.execute(f"SELECT id,'purchase' as type,date,voucher_no,invoice_number,invoice_date,total_value as amount,narration FROM purchases WHERE vendor_id=? AND status='active' {fy_cond} {dc} ORDER BY date ASC, voucher_no ASC",
                [vendor_id] + dp)
    purchases = [dict(r) for r in cur.fetchall()]

    cur.execute(f"SELECT id,'payment' as type,date,voucher_no,amount,narration FROM vouchers WHERE vendor_id=? AND type='payment' AND status='active' {fy_cond} {dc} ORDER BY date ASC, voucher_no ASC",
                [vendor_id] + dp)
    payments = [dict(r) for r in cur.fetchall()]

    cur.execute(f"SELECT id,'credit_note' as type,date,voucher_no,total_value as amount,narration FROM credit_notes WHERE vendor_id=? AND status='active' {fy_cond} {dc} ORDER BY date ASC, voucher_no ASC",
                [vendor_id] + dp)
    credits = [dict(r) for r in cur.fetchall()]

    cur.execute(f"SELECT id,'debit_note' as type,date,voucher_no,total_value as amount,narration FROM debit_notes WHERE vendor_id=? AND status='active' {fy_cond} {dc} ORDER BY date ASC, voucher_no ASC",
                [vendor_id] + dp)
    debits = [dict(r) for r in cur.fetchall()]

    # Get OB payment amounts per voucher (to split payment rows correctly)
    payment_ids = [p["id"] for p in payments]
    ob_by_voucher = {}
    if payment_ids:
        placeholders = ",".join("?" * len(payment_ids))
        cur.execute(
            f"SELECT voucher_id, COALESCE(SUM(amount),0) as ob_amt "
            f"FROM opening_bal_payments WHERE vendor_id=? AND voucher_id IN ({placeholders}) "
            f"GROUP BY voucher_id",
            [vendor_id] + payment_ids)
        for row in cur.fetchall():
            ob_by_voucher[row["voucher_id"]] = row["ob_amt"] or 0

    # Show the FULL original OB — OB payments will appear as separate debit rows
    original_ob = vendor.get("opening_balance", 0) or 0
    conn.close()

    raw = []
    if original_ob != 0:
        # Positive OB = Credit (payable); Negative OB = Debit (advance paid)
        raw.append({"date": "", "voucher_no": "-", "type": "Opening Balance",
                    "description": "Opening Balance brought forward",
                    "credit": original_ob if original_ob > 0 else 0,
                    "debit": abs(original_ob) if original_ob < 0 else 0,
                    "invoice_number": "", "invoice_date": "",
                    "src_id": None, "src_table": None})
    for p in purchases:
        inv_ref = p.get("invoice_number") or p["voucher_no"]
        raw.append({"date": p["date"], "voucher_no": p["voucher_no"], "type": "Purchase",
                    "description": p["narration"] or f"Purchase | Inv: {inv_ref}",
                    "ref_number": inv_ref,
                    "invoice_number": p.get("invoice_number") or "",
                    "invoice_date":   p.get("invoice_date") or "",
                    "credit": p["amount"], "debit": 0,
                    "src_id": p["id"], "src_table": "purchases"})
    for p in credits:
        raw.append({"date": p["date"], "voucher_no": p["voucher_no"], "type": "Credit Note",
                    "description": p["narration"] or f"Credit Note | {p['voucher_no']}",
                    "ref_number": p["voucher_no"],
                    "invoice_number": "", "invoice_date": "",
                    "credit": p["amount"], "debit": 0,
                    "src_id": p["id"], "src_table": "credit_notes"})
    for p in payments:
        ob_amt = ob_by_voucher.get(p["id"], 0)
        regular_amt = round(p["amount"] - ob_amt, 2)
        # OB portion → shown as a separate "OB Payment" row
        if ob_amt > 0:
            raw.append({"date": p["date"], "voucher_no": p["voucher_no"], "type": "OB Payment",
                        "description": f"Opening Balance Payment | {p['voucher_no']}",
                        "ref_number": p["voucher_no"],
                        "invoice_number": "", "invoice_date": "",
                        "debit": ob_amt, "credit": 0,
                        "src_id": p["id"], "src_table": "vouchers"})
        # Regular (non-OB) portion → shown as normal Payment row
        if regular_amt > 0:
            raw.append({"date": p["date"], "voucher_no": p["voucher_no"], "type": "Payment",
                        "description": p["narration"] or f"Payment to {vendor['name']}",
                        "ref_number": p["voucher_no"],
                        "invoice_number": "", "invoice_date": "",
                        "debit": regular_amt, "credit": 0,
                        "src_id": p["id"], "src_table": "vouchers"})
    for p in debits:
        raw.append({"date": p["date"], "voucher_no": p["voucher_no"], "type": "Debit Note",
                    "description": p["narration"] or f"Debit Note | {p['voucher_no']}",
                    "ref_number": p["voucher_no"],
                    "invoice_number": "", "invoice_date": "",
                    "debit": p["amount"], "credit": 0,
                    "src_id": p["id"], "src_table": "debit_notes"})

    raw.sort(key=lambda x: (x["date"] or "", x["voucher_no"]))
    balance = 0
    entries = []
    for r in raw:
        # Credit increases payable; Debit reduces payable
        balance = balance + r["credit"] - r["debit"]
        entries.append({**r, "balance": balance})
    return {"name": vendor["name"], "opening_balance": original_ob,
            "closing_balance": balance, "entries": entries}


def get_account_ledger(db_path, account_id, date_from=None, date_to=None, fy_id=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (account_id,))
    account = dict(cur.fetchone())
    opening = account["opening_balance"]

    fy_cond = "AND financial_year_id=?" if fy_id else ""
    dp_base = ([fy_id] if fy_id else [])
    dc = ""
    if date_from:
        dc += " AND date>=?"
    if date_to:
        dc += " AND date<=?"
    dp = dp_base + ([date_from] if date_from else []) + ([date_to] if date_to else [])

    cur.execute(f"""SELECT v.id, v.voucher_no, v.date, v.amount, v.narration, v.type,
                       vn.name as vendor_name, 'from' as dir
                FROM vouchers v LEFT JOIN vendors vn ON v.vendor_id=vn.id
                WHERE v.from_account_id=? AND v.status='active' {fy_cond} {dc}
                ORDER BY v.date ASC, v.voucher_no ASC""",
                [account_id] + dp)
    from_v = [dict(r) for r in cur.fetchall()]

    cur.execute(f"""SELECT v.id, v.voucher_no, v.date, v.amount, v.narration, v.type,
                       fa.name as from_name, 'to' as dir
                FROM vouchers v LEFT JOIN accounts fa ON v.from_account_id=fa.id
                WHERE v.to_account_id=? AND v.status='active' {fy_cond} {dc}
                ORDER BY v.date ASC, v.voucher_no ASC""",
                [account_id] + dp)
    to_v = [dict(r) for r in cur.fetchall()]
    conn.close()

    raw, seen = [], set()
    if opening != 0:
        raw.append({"date": "", "voucher_no": "-", "type": "Opening Balance",
                    "description": "Opening Balance",
                    "debit": 0, "credit": opening, "src_id": None, "src_table": None})
    for v in from_v:
        if v["id"] not in seen:
            seen.add(v["id"])
            description = v["narration"] or (f"Payment to {v['vendor_name']}" if v.get("vendor_name") else "Transfer out")
            raw.append({"date": v["date"], "voucher_no": v["voucher_no"], "type": v["type"].title(),
                        "description": description, "debit": v["amount"], "credit": 0,
                        "src_id": v["id"], "src_table": "vouchers"})
    for v in to_v:
        if v["id"] not in seen:
            seen.add(v["id"])
            raw.append({"date": v["date"], "voucher_no": v["voucher_no"], "type": "Transfer In",
                        "description": v["narration"] or "Transfer in", "debit": 0, "credit": v["amount"],
                        "src_id": v["id"], "src_table": "vouchers"})
    raw.sort(key=lambda x: (x["date"] or "", x["voucher_no"]))

    balance = 0
    entries = []
    for r in raw:
        balance = balance + r["credit"] - r["debit"]
        entries.append({**r, "balance": balance})
    return {"name": account["name"], "opening_balance": opening, "closing_balance": balance, "entries": entries}


def update_note(db_path, table, note_id, date_str, vendor_id, ref_purchase_id,
                value, gst_amount, narration):
    conn = get_connection(db_path)
    cur = conn.cursor()
    # Preserve existing fy_id if no FY matches the new date
    fy = get_fy_for_date(db_path, date_str)
    if fy:
        fy_id = fy["id"]
    else:
        cur.execute(f"SELECT financial_year_id FROM {table} WHERE id=?", (note_id,))
        row = cur.fetchone()
        fy_id = row["financial_year_id"] if row else None
    total = value + gst_amount
    cur.execute(f"""UPDATE {table} SET date=?,vendor_id=?,ref_purchase_id=?,
                    value=?,gst_amount=?,total_value=?,narration=?,financial_year_id=?
                    WHERE id=?""",
                (date_str, vendor_id, ref_purchase_id,
                 value, gst_amount, total, narration or None, fy_id, note_id))
    conn.commit()
    conn.close()


# ── Financial Year Carry Forward ──────────────────────────────────────────────

def carry_forward_fy(db_path, new_fy_label, new_start, new_end, fy_type):
    """Create new FY and carry forward ONLY creditor vendor balances + pending invoices.
    Does NOT carry forward Cash/Bank account totals or expense balances.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Create the new FY
    cur.execute(
        "INSERT INTO financial_years(label,start_date,end_date,fy_type,is_active) VALUES(?,?,?,?,1)",
        (new_fy_label, new_start, new_end, fy_type)
    )
    new_fy_id = cur.lastrowid
    # Deactivate all others
    cur.execute("UPDATE financial_years SET is_active=0 WHERE id!=?", (new_fy_id,))

    # Carry forward vendor balances (creditors only)
    cur.execute("SELECT id FROM vendors WHERE category='creditor'")
    creditors = [r["id"] for r in cur.fetchall()]
    conn.commit()
    conn.close()

    for vendor_id in creditors:
        bal = get_vendor_balance(db_path, vendor_id)  # all-time balance
        if bal["balance"] != 0:
            update_vendor_opening(db_path, vendor_id, bal["balance"])

    # NOTE: Cash/Bank accounts are NOT carried forward.
    # Pending invoices (outstanding > 0) remain accessible across FYs naturally.
    return new_fy_id


def update_vendor_opening(db_path, vendor_id, opening_balance):
    conn = get_connection(db_path)
    conn.execute("UPDATE vendors SET opening_balance=? WHERE id=?", (opening_balance, vendor_id))
    conn.commit()
    conn.close()
