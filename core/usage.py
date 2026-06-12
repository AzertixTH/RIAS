import os
import sqlite3
import time
import requests
from datetime import datetime, timedelta
from config import LLM_API_KEY, LLM_BASE_URL

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "usage.db")


def _connect():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS usage_log (ts TEXT NOT NULL, tokens INTEGER NOT NULL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_log_ts ON usage_log (ts)")
    return conn


def log_usage(tokens: int):
    if not tokens:
        return
    conn = _connect()
    conn.execute("INSERT INTO usage_log (ts, tokens) VALUES (?, ?)", (datetime.now().isoformat(), tokens))
    conn.commit()
    conn.close()


def daily_totals(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    conn = _connect()
    rows = conn.execute(
        "SELECT substr(ts, 1, 10) AS day, SUM(tokens) FROM usage_log WHERE ts >= ? GROUP BY day ORDER BY day",
        (since,),
    ).fetchall()
    conn.close()
    return [{"date": day, "tokens": tokens} for day, tokens in rows]


def period_totals() -> dict:
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    month_start = now.strftime("%Y-%m-01")

    conn = _connect()

    def _sum_since(date_str):
        row = conn.execute("SELECT SUM(tokens) FROM usage_log WHERE ts >= ?", (date_str,)).fetchone()
        return row[0] or 0

    result = {
        "today": _sum_since(today),
        "week": _sum_since(week_start),
        "month": _sum_since(month_start),
        "all_time": conn.execute("SELECT SUM(tokens) FROM usage_log").fetchone()[0] or 0,
    }
    conn.close()
    return result


_openrouter_cache: dict = {"data": None, "ts": 0.0}
_OPENROUTER_CACHE_TTL = 60.0


def fetch_openrouter_usage() -> dict | None:
    if not LLM_API_KEY or "openrouter" not in LLM_BASE_URL:
        return None

    if _openrouter_cache["data"] is not None and time.time() - _openrouter_cache["ts"] < _OPENROUTER_CACHE_TTL:
        return _openrouter_cache["data"]

    try:
        res = requests.get(
            "https://openrouter.ai/api/v1/key",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            timeout=5,
        )
        res.raise_for_status()
        data = res.json().get("data", {})
        result = {
            "usage": data.get("usage"),
            "usage_daily": data.get("usage_daily"),
            "usage_weekly": data.get("usage_weekly"),
            "usage_monthly": data.get("usage_monthly"),
            "limit": data.get("limit"),
            "limit_remaining": data.get("limit_remaining"),
        }
    except Exception:
        result = _openrouter_cache["data"]

    _openrouter_cache["data"] = result
    _openrouter_cache["ts"] = time.time()
    return result
