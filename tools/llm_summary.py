from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, Optional


DB_PATH = "data.db"
RESOURCES_DIR = "CODE_GEN/resources"


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except Exception:
        return {}


def _safe_json(obj: Any, max_str_len: int = 2000) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        s = str(obj)
        if len(s) > max_str_len:
            s = s[:max_str_len] + "..."
        return s


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS advises (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          symbol TEXT NOT NULL,
          advice_action TEXT NOT NULL,
          advice_strength TEXT NOT NULL,
          reason TEXT,
          predicted_at INTEGER NOT NULL,
          created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        );
        """
    )


def _insert_advice(
    symbol: str,
    advice_action: str,
    advice_strength: str,
    reason: Optional[str],
    predicted_at: int,
) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO advises (symbol, advice_action, advice_strength, reason, predicted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (symbol, advice_action, advice_strength, reason, predicted_at),
        )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _build_messages(symbol: str, market_data: Dict[str, Any], social_summary: Optional[str], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    system = (
        "You are an investment analysis assistant. "
        "Only use the provided structured signals and summaries. "
        "If key data is missing or conflicting, prefer HOLD with low strength. "
        "Return a single JSON object with keys: symbol, advice_action (buy|hold|sell), "
        "advice_strength (high|medium|low), reason, predicted_at (unix seconds). "
        "Do not include any text outside the JSON."
    )

    user_payload = {
        "symbol": symbol,
        "market_data": market_data,
        "social_media_summary": social_summary or "",
        "analysis_results": {k: _safe_json(v) for k, v in (analysis_results or {}).items()},
        "decision_policy": {
            "strong_consensus": "Multiple independent signals strongly agree → buy/sell with high.",
            "mixed_signals": "Signals conflict or are weak → medium.",
            "insufficient_data": "Missing key signals/data → hold with low.",
        },
    }

    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
    }


def _call_llm(messages: Dict[str, Any], model: Optional[str] = None, temperature: float = 0.0, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Call OpenAI Chat Completions API using default endpoint.

    - API key is read from env var `TEM_OPENAI_KEY`.
    - Default model: `gpt-5` (override via arg or `LLM_MODEL`).
    - Reasoning effort: high.

    Returns parsed JSON dict or None on failure.
    """
    import urllib.request
    import urllib.error

    api_key = os.getenv("TEM_OPENAI_KEY")
    if not api_key:
        return None

    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": model or os.getenv("LLM_MODEL", "gpt-5"),
        "messages": messages.get("messages", []),
        "temperature": temperature,
        "max_tokens": 512,
        "reasoning": {"effort": "high"},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        payload = json.loads(raw)
        choices = payload.get("choices") or []
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content")
        if not content:
            return None
        try:
            return json.loads(content)
        except Exception:
            return None
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def _validate(advice: Dict[str, Any]) -> Dict[str, Any]:
    now = int(time.time())
    action = str(advice.get("advice_action", "hold")).lower()
    strength = str(advice.get("advice_strength", "low")).lower()
    reason = advice.get("reason")
    if action not in {"buy", "hold", "sell"}:
        action = "hold"
    if strength not in {"high", "medium", "low"}:
        strength = "low"
    try:
        ts = int(advice.get("predicted_at"))
    except Exception:
        ts = now
    return {
        "advice_action": action,
        "advice_strength": strength,
        "reason": None if reason is None else str(reason),
        "predicted_at": ts,
    }


def llm_summary(symbol: str, analysis_results: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    """
    Summarize signals for a symbol via LLM and persist a single advice row.

    Parameters:
        symbol: Target cryptocurrency symbol.
        analysis_results: Aggregated outputs from all analysis functions.
        model: Optional LLM model name (defaults via env LLM_MODEL).

    Returns:
        Dict with keys: symbol, advice_action, advice_strength, reason, predicted_at.
    """
    social_path = os.path.join(RESOURCES_DIR, "social_media_analysis.txt")
    symbol_path = os.path.join(RESOURCES_DIR, f"{symbol}.txt")

    social_summary = _read_text(social_path)
    market_data = _read_json(symbol_path)

    messages = _build_messages(symbol, market_data, social_summary, analysis_results)
    llm_output = _call_llm(messages, model=model)

    if not llm_output:
        # No fallback per requirements; enforce explicit configuration
        raise RuntimeError("llm_summary: LLM call failed or returned empty response. Ensure TEM_OPENAI_KEY is configured.")

    validated = _validate(llm_output)
    result = {
        "symbol": symbol,
        **validated,
    }

    _insert_advice(
        symbol=result["symbol"],
        advice_action=result["advice_action"],
        advice_strength=result["advice_strength"],
        reason=result.get("reason"),
        predicted_at=result["predicted_at"],
    )

    return result


def llm_select_attention(symbols: list[str], market_data: str) -> dict[str, Any]:
    """
    Ask LLM to select one attention symbol based on a free-form market data string.

    Parameters:
        symbols: Candidate symbols (e.g., ["BTC", "ETH"]).
        market_data: Plain text or JSON string of market context.

    Returns:
        Dict with shape:
            {
              "selected": [
                 {"symbol": str, "attention_score": float, "reasons": [str]}
              ],
              "generated_at": int
            }
    """

    system = (
        "You are a crypto market analyst."
        " Review the market context and pick exactly ONE symbol from the candidates"
        " that needs the most immediate attention (opportunity or risk)."
        " Return ONLY a JSON object with keys: selected (list with 1 item), generated_at."
        " Each item: {symbol, attention_score (0..1), reasons (array of strings)}."
    )

    user_payload = {
        "candidates": symbols,
        "market_data": str(market_data or "")[:5000],
        "score_definition": "0 (no attention) .. 1 (critical attention)",
    }

    messages = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
    }

    llm_output = _call_llm(messages)

    if not llm_output:
        raise RuntimeError("llm_select_attention: LLM call failed or returned empty response. Ensure TEM_OPENAI_KEY is configured.")

    selected = llm_output.get("selected")
    if isinstance(selected, dict):
        selected = [selected]
    if not isinstance(selected, list) or len(selected) == 0:
        raise ValueError("llm_select_attention: invalid LLM payload, `selected` is missing or empty.")

    item = selected[0]
    sym = str(item.get("symbol", "")).upper()
    if not sym:
        raise ValueError("llm_select_attention: selected item missing `symbol`.")
    if symbols and sym not in {s.upper() for s in symbols}:
        raise ValueError(f"llm_select_attention: symbol '{sym}' not in candidates: {symbols}.")
    try:
        score = float(item.get("attention_score", 0.0))
    except Exception as e:
        raise ValueError(f"llm_select_attention: attention_score invalid: {e}")
    reasons = item.get("reasons") or []
    if not isinstance(reasons, list):
        raise ValueError("llm_select_attention: reasons must be a list.")

    result = {
        "selected": [
            {
                "symbol": sym,
                "attention_score": max(0.0, min(1.0, score)),
                "reasons": [str(r) for r in reasons][:5],
            }
        ],
        "generated_at": int(time.time()),
    }
    return result


__all__ = ["llm_summary", "llm_select_attention"]

