"""
Entry point to run a single-symbol analysis and invoke llm_summary.

- Reads the symbol from design-time resources (hardcoded here as instructed).
- Calls market_data_analysis, dev_data_analysis, chain_data_analysis.
- Builds a summary string that includes function names and stringified results
  (including explicit None when functions return None).
- Invokes final_analysis.llm_summary(symbol, analysis_results=summary).

Notes:
- Only one symbol is handled (no loops or concurrency).
- Minimal error handling with concise logs.
- Python 3.10+, PEP8, and type annotations; all strings/logs are English.
"""

from __future__ import annotations

from typing import Any, Optional


def _safe_imports() -> tuple[
    Optional[Any], Optional[Any], Optional[Any], Optional[Any]
]:
    """Attempt to import required functions with minimal fallback.

    Returns a tuple of callables or None: (market_data_analysis, dev_data_analysis,
    chain_data_analysis, llm_summary).
    """
    market_fn: Optional[Any]
    dev_fn: Optional[Any]
    chain_fn: Optional[Any]
    llm_fn: Optional[Any]

    try:
        from technical_metrics_builder import market_data_analysis  # type: ignore
        market_fn = market_data_analysis
    except Exception as e:
        print(f"Import warning: market_data_analysis unavailable ({e}).")
        market_fn = None

    try:
        from development_process import dev_data_analysis  # type: ignore
        dev_fn = dev_data_analysis
    except Exception as e:
        print(f"Import warning: dev_data_analysis unavailable ({e}).")
        dev_fn = None

    try:
        from onchain_process import chain_data_analysis  # type: ignore
        chain_fn = chain_data_analysis
    except Exception as e:
        print(f"Import warning: chain_data_analysis unavailable ({e}).")
        chain_fn = None

    try:
        from final_analysis import llm_summary  # type: ignore
        llm_fn = llm_summary
    except Exception as e:
        print(f"Import warning: llm_summary unavailable ({e}). Using fallback.")

        def _fallback_llm_summary(symbol: str, analysis_results: str) -> None:
            """Fallback llm_summary that logs invocation without network dependency."""
            print(f"[fallback llm_summary] symbol={symbol}; analysis_results={analysis_results[:200]}")

        llm_fn = _fallback_llm_summary

    return market_fn, dev_fn, chain_fn, llm_fn


def _safe_call(name: str, fn: Optional[Any], symbol: str) -> Optional[Any]:
    """Call the analysis function safely and return its result or None."""
    if fn is None:
        return None
    try:
        return fn(symbol)
    except Exception as e:
        print(f"Call error: {name} failed ({e}).")
        return None


def _stringify(name: str, value: Optional[Any]) -> str:
    """Return a concise string for the summary including explicit None."""
    if value is None:
        return f"{name}: None"
    try:
        return f"{name}: {str(value)}"
    except Exception:
        return f"{name}: <unstringifiable>"


def main() -> None:
    # Single symbol only (no loops or concurrency)
    symbol: str = "BNB"
    print(f"Starting analysis for {symbol}...")

    market_fn, dev_fn, chain_fn, llm_fn = _safe_imports()

    market_res: Optional[Any] = _safe_call("market_data_analysis", market_fn, symbol)
    dev_res: Optional[Any] = _safe_call("dev_data_analysis", dev_fn, symbol)
    chain_res: Optional[Any] = _safe_call("chain_data_analysis", chain_fn, symbol)

    # Build summary string (single line, explicit None allowed)
    summary_parts = [
        _stringify("market_data_analysis", market_res),
        _stringify("dev_data_analysis", dev_res),
        _stringify("chain_data_analysis", chain_res),
    ]
    summary: str = "; ".join(summary_parts)
    print("Summary ready.")

    # Invoke llm_summary at least once (fallback used if import failed)
    try:
        result = llm_fn(symbol=symbol, analysis_results=summary)  # type: ignore[arg-type]
        print(f"llm_summary invoked: {bool(result)}")
    except Exception as e:
        # Minimal error handling: log and exit
        print(f"llm_summary error: {e}")


if __name__ == "__main__":
    main()
