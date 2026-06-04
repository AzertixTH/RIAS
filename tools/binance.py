import json
import urllib.request
from datetime import datetime, timezone

import pandas as pd

BINANCE_BASE = "https://api.binance.com/api/v3"


def _fetch(endpoint: str, params: dict) -> list:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BINANCE_BASE}/{endpoint}?{query}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def get_price(symbol: str = "BTCUSDT") -> str:
    data = _fetch("ticker/price", {"symbol": symbol})
    return f"{symbol}: ${float(data['price']):,.2f}"


def get_klines(symbol: str = "BTCUSDT", interval: str = "15m", limit: int = 120) -> pd.DataFrame:
    raw = _fetch("klines", {"symbol": symbol, "interval": interval, "limit": limit})
    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df


def _calc_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("inf"))
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def _calc_macd(close: pd.Series):
    macd_line = _ema(close, 12) - _ema(close, 26)
    signal_line = _ema(macd_line, 9)
    histogram = macd_line - signal_line
    return (
        round(float(macd_line.iloc[-1]), 4),
        round(float(signal_line.iloc[-1]), 4),
        round(float(histogram.iloc[-1]), 4),
    )


def _calc_bbands(close: pd.Series, period: int = 20):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return (
        round(float(lower.iloc[-1]), 2),
        round(float(sma.iloc[-1]), 2),
        round(float(upper.iloc[-1]), 2),
    )


def _calc_adx(df: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate the Average Directional Index (ADX).
    ADX >= 20 indicates a trending market.
    ADX < 20 indicates a ranging/consolidation market (no trade).
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # True Range
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move

    # Smoothed averages (Wilder's smoothing = EMA with alpha=1/period)
    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr

    # DX and ADX
    di_sum = plus_di + minus_di
    dx = 100 * (plus_di - minus_di).abs() / di_sum.replace(0, float("inf"))
    adx = dx.ewm(alpha=1 / period, min_periods=period).mean()

    return round(float(adx.iloc[-1]), 2)


def analyze_market(symbol: str = "BTCUSDT", interval: str = "15m") -> str:
    try:
        df = get_klines(symbol, interval, limit=120)
    except Exception as e:
        return f"Fout bij ophalen data voor {symbol}: {e}"

    close = df["close"]
    price = round(float(close.iloc[-1]), 2)

    rsi = _calc_rsi(close)
    macd, macd_sig, macd_hist = _calc_macd(close)
    bb_lower, bb_mid, bb_upper = _calc_bbands(close)
    adx = _calc_adx(df)

    vol_now = float(df["volume"].iloc[-1])
    vol_avg = float(df["volume"].rolling(20).mean().iloc[-1])
    vol_ratio = round(vol_now / vol_avg, 2) if vol_avg else 0

    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    signals = []
    if rsi < 30:
        signals.append(f"RSI {rsi} — oversold → bullish bias")
    elif rsi > 70:
        signals.append(f"RSI {rsi} — overbought → bearish bias")
    else:
        signals.append(f"RSI {rsi} — neutraal")

    if macd_hist > 0:
        signals.append(f"MACD histogram positief ({macd_hist:+.4f}) → bullish momentum")
    else:
        signals.append(f"MACD histogram negatief ({macd_hist:+.4f}) → bearish momentum")

    if price < bb_lower:
        signals.append(f"Prijs onder BB lower ({bb_lower}) → mogelijke reversal omhoog")
    elif price > bb_upper:
        signals.append(f"Prijs boven BB upper ({bb_upper}) → mogelijke reversal omlaag")
    else:
        bb_pct = round((price - bb_lower) / (bb_upper - bb_lower) * 100) if (bb_upper - bb_lower) else 50
        signals.append(f"Prijs in BB ({bb_pct}% van lower naar upper)")

    if vol_ratio >= 1.5:
        signals.append(f"Volume spike: {vol_ratio}x gemiddelde → bevestig beweging")
    elif vol_ratio < 0.7:
        signals.append(f"Laag volume ({vol_ratio}x gemiddelde) → zwakke beweging")

    # ADX regime filter
    if adx < 20:
        signals.append(f"**ADX {adx} < 20 — GEEN TREND → Geen signaal genereren (ranging market)**")
    else:
        signals.append(f"ADX {adx} ≥ 20 — trend aanwezig")

    lines = [
        f"**{symbol} | {interval} | {timestamp}**",
        f"Prijs: ${price:,}",
        f"RSI(14): {rsi}",
        f"MACD: {macd} | Signal: {macd_sig} | Hist: {macd_hist:+.4f}",
        f"Bollinger: {bb_lower} / {bb_mid} / {bb_upper}",
        f"Volume ratio: {vol_ratio}x",
        f"ADX(14): {adx}",
        "",
        "Signalen:",
    ] + [f"- {s}" for s in signals]

    return "\n".join(lines)
