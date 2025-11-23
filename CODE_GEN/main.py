"""
Entry point that aggregates analysis outputs and calls llm_summary.

- Imports required analysis functions from local modules.
- Builds a compact summary string: "function_name: <result>" for each.
- Calls final_analysis.llm_summary(symbol, analysis_results=summary).
- Minimal error handling: failures are logged without stopping other symbols.

Python 3.10+, PEP8, all strings/logs in English.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from development_process import dev_data_analysis
from onchain_process import chain_data_analysis
from final_analysis import llm_summary


def _df_summary(df: Optional[pd.DataFrame]) -> str:
    """Return a concise summary for a DataFrame or None.

    Examples:
    - None -> "None"
    - Empty -> "rows=0"
    - Non-empty -> "rows=N cols=a,b,c" (limited to first few columns)
    """
    if df is None:
        return "None"
    if not isinstance(df, pd.DataFrame):
        return str(df)
    rows = len(df)
    cols = list(df.columns) if hasattr(df, "columns") else []
    preview = ",".join(cols[:6]) if cols else ""
    if cols and len(cols) > 6:
        preview += ",..."
    return f"rows={rows}{' cols=' + preview if preview else ''}"


def process_symbol(symbol: str) -> None:
    """Run analyses for a single symbol and invoke llm_summary.

    Errors in individual steps are caught and logged; execution continues.
    """
    summary_parts: list[str] = []

    # market_data_analysis (lazy import to avoid hard dependency failures)
    try:
        from technical_metrics_builder import market_data_analysis as _market_data_analysis
        md = _market_data_analysis(symbol)
        logging.info("md:"+md)
        summary_parts.append(f"market_data_analysis: {_df_summary(md)}")
    except Exception as exc:  # noqa: BLE001
        logging.error("market_data_analysis failed for %s: %s", symbol, exc)
        summary_parts.append("market_data_analysis: None")

    # dev_data_analysis
    try:
        dd = dev_data_analysis(symbol)
        summary_parts.append(f"dev_data_analysis: {_df_summary(dd)}")
    except Exception as exc:  # noqa: BLE001
        logging.error("dev_data_analysis failed for %s: %s", symbol, exc)
        summary_parts.append("dev_data_analysis: None")

    # chain_data_analysis
    try:
        cd = chain_data_analysis(symbol)
        summary_parts.append(f"chain_data_analysis: {_df_summary(cd)}")
    except Exception as exc:  # noqa: BLE001
        logging.error("chain_data_analysis failed for %s: %s", symbol, exc)
        summary_parts.append("chain_data_analysis: None")

    summary = "; ".join(summary_parts)
    logging.info("summary:"+summary)

    # Invoke final LLM-based summary
    try:
        llm_summary(symbol=symbol, analysis_results=summary)
        logging.info(f"llm_summary invoked for {symbol}")
    except Exception as exc:  # noqa: BLE001
        # Do not crash; log and continue to next symbol
        logging.error("llm_summary failed for %s: %s", symbol, exc)


def main() -> None:
    # Use the symbol observed in social_media_analysis.txt during planning (BTC).
    # The final_analysis.llm_summary will read social_media_analysis itself.
    symbols = ["BTC"]

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    for sym in symbols:
        try:
            process_symbol(sym)
        except Exception as exc:  # noqa: BLE001
            logging.error("Processing aborted for %s: %s", sym, exc)
            # Continue to other symbols (if any)
            continue


if __name__ == "__main__":
    main()
