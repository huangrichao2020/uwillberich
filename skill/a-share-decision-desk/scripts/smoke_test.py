#!/usr/bin/env python3

from __future__ import annotations

import sys

from market_data import fetch_index_snapshot, fetch_sector_movers, fetch_tencent_quotes


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
