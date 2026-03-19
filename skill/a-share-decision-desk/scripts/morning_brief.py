#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from market_data import fetch_index_snapshot, fetch_sector_movers, fetch_tencent_quotes, format_markdown_table


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WATCHLIST = ROOT / "assets" / "default_watchlists.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a simple A-share morning brief from default watchlists.")
    parser.add_argument(
        "--watchlist",
        default=str(DEFAULT_WATCHLIST),
        help="Path to a watchlist JSON file. Defaults to the bundled watchlist.",
    )
    parser.add_argument(
        "--groups",
        nargs="+",
        default=["core10"],
        help="Watchlist groups to print, for example: core10 tech_repair defensive_gauge",
    )
    return parser


def load_watchlist(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_rows(items: list[dict], quotes: list[dict]) -> list[dict]:
    quote_map = {quote["code"]: quote for quote in quotes}
    rows: list[dict] = []
    for item in items:
        code = item["symbol"][2:]
        quote = quote_map.get(code)
        if not quote:
            continue
        rows.append(
            {
                "name": quote["name"],
                "code": quote["code"],
                "role": item["role"],
                "price": quote["price"],
                "change_pct": quote["change_pct"],
                "high": quote["high"],
                "low": quote["low"],
                "amount_100m": quote["amount_100m"],
            }
        )
    return rows


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    watchlist = load_watchlist(args.watchlist)
    selected_groups = [group for group in args.groups if group in watchlist]

    print("# A-Share Morning Brief")
    print("\n## Indices")
    print(
        format_markdown_table(
            fetch_index_snapshot(),
            [
                ("Name", "name"),
                ("Price", "price"),
                ("Chg%", "change_pct"),
                ("Up", "up_count"),
                ("Down", "down_count"),
            ],
        )
    )

    print("\n## Top Sectors")
    print(
        format_markdown_table(
            fetch_sector_movers(limit=5, rising=True),
            [("Sector", "name"), ("Chg%", "change_pct"), ("Leader", "leader")],
        )
    )

    print("\n## Bottom Sectors")
    print(
        format_markdown_table(
            fetch_sector_movers(limit=5, rising=False),
            [("Sector", "name"), ("Chg%", "change_pct"), ("Leader", "leader")],
        )
    )

    for group in selected_groups:
        items = watchlist[group]
        quotes = fetch_tencent_quotes(item["symbol"] for item in items)
        rows = build_rows(items, quotes)
        print(f"\n## Watchlist: {group}")
        print(
            format_markdown_table(
                rows,
                [
                    ("Name", "name"),
                    ("Code", "code"),
                    ("Role", "role"),
                    ("Price", "price"),
                    ("Chg%", "change_pct"),
                    ("High", "high"),
                    ("Low", "low"),
                    ("Amount(100m)", "amount_100m"),
                ],
            )
        )


if __name__ == "__main__":
    main()
