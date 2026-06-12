import os
import json
import sqlite3
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "conversations.db")


def _connect():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS conversations ("
        "id TEXT PRIMARY KEY, history TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    return conn


def save_history(session_id: str, history: list):
    conn = _connect()
    conn.execute(
        "INSERT INTO conversations (id, history, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET history = excluded.history, updated_at = excluded.updated_at",
        (session_id, json.dumps(history), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def load_history(session_id: str) -> list | None:
    conn = _connect()
    row = conn.execute("SELECT history FROM conversations WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None
