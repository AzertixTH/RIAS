import sqlite3
import os
from datetime import datetime, timezone, timedelta

DB_PATH = os.path.expanduser("~/Obsidian/Saga/trading/signals.db")

# Minimum % move to count as correct (filters out noise)
MIN_MOVE_PCT = 0.1


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT NOT NULL,
                pair         TEXT NOT NULL,
                timeframe    TEXT NOT NULL,
                direction    TEXT NOT NULL,
                horizon      TEXT NOT NULL,
                confidence   TEXT NOT NULL,
                price        REAL NOT NULL,
                target_time  TEXT NOT NULL,
                reasoning    TEXT,
                verified     INTEGER DEFAULT 0,
                correct      INTEGER
            )
        """)


def _normalize_direction(direction: str) -> str:
    """Normalize direction to one of: bullish, bearish, neutral."""
    d = direction.strip().lower()
    if d in ("bullish", "bull", "long", "up"):
        return "bullish"
    if d in ("bearish", "bear", "short", "down"):
        return "bearish"
    # Both "neutral" and "neutraal" (Dutch) → normalize to English
    if d in ("neutral", "neutraal", "flat", "range", "sideways"):
        return "neutral"
    # Unknown: pass through (will be handled by verification)
    return d


def log_signal(pair, timeframe, direction, horizon, confidence, price, reasoning="") -> str:
    direction = _normalize_direction(direction)
    horizon_hours = {"1h": 1, "4h": 4, "24h": 24}.get(horizon, 4)
    now = datetime.now(timezone.utc)
    target = now + timedelta(hours=horizon_hours)

    with _conn() as con:
        con.execute("""
            INSERT INTO signals
            (timestamp, pair, timeframe, direction, horizon, confidence, price, target_time, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now.isoformat(),
            pair, timeframe, direction, horizon, confidence,
            price,
            target.isoformat(),
            reasoning,
        ))
    return f"Signaal gelogd: {pair} {direction} ({horizon}, {confidence}) @ ${price:,.2f}"


def get_unverified_expired() -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT * FROM signals
            WHERE verified = 0 AND target_time <= ?
        """, (now,)).fetchall()
    return [dict(r) for r in rows]


def mark_verified(signal_id: int, correct: bool):
    with _conn() as con:
        con.execute("""
            UPDATE signals SET verified = 1, correct = ?
            WHERE id = ?
        """, (1 if correct else 0, signal_id))


def is_correct_prediction(direction: str, ref_price: float, current_price: float) -> bool | None:
    """
    Determine if a prediction was correct.
    Returns True/False, or None if it cannot be determined.
    """
    direction = _normalize_direction(direction)

    if direction == "bullish":
        move_pct = (current_price - ref_price) / ref_price * 100
        return move_pct >= MIN_MOVE_PCT

    if direction == "bearish":
        move_pct = (ref_price - current_price) / ref_price * 100
        return move_pct >= MIN_MOVE_PCT

    if direction == "neutral":
        # Correct if price stayed within the threshold (flat move)
        move_pct = abs(current_price - ref_price) / ref_price * 100
        return move_pct <= MIN_MOVE_PCT

    # Unknown direction — can't evaluate
    return None


def get_accuracy() -> str:
    with _conn() as con:
        # Overall
        row = con.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) as done,
                SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as hits
            FROM signals
        """).fetchone()
        total, done, hits = row[0], row[1] or 0, row[2] or 0

        # By direction
        rows = con.execute("""
            SELECT direction, COUNT(*) as cnt, SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) as h
            FROM signals
            WHERE verified = 1
            GROUP BY direction
        """).fetchall()

    if not done:
        return "Nog geen geverifieerde signalen."

    lines = [f"**Overall: {hits}/{done} correct ({round(hits/done*100)}%) — {total - done} pending**", ""]
    for dir_name, cnt, h in rows:
        h = h or 0
        if dir_name in ("neutral", "neutraal"):
            label = "neutral"
        else:
            label = dir_name
        lines.append(f"  {label}: {h}/{cnt} ({round(h/cnt*100) if cnt else 0}%)")

    return "\n".join(lines)


def get_recent(n: int = 10) -> str:
    with _conn() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT * FROM signals ORDER BY id DESC LIMIT ?
        """, (n,)).fetchall()
    if not rows:
        return "Geen signalen."
    lines = []
    for r in rows:
        status = "✓" if r["correct"] == 1 else ("✗" if r["correct"] == 0 else "?")
        lines.append(
            f"[{status}] {r['pair']} {r['direction']} ({r['horizon']}, {r['confidence']}) "
            f"@ ${r['price']:,.2f} — {r['timestamp'][:16]}"
        )
    return "\n".join(lines)
