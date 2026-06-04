import threading
import time

from tools.binance import get_price
from tools.trading_db import init_db, log_signal, get_unverified_expired, mark_verified, is_correct_prediction
from agents.trading import TradingAgent

PAIRS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["15m", "1h"]
INTERVAL_SECONDS = 30 * 60


def _parse_price(raw: str) -> float:
    """
    Parse price from get_price() output.
    Expected format: 'BTCUSDT: $73,876.00'
    """
    # Find the last colon, take everything after it
    price_part = raw.rsplit(":", 1)[-1].strip()
    # Remove $ and commas
    price_part = price_part.replace("$", "").replace(",", "")
    return float(price_part)


def _verify_expired():
    expired = get_unverified_expired()
    for sig in expired:
        try:
            raw = get_price(sig["pair"])
            current = _parse_price(raw)
            ref = sig["price"]

            result = is_correct_prediction(sig["direction"], ref, current)
            if result is not None:
                mark_verified(sig["id"], result)
            else:
                # Unknown direction — skip verification
                pass
        except Exception:
            pass


def _watch_cycle(agent: TradingAgent):
    _verify_expired()
    for pair in PAIRS:
        for tf in TIMEFRAMES:
            try:
                agent.run(
                    f"Analyseer {pair} op {tf} timeframe. "
                    f"Gebruik analyze_market en log daarna een signaal met log_signal. "
                    f"Geef direction (bullish/bearish/neutral), horizon (1h/4h/24h) "
                    f"en confidence (low/medium/high)."
                )
            except Exception:
                pass


def _loop(agent: TradingAgent):
    init_db()
    while True:
        _watch_cycle(agent)
        time.sleep(INTERVAL_SECONDS)


_watcher_thread: threading.Thread | None = None


def start_watcher():
    global _watcher_thread
    if _watcher_thread and _watcher_thread.is_alive():
        return "Watcher loopt al."
    agent = TradingAgent()
    _watcher_thread = threading.Thread(target=_loop, args=(agent,), daemon=True)
    _watcher_thread.start()
    return "Loki watcher gestart."


def watcher_status() -> str:
    if _watcher_thread and _watcher_thread.is_alive():
        return "Loki watcher: actief"
    return "Loki watcher: gestopt"
