import json
import logging
import os
import re
import sqlite3
import time
import sys
from typing import Any, Dict, Optional

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
except Exception as e:  # pragma: no cover
    raise RuntimeError(f"Missing langchain-openai dependency or incompatible version: {e}")


DB_PATH = "data.db"
RESOURCES_DIR = "CODE_GEN/resources"

# Ensure repository root is on sys.path for imports like `service.*`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_latest_price(symbol_resource: Dict[str, Any]) -> Optional[float]:
    stats = symbol_resource.get("stats") or {}
    price = stats.get("close_latest")
    if isinstance(price, (int, float)):
        return float(price)
    bars = symbol_resource.get("bars") or []
    if bars:
        last = bars[-1]
        close = last.get("close")
        if isinstance(close, (int, float)):
            return float(close)
    return None


def _ensure_extended_columns() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(advises)")
        cols = cur.fetchall()
        names = {c[1] for c in cols}
        migrations = []
        if "price" not in names:
            migrations.append("ALTER TABLE advises ADD COLUMN price REAL")
        if "change_24h_percent" not in names:
            migrations.append("ALTER TABLE advises ADD COLUMN change_24h_percent REAL")
        if "sentiment_score" not in names:
            migrations.append("ALTER TABLE advises ADD COLUMN sentiment_score REAL")
        if "volume_24h" not in names:
            migrations.append("ALTER TABLE advises ADD COLUMN volume_24h REAL")
        if "market_capacity" not in names:
            migrations.append("ALTER TABLE advises ADD COLUMN market_capacity REAL")

        for sql in migrations:
            cur.execute(sql)
        if migrations:
            conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _is_english_text(text: str) -> bool:
    """Heuristic English check: must contain A–Z letters and no CJK.

    This is intentionally simple and avoids heavy dependencies. It will
    treat ASCII-lettered content (with digits/punctuation/spaces) as English
    as long as it doesn't include CJK codepoints.
    """
    if not isinstance(text, str):
        return False
    if _contains_cjk(text):
        return False
    return bool(re.search(r"[A-Za-z]", text))


def _insert_advice(row: Dict[str, Any]) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO advises (
              symbol,
              advice_action,
              advice_strength,
              reason,
              predicted_at,
              price,
              change_24h_percent,
              sentiment_score,
              volume_24h,
              market_capacity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["symbol"],
                row["advice_action"],
                row["advice_strength"],
                row["reason"],
                int(row["predicted_at"]),
                float(row["price"]) if row.get("price") is not None else None,
                float(row["change_24h_percent"]) if row.get("change_24h_percent") is not None else None,
                float(row["sentiment_score"]) if row.get("sentiment_score") is not None else None,
                float(row["volume_24h"]) if row.get("volume_24h") is not None else None,
                float(row["market_capacity"]) if row.get("market_capacity") is not None else None,
            ),
        )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def llm_summary(symbol: str, analysis_results: str) -> None:
    """
    Generate an investment advice using LLM with aggregated context and persist to SQLite.

    Inputs:
        symbol: Target crypto symbol, e.g., "BTC".
        analysis_results: String containing consolidated outputs from analysis functions.

    Behavior:
        - Read social media context from `CODE_GEN/resources/social_media_analysis.txt`.
        - Read `{symbol}.txt` resource JSON for 24h data and price.
        - Call `langchain-openai` ChatOpenAI (model: gpt-5) with medium reasoning (via prompt).
        - Require `reason` to be English and to synthesize: social media sentiment, the
          provided analysis results, and the current price context from stats/last bar.
        - Request and store additional numeric fields: change_24h_percent, sentiment_score (0-1),
          volume_24h, market_capacity. Prefer values derivable from provided stats when available.
        - Validate output fields and insert into `data.db` (table: advises) including `price` and extras.

    Raises:
        RuntimeError or ValueError on missing env, context, price, or invalid model output.
    """

    if not symbol or not isinstance(symbol, str):
        raise ValueError("symbol must be a non-empty string")


    social_path = os.path.join(RESOURCES_DIR, "social_media_analysis.txt")
    symbol_path = os.path.join(RESOURCES_DIR, f"{symbol}.txt")

    # Read context files (no excessive fallbacks)
    try:
        social_context = _read_text(social_path)
    except Exception as e:
        raise RuntimeError(f"Failed to read social media analysis: {e}")

    try:
        symbol_resource = _read_json(symbol_path)
    except Exception as e:
        raise RuntimeError(f"Failed to read symbol resource JSON: {e}")

    # Extract latest price; fail if unavailable
    latest_price = _extract_latest_price(symbol_resource)
    if latest_price is None:
        raise RuntimeError("Latest price not available in symbol resource")

    # Prepare a compact resource summary to avoid sending full payload
    summary = {
        "pair": symbol_resource.get("pair"),
        "exchange": symbol_resource.get("exchange"),
        "timeframe": symbol_resource.get("timeframe"),
        "stats": symbol_resource.get("stats", {}),
        # last bar snapshot (if exists)
        "last_bar": (symbol_resource.get("bars") or [{}])[-1],
    }

    # Initialize model
    try:
        model = ChatOpenAI(
            model="gpt-5"        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize ChatOpenAI: {e}")

    # Derive helpful stats for robustness and to avoid model hallucination
    stats = summary.get("stats") or {}
    derived_change_pct = None
    if isinstance(stats.get("change_24h_percent"), (int, float)):
        derived_change_pct = float(stats["change_24h_percent"])
    else:
        try:
            o = stats.get("open_24h")
            c = stats.get("close_latest") or latest_price
            if isinstance(o, (int, float)) and isinstance(c, (int, float)) and o:
                derived_change_pct = (float(c) - float(o)) / float(o) * 100.0
        except Exception:
            derived_change_pct = None

    derived_volume_24h = stats.get("volume_24h") if isinstance(stats.get("volume_24h"), (int, float)) else None
    # Use quote_volume_24h as a proxy for market capacity/liquidity if market cap isn't present
    derived_market_capacity = (
        stats.get("quote_volume_24h") if isinstance(stats.get("quote_volume_24h"), (int, float)) else None
    )

    system_msg = SystemMessage(
        content=(
            "You are a crypto investment advisor. Respond strictly as JSON with the fields: "
            "symbol (advice symbol), advice_action (buy|hold|sell), advice_strength (high|medium|low), "
            "reason (English), predicted_at (UNIX seconds), price (number), "
            "change_24h_percent (number), sentiment_score (0-1), volume_24h (number), market_capacity (number). "
            "Use a medium reasoning effort and keep output concise and readable. "
            "The reason MUST synthesize three aspects: (1) social media sentiment, "
            "(2) the provided analysis results, and (3) price data/trend from the resource summary."
        )
    )

    human_msg = HumanMessage(
        content=(
            f"symbol: {symbol}\n"
            f"social_media_analysis: {social_context}\n"
            f"symbol_24h_resource_summary: {json.dumps(summary, ensure_ascii=False)}\n"
            f"analysis_results: {analysis_results}\n"
            "Output the JSON fields listed by the system message. The reason must be in English "
            "and explicitly synthesize social sentiment, the analysis results, and price data/trend. "
            "For numeric fields: if the resource summary includes a value (e.g., change_24h_percent, volume_24h, "
            "quote_volume_24h as market_capacity), copy that value; otherwise, estimate based on provided data."
        )
    )

    # Invoke model and parse JSON
    try:
        resp = model.invoke([system_msg, human_msg])
    except Exception as e:
        raise RuntimeError(f"LLM invocation failed: {e}")

    content = getattr(resp, "content", None)
    if not content or not isinstance(content, str):
        raise RuntimeError("LLM returned empty content")

    try:
        data = json.loads(content)
    except Exception as e:
        raise RuntimeError(f"LLM output is not valid JSON: {e}\nRaw: {content}")

    # Validate fields (minimal, no excessive fallbacks)
    symbol_out = data.get("symbol")
    action = data.get("advice_action")
    strength = data.get("advice_strength")
    reason = data.get("reason")
    predicted_at = data.get("predicted_at")
    price_out = data.get("price")
    change_24h_percent_out = data.get("change_24h_percent")
    sentiment_score_out = data.get("sentiment_score")
    volume_24h_out = data.get("volume_24h")
    market_capacity_out = data.get("market_capacity")

    if symbol_out != symbol:
        raise ValueError("LLM output symbol mismatch")
    if action not in {"buy", "hold", "sell"}:
        raise ValueError("Invalid advice_action")
    if strength not in {"high", "medium", "low"}:
        raise ValueError("Invalid advice_strength")
    if not isinstance(reason, str) or not reason.strip() or not _is_english_text(reason):
        raise ValueError("reason must be non-empty English text without CJK characters")
    if not isinstance(predicted_at, (int, float)):
        # keep minimal fallback: use current time seconds
        predicted_at = int(time.time())
    else:
        predicted_at = int(predicted_at)

    # Prefer extracted latest price over model-produced price to ensure consistency
    final_price = latest_price

    # Resolve extended numeric fields, preferring derived stats
    final_change_pct = None
    if isinstance(derived_change_pct, (int, float)):
        final_change_pct = float(derived_change_pct)
    elif isinstance(change_24h_percent_out, (int, float)):
        final_change_pct = float(change_24h_percent_out)

    final_volume_24h = None
    if isinstance(derived_volume_24h, (int, float)):
        final_volume_24h = float(derived_volume_24h)
    elif isinstance(volume_24h_out, (int, float)):
        final_volume_24h = float(volume_24h_out)

    final_market_capacity = None
    if isinstance(derived_market_capacity, (int, float)):
        final_market_capacity = float(derived_market_capacity)
    elif isinstance(market_capacity_out, (int, float)):
        final_market_capacity = float(market_capacity_out)

    final_sentiment = None
    if isinstance(sentiment_score_out, (int, float)):
        # Clamp to [0,1] as required
        final_sentiment = max(0.0, min(1.0, float(sentiment_score_out)))

    # Ensure price is numeric
    if not isinstance(final_price, (int, float)):
        raise ValueError("Missing numeric price for insert")

    # Ensure DB schema and insert
    _ensure_extended_columns()
    row = {
        "symbol": symbol,
        "advice_action": action,
        "advice_strength": strength,
        "reason": reason.strip(),
        "predicted_at": predicted_at,
        "price": float(final_price),
        "change_24h_percent": final_change_pct,
        "sentiment_score": final_sentiment,
        "volume_24h": final_volume_24h,
        "market_capacity": final_market_capacity,
    }

    try:
        _insert_advice(row)
        logging.info("Inserted advice: %s @ %d", symbol, predicted_at)
        return content
    except Exception as e:
        raise RuntimeError(f"Failed to insert advice: {e}")

if __name__ == "__main__":
    # Invoke llm_summary once for every tracked symbol
    try:
        from service.cryptocurrency_service import get_tracking_cryptocurrenc
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to import tracking symbols: {e}")

    symbols = get_tracking_cryptocurrenc()
    for sym in symbols:
        try:
            result = llm_summary(symbol=sym, analysis_results="Data analysis is optimistic")
            print(f"Processed {sym}: {bool(result)}")
        except Exception as e:
            # Continue processing other symbols if one fails
            logging.error("Failed processing %s: %s", sym, e)
            continue
