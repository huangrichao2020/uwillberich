#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

from market_data import fetch_index_snapshot, fetch_sector_movers, fetch_tencent_quotes
from opening_window_checklist import classify_state

ROOT = Path(__file__).resolve().parents[1]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    indices = fetch_index_snapshot()
    assert_true(len(indices) >= 3, "expected at least 3 indices")
    assert_true(any(item.get("name") == "上证指数" for item in indices), "missing 上证指数")

    leaders = fetch_sector_movers(limit=3, rising=True)
    laggards = fetch_sector_movers(limit=3, rising=False)
    assert_true(len(leaders) == 3, "expected 3 top sectors")
    assert_true(len(laggards) == 3, "expected 3 bottom sectors")

    quotes = fetch_tencent_quotes(["sz300502", "sh688981", "sh600938"])
    assert_true(len(quotes) == 3, "expected 3 quotes")
    assert_true(all(quote.get("price") is not None for quote in quotes), "quote price missing")

    watchlists = json.loads((ROOT / "assets" / "default_watchlists.json").read_text(encoding="utf-8"))
    assert_true("cross_cycle_anchor12" in watchlists, "missing cross_cycle_anchor12")
    assert_true("cross_cycle_core" in watchlists, "missing cross_cycle_core")
    assert_true(len(watchlists["cross_cycle_anchor12"]) >= 10, "anchor watchlist too small")

    state = classify_state(
        [
            {"group": "tech_repair", "above_prev_close": 3},
            {"group": "policy_beta", "above_prev_close": 1},
            {"group": "defensive_gauge", "above_prev_close": 1},
        ]
    )
    assert_true("true repair" in state.lower(), "opening-window classifier mismatch")

    print("smoke test passed")
    print(f"indices: {len(indices)}")
    print(f"leaders: {len(leaders)}")
    print(f"laggards: {len(laggards)}")
    print(f"quotes: {len(quotes)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"smoke test failed: {exc}", file=sys.stderr)
        raise
