from typing import Dict, Any, List, Optional, Tuple
import asyncio
import json
import math
import statistics
import os

try:
    # spoon-toolkits provides CEX market data access
    from spoon_toolkits.crypto.crypto_powerdata.tools import (
        CryptoPowerDataCEXTool,
        get_cex_data_with_indicators,
    )
except Exception:
    CryptoPowerDataCEXTool = None  # type: ignore
    get_cex_data_with_indicators = None  # type: ignore


# Optional async CCXT fallback for real CEX calls when spoon_toolkits is missing
try:  # pragma: no cover - optional dependency
    import ccxt.async_support as ccxt_async  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ccxt_async = None  # type: ignore


async def _fetch_bars_ccxt(
    symbol: str,
    exchange: str,
    quote: str,
    timeframe: str,
    limit: int = 24,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Fetch OHLCV bars using ccxt async as a real-data fallback.

    Returns a tuple of (bars, resolved_pair). Each bar is a dict with
    keys: timestamp, open, high, low, close, volume.
    """
    if ccxt_async is None:
        raise RuntimeError("ccxt is not available for real-data fallback")

    ex_class = getattr(ccxt_async, exchange, None)
    if ex_class is None:
        raise ValueError(f"Unsupported exchange: {exchange}")

    ex = ex_class()
    try:
        await ex.load_markets()

        # Resolve market symbol considering exchange-specific naming (e.g., Kraken XBT)
        preferred = f"{symbol}/{quote}"
        market_symbol: Optional[str] = preferred if preferred in ex.markets else None

        if market_symbol is None:
            alt_bases = [symbol]
            if symbol.upper() == "BTC":
                alt_bases.append("XBT")  # Kraken naming
            alt_quotes = [quote, "USDT", "USD", "USDC", "EUR"]
            for b in alt_bases:
                for q in alt_quotes:
                    cand = f"{b}/{q}"
                    if cand in ex.markets:
                        market_symbol = cand
                        break
                if market_symbol is not None:
                    break

        if market_symbol is None:
            raise ValueError(f"No market found for {symbol} on {exchange}")

        ohlcv = await ex.fetch_ohlcv(market_symbol, timeframe=timeframe, limit=limit)
        bars: List[Dict[str, Any]] = []
        for item in ohlcv:
            # ccxt format: [timestamp, open, high, low, close, volume]
            ts, o, h, l, c, v = item
            bars.append(
                {
                    "timestamp": ts,
                    "open": float(o) if o is not None else None,
                    "high": float(h) if h is not None else None,
                    "low": float(l) if l is not None else None,
                    "close": float(c) if c is not None else None,
                    "volume": float(v) if v is not None else None,
                }
            )

        return bars, market_symbol
    finally:  # ensure proper cleanup of exchange resources
        try:
            await ex.close()
        except Exception:
            pass


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
        "DOGE"
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

    # Ensure we always perform real calls: use spoon_toolkits if available,
    # otherwise fall back to ccxt async. No mock or empty data.

    # Include richer indicator config to return more data in each bar
    indicators_config = json.dumps(
        {
            "ema": [{"timeperiod": 12}, {"timeperiod": 26}],
            "sma": [{"timeperiod": 20}],
            "rsi": [{"timeperiod": 14}],
            "macd": [{"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}],
            "atr": [{"timeperiod": 14}],
            "bbands": [{"timeperiod": 20, "nbdevup": 2, "nbdevdn": 2}],
            # Remove unsupported STOCH parameters to avoid warnings; use defaults
            "stoch": [{}],
            "adx": [{"timeperiod": 14}],
            "cci": [{"timeperiod": 14}],
            "obv": [{}],
        }
    )

    resolved_pair = f"{symbol}/{quote}"
    bars: List[Dict[str, Any]]

    # Prefer direct tool function when available
    if get_cex_data_with_indicators is not None:
        result = await get_cex_data_with_indicators(
            exchange=exchange,
            symbol=resolved_pair,
            timeframe=timeframe,
            limit=24,
            indicators_config=indicators_config,
            use_enhanced=True,
        )
        if not result.get("success"):
            # Fall back to ccxt if the tool function fails
            bars, resolved_pair = await _fetch_bars_ccxt(symbol, exchange, quote, timeframe, 24)
        else:
            bars = result.get("data", [])
    elif CryptoPowerDataCEXTool is not None:
        tool = CryptoPowerDataCEXTool()
        tool_result = await tool.execute(
            exchange=exchange,
            symbol=resolved_pair,
            timeframe=timeframe,
            limit=24,
            use_enhanced=True,
            indicators_config=indicators_config,
        )
        if getattr(tool_result, "error", None):
            # Fall back to ccxt if the toolkit class call fails
            bars, resolved_pair = await _fetch_bars_ccxt(symbol, exchange, quote, timeframe, 24)
        else:
            bars = tool_result.output or []
    else:
        # Spoon not available: use ccxt for real CEX data
        bars, resolved_pair = await _fetch_bars_ccxt(symbol, exchange, quote, timeframe, 24)

    # Compute 24h aggregates
    open_24h = bars[0].get("open") if bars else None
    close_latest = bars[-1].get("close") if bars else None
    high_24h = max((b.get("high") for b in bars), default=None) if bars else None
    low_24h = min((b.get("low") for b in bars), default=None) if bars else None
    volume_24h = sum((b.get("volume") or 0.0 for b in bars)) if bars else None

    # Additional aggregates
    closes = [b.get("close") for b in bars if b.get("close") is not None]
    vwap_24h = None
    twap_24h = None
    median_close_24h = None
    stddev_close_24h = None
    quote_volume_24h = None
    if bars and volume_24h and volume_24h > 0:
        vwap_24h = sum((b.get("close", 0.0) * (b.get("volume") or 0.0) for b in bars)) / volume_24h
        quote_volume_24h = sum((b.get("close", 0.0) * (b.get("volume") or 0.0) for b in bars))
    if closes:
        twap_24h = sum(closes) / len(closes)
        try:
            median_close_24h = statistics.median(closes)
        except statistics.StatisticsError:
            median_close_24h = None
        try:
            stddev_close_24h = statistics.pstdev(closes)
        except statistics.StatisticsError:
            stddev_close_24h = None

    change_24h_abs = None
    change_24h_percent = None
    log_return_24h_percent = None
    if open_24h is not None and close_latest is not None and open_24h != 0:
        change_24h_abs = close_latest - open_24h
        change_24h_percent = (change_24h_abs / open_24h) * 100.0
        try:
            log_return_24h_percent = math.log(close_latest / open_24h) * 100.0
        except Exception:
            log_return_24h_percent = None

    # True Range and volatility metrics across the window
    true_ranges: List[float] = []
    prev_close = None
    for b in bars:
        h = b.get("high")
        l = b.get("low")
        c = b.get("close")
        if h is None or l is None:
            continue
        if prev_close is None or c is None:
            tr = (h - l) if (h is not None and l is not None) else None
        else:
            tr = max(h - l, abs(h - prev_close), abs(prev_close - l))
        if tr is not None:
            true_ranges.append(tr)
        prev_close = c

    avg_true_range_24h = (sum(true_ranges) / len(true_ranges)) if true_ranges else None

    # Latest indicator snapshot (everything beyond core OHLCV)
    indicators_latest: Dict[str, Any] = {}
    if bars:
        latest = dict(bars[-1])
        for k, v in list(latest.items()):
            if k in {"timestamp", "open", "high", "low", "close", "volume"}:
                continue
            if v is not None:
                indicators_latest[k] = v

    # Remove None values from each bar to avoid collecting empty fields
    clean_bars: List[Dict[str, Any]] = []
    for b in bars:
        clean_bars.append({k: v for k, v in b.items() if v is not None})

    result_payload = {
        "pair": resolved_pair,
        "exchange": exchange,
        "timeframe": timeframe,
        "bars": clean_bars,
        "stats": {
            "open_24h": open_24h,
            "close_latest": close_latest,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "range_24h": (high_24h - low_24h) if (high_24h is not None and low_24h is not None) else None,
            "volume_24h": volume_24h,
            "quote_volume_24h": quote_volume_24h,
            "vwap_24h": vwap_24h,
            "twap_24h": twap_24h,
            "median_close_24h": median_close_24h,
            "stddev_close_24h": stddev_close_24h,
            "avg_true_range_24h": avg_true_range_24h,
            "change_24h_abs": change_24h_abs,
            "change_24h_percent": change_24h_percent,
            "log_return_24h_percent": log_return_24h_percent,
        },
        "indicators_latest": indicators_latest,
    }

    # Drop None values from stats
    result_payload["stats"] = {k: v for k, v in result_payload["stats"].items() if v is not None}

    return result_payload


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



def save_tracking_symbols_to_resources(
    exchange: str = "kraken",
    quote: str = "USD",
    timeframe: str = "1h",
    output_dir: str = "CODE_GEN/resources",
    symbols: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Fetch data for provided `symbols` if given; otherwise use
    `get_tracking_cryptocurrenc()` defaults. Save each symbol's dataset into
    `CODE_GEN/resources/{symbol}.txt`.

    Returns a mapping of `symbol -> file_path` for successfully written files.
    """

    os.makedirs(output_dir, exist_ok=True)
    written: Dict[str, str] = {}

    iteration_symbols = symbols if symbols else get_tracking_cryptocurrenc()

    for symbol in iteration_symbols:
        try:
            data = get_symbol_24h_data(
                symbol=symbol,
                exchange=exchange,
                quote=quote,
                timeframe=timeframe,
            )
            file_path = os.path.join(output_dir, f"{symbol}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, indent=2))
            written[symbol] = file_path
        except Exception as e:
            # Continue on error; do not raise to allow other symbols to be saved
            # You can inspect the error externally if needed.
            continue

    return written

if __name__ == "__main__":
    save_tracking_symbols_to_resources()
