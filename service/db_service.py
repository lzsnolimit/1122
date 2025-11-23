from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

DB_PATH = "data.db"


def _connect_readonly() -> sqlite3.Connection:
    """Return a read-only SQLite connection if possible; fall back to rw."""
    try:
        # Use URI to open the database in read-only mode when available
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except Exception:
        # Fall back to regular connection (e.g., file may not exist yet)
        return sqlite3.connect(DB_PATH)


def get_last_10_advises() -> List[Dict[str, Any]]:
    """
    Fetch the most recent 10 investment advises from SQLite.

    Sorting: predicted_at DESC, rowid DESC to ensure stable order when
    predicted_at ties or is missing.

    Returns:
        A list of dictionaries with keys:
        - symbol (str)
        - advice_action (str) -> one of 'buy' | 'hold' | 'sell'
        - advice_strength (str) -> one of 'high' | 'medium' | 'low'
        - reason (str or None)
        - predicted_at (int)
    """

    try:
        conn = _connect_readonly()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Detect available columns to include optional fields like price
        has_price = False
        try:
            cur.execute("PRAGMA table_info(advises)")
            columns_info = cur.fetchall()
            col_names = {r[1] for r in columns_info}  # type: ignore[index]
            has_price = "price" in col_names
        except Exception:
            # If table doesn't exist yet or PRAGMA fails, fall back gracefully
            has_price = False

        select_cols = [
            "symbol",
            "advice_action",
            "advice_strength",
            "reason",
            "CAST(predicted_at AS INTEGER) AS predicted_at",
        ]
        if has_price:
            select_cols.append("price")

        sql = (
            "SELECT "
            + ",\n              ".join(select_cols)
            + "\n            FROM advises\n            ORDER BY predicted_at DESC, rowid DESC\n            LIMIT 10"
        )

        cur.execute(sql)
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        # Table or columns may not exist yet; return empty list gracefully
        return []
    except Exception:
        # For unanticipated errors the server layer will decide how to respond
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass

    results: List[Dict[str, Any]] = []
    for r in rows:
        item = {
            "symbol": r["symbol"],
            "advice_action": r["advice_action"],
            "advice_strength": r["advice_strength"],
            "reason": r["reason"],
            # Ensure integer for API contract
            "predicted_at": int(r["predicted_at"]) if r["predicted_at"] is not None else None,
        }
        # Optional price field when present in schema
        try:
            if "price" in r.keys():
                item["price"] = r["price"]
        except Exception:
            pass

        # Drop None values to keep payload clean
        results.append({k: v for k, v in item.items() if v is not None})

    return results
