# src/db.py
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "shelf.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    frame_ts TEXT,
    item TEXT,
    count INTEGER
);
CREATE TABLE IF NOT EXISTS daily (
    item TEXT,
    date TEXT,
    units INTEGER,
    revenue REAL,
    PRIMARY KEY (item, date)
);
CREATE TABLE IF NOT EXISTS inventory (
    item TEXT PRIMARY KEY,
    last_count INTEGER,
    updated_at TEXT
);
"""

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)

@contextmanager
def connect():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()
