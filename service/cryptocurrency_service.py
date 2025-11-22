from typing import Dict, Any, List
import asyncio
import json

try:
    # spoon-toolkits provides CEX market data access
    from spoon_toolkits.crypto.crypto_powerdata.tools import CryptoPowerDataCEXTool
except Exception:
    CryptoPowerDataCEXTool = None  # type: ignore


def get_tracking_cryptocurrenc() -> List[str]:
    """Return the ten most active cryptocurrencies as hardcoded symbols."""

    return [
        "USDT",
        "BTC",
        "ETH",
        "USDC",
        "SOL",
        "XRP",
        "ZEC",
        "BNB",
        "DOGE",
        "BSC-USD",
    ]


async def async_get_symbol_24h_data(
    symbol: str,
    exchange: str = "kraken",
    quote: str = "USD",
    timeframe: str = "1h",
) -> Dict[str, Any]:
    """
    Fetch last 24 hours of market data for the given symbol.

    - Uses spoon_toolkits CryptoPowerDataCEXTool (CEX data source).
    - Aggregates 24 bars of "1h" OHLCV into 24h stats (high/low/volume/change).

    Args:
        symbol: Base asset symbol, e.g., "BTC".
        exchange: CEX name supported by CCXT (default: "kraken").
        quote: Quote currency, e.g., "USD" or "USDT".
        timeframe: Candlestick timeframe (default: "1h").

    Returns:
        A dictionary with fields:
        - pair: full trading pair (e.g., "BTC/USD")
        - exchange, timeframe
        - bars: list of dicts [{timestamp, open, high, low, close, volume, ...}]
        - stats: {open_24h, close_latest, high_24h, low_24h, volume_24h, change_24h_abs, change_24h_percent}
        - source, error
    """

    if CryptoPowerDataCEXTool is None:
        return {
            "pair": f"{symbol}/{quote}",
            "exchange": exchange,
            "timeframe": timeframe,
            "bars": [],
            "stats": {},
            "source": "missing spoon_toolkits",
            "error": "spoon_toolkits not available",
        }

    tool = CryptoPowerDataCEXTool()

    # Include indicator config to align with spoon examples (optional)
    indicators_config = json.dumps(
        {
            "rsi": [{"timeperiod": 14}],
            "ema": [{"timeperiod": 12}, {"timeperiod": 26}],
            "macd": [{"fastperiod": 12, "slowperiod": 26}],
        }
    )

    # Fetch 24 bars of 1h data to represent last 24 hours
    result = await tool.execute(
        exchange=exchange,
        symbol=f"{symbol}/{quote}",
        timeframe=timeframe,
        limit=24,
        use_enhanced=True,
        indicators_config=indicators_config,
    )

    # Handle tool errors
    if getattr(result, "error", None):
        return {
            "pair": f"{symbol}/{quote}",
            "exchange": exchange,
            "timeframe": timeframe,
            "bars": [],
            "stats": {},
            "source": "spoon_toolkits.crypto_powerdata",
            "error": result.error,
        }

    bars: List[Dict[str, Any]] = result.output or []

    # Compute 24h aggregates
    open_24h = bars[0]["open"] if bars else None
    close_latest = bars[-1]["close"] if bars else None
    high_24h = max((b.get("high") for b in bars), default=None) if bars else None
    low_24h = min((b.get("low") for b in bars), default=None) if bars else None
    volume_24h = sum((b.get("volume") or 0.0 for b in bars)) if bars else None

    change_24h_abs = None
    change_24h_percent = None
    if open_24h is not None and close_latest is not None and open_24h != 0:
        change_24h_abs = close_latest - open_24h
        change_24h_percent = (change_24h_abs / open_24h) * 100.0

    return {
        "pair": f"{symbol}/{quote}",
        "exchange": exchange,
        "timeframe": timeframe,
        "bars": bars,
        "stats": {
            "open_24h": open_24h,
            "close_latest": close_latest,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "volume_24h": volume_24h,
            "change_24h_abs": change_24h_abs,
            "change_24h_percent": change_24h_percent,
        },
        "source": "spoon_toolkits.crypto_powerdata",
        "error": None,
    }


def get_symbol_24h_data(
    symbol: str,
    exchange: str = "kraken",
    quote: str = "USD",
    timeframe: str = "1h",
) -> Dict[str, Any]:
    """
    Sync wrapper for `async_get_symbol_24h_data`.

    If called within an existing asyncio loop, prefer using the async function.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Cannot block a running event loop from a sync function.
        raise RuntimeError(
            "get_symbol_24h_data() called in a running event loop. "
            "Use await async_get_symbol_24h_data(...) instead."
        )
    return asyncio.run(async_get_symbol_24h_data(symbol, exchange, quote, timeframe))
if __name__ == "__main__":
    for symbol in get_tracking_cryptocurrenc():
        print(symbol+":")
        print(get_symbol_24h_data(symbol=symbol,exchange="kraken"))
        print("\n")