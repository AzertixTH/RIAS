from .base import BaseAgent
from tools.binance import analyze_market, get_price
from tools.trading_db import init_db, log_signal, get_recent, get_accuracy
from config import TRADING_MODEL

init_db()

TRADING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_market",
            "description": "Fetch live price data and calculate RSI, MACD, Bollinger Bands, ADX, and volume for a symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol":   {"type": "string", "description": "e.g. BTCUSDT or ETHUSDT"},
                    "interval": {"type": "string", "description": "15m, 1h, 4h, 1d"}
                },
                "required": ["symbol", "interval"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_signal",
            "description": "Log a trading signal prediction to the database for accuracy tracking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair":       {"type": "string", "description": "e.g. BTCUSDT"},
                    "timeframe":  {"type": "string", "description": "15m, 1h, 4h"},
                    "direction":  {"type": "string", "description": "bullish / bearish / neutral"},
                    "horizon":    {"type": "string", "description": "1h / 4h / 24h"},
                    "confidence": {"type": "string", "description": "low / medium / high"},
                    "price":      {"type": "number", "description": "Current price at time of signal"},
                    "reasoning":  {"type": "string"}
                },
                "required": ["pair", "timeframe", "direction", "horizon", "confidence", "price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_signals",
            "description": "Get recent logged signals with their verification status.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer", "description": "Number of signals to return (default 10)"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_accuracy",
            "description": "Get overall prediction accuracy broken down by direction.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]


class TradingAgent(BaseAgent):
    model = TRADING_MODEL
    tools = TRADING_TOOLS

    def _execute_tool(self, name: str, args: dict) -> str:
        if name == "analyze_market":
            return analyze_market(args.get("symbol", "BTCUSDT"), args.get("interval", "15m"))
        if name == "log_signal":
            return log_signal(
                pair=args["pair"],
                timeframe=args["timeframe"],
                direction=args["direction"],
                horizon=args["horizon"],
                confidence=args["confidence"],
                price=args["price"],
                reasoning=args.get("reasoning", ""),
            )
        if name == "get_recent_signals":
            return get_recent(args.get("n", 10))
        if name == "get_accuracy":
            return get_accuracy()
        return f"Unknown tool: {name}"
