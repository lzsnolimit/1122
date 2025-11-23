import json
import logging
import os
import re
import sqlite3
import time
from typing import Any, Dict, Optional

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
except Exception as e:  # pragma: no cover
    raise RuntimeError(f"Missing langchain-openai dependency or incompatible version: {e}")


DB_PATH = "data.db"
RESOURCES_DIR = "CODE_GEN/resources"


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


def _ensure_price_column() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(advises)")
        cols = cur.fetchall()
        names = {c[1] for c in cols}
        if "price" not in names:
            cur.execute("ALTER TABLE advises ADD COLUMN price REAL")
            conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _is_chinese_text(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _insert_advice(row: Dict[str, Any]) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO advises (symbol, advice_action, advice_strength, reason, predicted_at, price)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["symbol"],
                row["advice_action"],
                row["advice_strength"],
                row["reason"],
                int(row["predicted_at"]),
                float(row["price"]) if row.get("price") is not None else None,
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
        - Call `langchain-openai` ChatOpenAI (model: gpt-5) with medium reasoning (via prompt),
          without explicitly setting temperature.
        - Validate output fields and insert into `data.db` (table: advises) including `price`.

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

    system_msg = SystemMessage(
        content=(
            "你是加密资产投资顾问。必须以严格 JSON 输出以下字段："
            "symbol(advice symbol), advice_action(buy|hold|sell), advice_strength(high|medium|low),"
            "reason(中文), predicted_at(UNIX秒), price(number)。"
            "请采用中等推理力度（medium reasoning effort），保持输出简洁、可读。"
        )
    )

    human_msg = HumanMessage(
        content=(
            f"symbol: {symbol}\n"
            f"social_media_analysis: {social_context}\n"
            f"symbol_24h_resource_summary: {json.dumps(summary, ensure_ascii=False)}\n"
            f"analysis_results: {analysis_results}\n"
            "请综合以上信息，输出上述 JSON 字段，reason 必须为中文。"
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

    if symbol_out != symbol:
        raise ValueError("LLM output symbol mismatch")
    if action not in {"buy", "hold", "sell"}:
        raise ValueError("Invalid advice_action")
    if strength not in {"high", "medium", "low"}:
        raise ValueError("Invalid advice_strength")
    if not isinstance(reason, str) or not reason.strip() or not _is_chinese_text(reason):
        raise ValueError("reason must be non-empty Chinese text")
    if not isinstance(predicted_at, (int, float)):
        # keep minimal fallback: use current time seconds
        predicted_at = int(time.time())
    else:
        predicted_at = int(predicted_at)

    # Prefer extracted latest price over model-produced price to ensure consistency
    final_price = latest_price

    # Ensure price is numeric
    if not isinstance(final_price, (int, float)):
        raise ValueError("Missing numeric price for insert")

    # Ensure DB schema and insert
    _ensure_price_column()
    row = {
        "symbol": symbol,
        "advice_action": action,
        "advice_strength": strength,
        "reason": reason.strip(),
        "predicted_at": predicted_at,
        "price": float(final_price),
    }

    try:
        _insert_advice(row)
        logging.info("Inserted advice: %s @ %d", symbol, predicted_at)
        return content
    except Exception as e:
        raise RuntimeError(f"Failed to insert advice: {e}")

if __name__ == "__main__":
    print(llm_summary(symbol="BTC",analysis_results="数据面乐观"))