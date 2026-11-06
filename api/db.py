import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("KINCARE_DB", Path(__file__).resolve().parent.parent / "data" / "kincare.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    alert_month TEXT NOT NULL,
    published TEXT,
    url TEXT NOT NULL UNIQUE,
    pdf_url TEXT,
    file TEXT,
    rows INTEGER DEFAULT 0,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    product_name TEXT NOT NULL,
    brand TEXT,
    batch_no TEXT NOT NULL,
    batch_norm TEXT NOT NULL,
    mfg_date TEXT,
    expiry TEXT,
    manufacturer TEXT,
    manufacturer_full TEXT,
    reason TEXT,
    reported_by TEXT,
    remarks TEXT,
    alert_month TEXT NOT NULL,
    alert_url TEXT NOT NULL,
    pdf_page INTEGER,
    UNIQUE (batch_norm, product_name, document_id)
);
CREATE INDEX IF NOT EXISTS idx_alerts_batch ON alerts(batch_norm);
CREATE TABLE IF NOT EXISTS watchlist (
    device TEXT NOT NULL,
    batch TEXT NOT NULL,
    brand TEXT,
    maker TEXT,
    added_at TEXT NOT NULL,
    last_verdict TEXT NOT NULL,
    last_checked_at TEXT NOT NULL,
    PRIMARY KEY (device, batch)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, id);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY,
    run_id TEXT,
    channel TEXT NOT NULL,
    name TEXT,
    phone TEXT NOT NULL,
    language TEXT NOT NULL,
    batch TEXT NOT NULL,
    alert_id INTEGER,
    message TEXT NOT NULL,
    status TEXT NOT NULL,
    provider_id TEXT,
    at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    pharmacy TEXT,
    city TEXT,
    customer TEXT,
    phone TEXT,
    language TEXT DEFAULT 'hi',
    product TEXT,
    batch TEXT NOT NULL,
    batch_norm TEXT NOT NULL,
    sold_at TEXT
);
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    name TEXT,
    phone TEXT,
    language TEXT,
    batch TEXT NOT NULL,
    alert_id INTEGER,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    responded_at TEXT,
    feeling TEXT,
    symptoms TEXT,
    bp_sys INTEGER,
    bp_dia INTEGER,
    note TEXT,
    triage TEXT,
    reviewed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    member TEXT NOT NULL DEFAULT 'Me',
    at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    temp_c REAL, bp_sys INTEGER, bp_dia INTEGER, pulse INTEGER, spo2 INTEGER,
    source TEXT DEFAULT 'manual',
    level TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    member TEXT NOT NULL DEFAULT 'Me',
    doctor TEXT,
    diagnosis TEXT,
    start_date TEXT NOT NULL,
    advice TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE IF NOT EXISTS plan_meds (
    id INTEGER PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    name TEXT NOT NULL, strength TEXT, food TEXT,
    morning INTEGER, noon INTEGER, night INTEGER,
    days INTEGER, as_needed INTEGER DEFAULT 0,
    batch TEXT
);
CREATE TABLE IF NOT EXISTS doses (
    med_id INTEGER NOT NULL REFERENCES plan_meds(id),
    day TEXT NOT NULL,
    slot TEXT NOT NULL,
    taken_at TEXT,
    PRIMARY KEY (med_id, day, slot)
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    batch TEXT NOT NULL,
    batch_norm TEXT NOT NULL,
    brand TEXT, maker TEXT, city TEXT,
    symptoms TEXT NOT NULL,
    onset_days INTEGER,
    origin TEXT DEFAULT 'user',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (device, batch_norm)
);
CREATE INDEX IF NOT EXISTS reports_batch ON reports(batch_norm);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    plan TEXT NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    email TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    paid_at TEXT
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    relation TEXT
);
CREATE TABLE IF NOT EXISTS sos_events (
    id INTEGER PRIMARY KEY,
    device TEXT NOT NULL,
    member TEXT,
    lat REAL, lng REAL,
    message TEXT,
    delivered INTEGER DEFAULT 0,
    at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS pharmacy_state (
    device TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")  # readers don't block the recall engine's writes
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # Columns added after the first release.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(watchlist)")}
    for col, ddl in (("phone", "TEXT"), ("language", "TEXT DEFAULT 'hi'"), ("name", "TEXT"), ("member", "TEXT"), ("expiry", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE watchlist ADD COLUMN {col} {ddl}")
    # Purchase details, filled when the patient buys a prescribed medicine.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(plan_meds)")}
    for col, ddl in (("bought_at", "TEXT"), ("phone", "TEXT"), ("language", "TEXT DEFAULT 'hi'"), ("pharmacy", "TEXT"), ("expiry", "TEXT"), ("maker", "TEXT"),
                     ("qty", "REAL"), ("refill_sent_at", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE plan_meds ADD COLUMN {col} {ddl}")
    conn.execute("CREATE TABLE IF NOT EXISTS reminders_sent (med_id INTEGER, day TEXT, slot TEXT, sent_at TEXT, PRIMARY KEY (med_id, day, slot))")
    conn.commit()
    return conn


class ThreadConnection:
    """One sqlite connection per thread, behind a single `conn` object.

    FastAPI runs sync endpoints on a thread pool. A single shared connection (check_same_thread=False) let parallel
    requests trample each other's cursors: COUNT(*) came back as None, "bad parameter or other API misuse", 500s.
    Autocommit, so a pooled thread never sits on an open write transaction and blocks the others; conn.commit() is a no-op.
    """

    def __init__(self):
        import threading

        self._local = threading.local()
        connect().close()  # schema + migrations once, up front

    def _get(self) -> sqlite3.Connection:
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA busy_timeout=30000")
            c.execute("PRAGMA synchronous=NORMAL")  # WAL-safe; FULL fsyncs every autocommit write (4x slower)
            self._local.c = c
        return c

    def __getattr__(self, name):
        return getattr(self._get(), name)
