"""
Main entrypoint to aggregate analysis and invoke final LLM summary.

Behavior:
- Reads `resources/social_media_analysis.txt` to ensure availability.
- Enumerates symbols from `resources/*.txt` (excluding the social file).
- For each symbol, calls available analysis functions from `function_list` and
  constructs a `summary` string of "function: result" pairs (including None).
- Invokes `final_analysis.llm_summary(symbol, analysis_results=summary)` with
  light error handling so one failure does not stop other symbols.

Requirements:
- Python 3.10+
- Environment variable `OPENAI_API_KEY` for LLM access.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

from tools.development_process import dev_data_analysis
from tools.onchain_process import chain_data_analysis
from tools.technical_metrics_builder import market_data_analysis


def _load_social_media_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        print(f"[warn] Failed to read social media analysis: {exc}")
        return None


def _discover_symbols(resources_dir: Path) -> List[str]:
    symbols: List[str] = []
    try:
        for p in resources_dir.glob("*.txt"):
            # Skip social media file by exact name
            if p.name.lower() == "social_media_analysis.txt":
                continue
            symbols.append(p.stem)
    except Exception as exc:
        print(f"[warn] Failed to enumerate resources: {exc}")
    return symbols


def _safe_call(func: Optional[Callable[[str], object]], symbol: str) -> Optional[object]:
    if func is None:
        return None
    try:
        return func(symbol)  # type: ignore[misc]
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[warn] {getattr(func, '__name__', 'analysis')} failed for {symbol}: {exc}")
        return None


def _build_summary(symbol: str, funcs: Iterable[Tuple[str, Optional[Callable[[str], object]]]]) -> str:
    parts: List[str] = []
    for name, fn in funcs:
        res = _safe_call(fn, symbol)
        parts.append(f"{name}: {res}")
    return "; ".join(parts)


def main() -> None:
    resources_dir = Path("resources")
    social_path = resources_dir / "social_media_analysis.txt"

    # Ensure we can read social media analysis (requirement visibility).
    social_text = _load_social_media_text(social_path)
    if social_text is not None:
        print(f"[info] Social media analysis loaded: {len(social_text)} chars")

    # Discover symbols from resource files
    symbols = _discover_symbols(resources_dir)
    if not symbols:
        print("[warn] No symbol files found under resources/")



    funcs: Tuple[Tuple[str, Optional[Callable[[str], object]]], ...] = (
        ("market_data_analysis", market_data_analysis),
        ("dev_data_analysis", dev_data_analysis),
        ("chain_data_analysis", chain_data_analysis),
    )

    # Check API key presence to give early visibility (llm_summary uses it)
    if not os.getenv("OPENAI_API_KEY"):
        print("[warn] OPENAI_API_KEY not set; llm invocation may fail.")

    for symbol in symbols:
        print(f"[info] Processing {symbol}...")
        try:
            summary = _build_summary(symbol, funcs)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[warn] Failed to build summary for {symbol}: {exc}")
            summary = ""

        # Import and invoke llm_summary per symbol with isolation
        try:
            from final_analysis import llm_summary  # imported late for resilience
        except Exception as exc:  # pragma: no cover
            print(f"[error] Cannot import llm_summary: {exc}")
            continue

        try:
            result = llm_summary(symbol=symbol, analysis_results=summary)
            print(f"[info] llm_summary called for {symbol}: {bool(result)}")
        except Exception as exc:
            # Continue with the next symbol if this one fails
            print(f"[warn] llm_summary failed for {symbol}: {exc}")
            continue


if __name__ == "__main__":
    main()

