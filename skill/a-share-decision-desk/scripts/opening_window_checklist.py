#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from market_data import fetch_tencent_quotes, format_markdown_table


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WATCHLIST = ROOT / "assets" / "default_watchlists.json"

TIME_GATES = [
    {
        "time": "09:00",
        "watch": "LPR and policy timing",
        "bullish": "5Y LPR cut or clearly supportive policy tone",
        "bearish": "No support and policy-sensitive names stay weak",
    },
    {
        "time": "09:20-09:25",
        "watch": "Auction leadership",
        "bullish": "Tech repair groups lead the bid",
        "bearish": "Only oil, coal, banks, or telecom lead",
    },
    {
        "time": "09:30-10:00",
        "watch": "Prior-close reclaim and index support",
        "bullish": "Core leaders reclaim prior close and broad indices stabilize",
        "bearish": "Leaders stay under prior close and defensives dominate",
    },
    {
        "time": "10:00-10:30",
        "watch": "Breadth expansion",
        "bullish": "Repair broadens beyond 2-3 names",
        "bearish": "Bounce stays narrow and fades",
    },
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a first-30-minute A-share opening checklist.")
    parser.add_argument(
        "--watchlist",
        default=str(DEFAULT_WATCHLIST),
        help="Path to watchlist JSON. Defaults to the bundled watchlist.",
    )
    parser.add_argument(
        "--groups",
        nargs="+",
        default=["tech_repair", "policy_beta", "defensive_gauge"],
        help="Watchlist groups to score during the opening window.",
    )
    return parser


def load_watchlist(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_signal_lookup(watchlist: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for items in watchlist.values():
        for item in items:
            symbol = item["symbol"]
            strong_signal = item.get("strong_signal")
            weak_signal = item.get("weak_signal")
            if not strong_signal and not weak_signal:
                continue
            lookup[symbol] = {
                "strong_signal": strong_signal or "",
                "weak_signal": weak_signal or "",
            }
    return lookup


def summarize_group(items: list[dict], quotes: list[dict]) -> dict:
    quote_map = {quote["code"]: quote for quote in quotes}
    above = 0
    below = 0
    flat = 0
    changes = []

    for item in items:
        code = item["symbol"][2:]
        quote = quote_map.get(code)
        if not quote or quote.get("change_pct") is None:
            continue
        changes.append(quote["change_pct"])
        if (quote.get("price") or 0) > (quote.get("prev_close") or 0):
            above += 1
        elif (quote.get("price") or 0) < (quote.get("prev_close") or 0):
            below += 1
        else:
            flat += 1

    avg_change = round(sum(changes) / len(changes), 2) if changes else None
    return {
        "group": "",
        "count": len(items),
        "above_prev_close": above,
        "below_prev_close": below,
        "flat": flat,
        "avg_change_pct": avg_change,
    }


def classify_state(scoreboard: list[dict]) -> str:
    by_name = {row["group"]: row for row in scoreboard}
    tech = by_name.get("tech_repair", {})
    policy = by_name.get("policy_beta", {})
    defensive = by_name.get("defensive_gauge", {})

    tech_above = tech.get("above_prev_close", 0)
    defensive_above = defensive.get("above_prev_close", 0)
    policy_above = policy.get("above_prev_close", 0)

    if tech_above >= 3 and defensive_above <= 2:
        return "State: likely true repair"
    if policy_above >= 2 and tech_above >= 2:
        return "State: likely policy-backed repair"
    if defensive_above >= 3 and tech_above <= 2:
        return "State: likely defensive concentration"
    return "State: mixed or unresolved opening tape"


def build_detail_rows(items: list[dict], quotes: list[dict], signal_lookup: dict[str, dict]) -> list[dict]:
    quote_map = {quote["code"]: quote for quote in quotes}
    rows = []
    for item in items:
        code = item["symbol"][2:]
        quote = quote_map.get(code)
        if not quote:
            continue
        fallback = signal_lookup.get(item["symbol"], {})
        rows.append(
            {
                "name": quote["name"],
                "code": quote["code"],
                "role": item["role"],
                "price": quote["price"],
                "chg%": quote["change_pct"],
                "strong_signal": item.get("strong_signal") or fallback.get("strong_signal", ""),
                "weak_signal": item.get("weak_signal") or fallback.get("weak_signal", ""),
            }
        )
    return rows


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    watchlist = load_watchlist(args.watchlist)
    signal_lookup = build_signal_lookup(watchlist)
    selected_groups = [group for group in args.groups if group in watchlist]

    all_symbols = []
    for group in selected_groups:
        all_symbols.extend(item["symbol"] for item in watchlist[group])
    quotes = fetch_tencent_quotes(all_symbols)

    print("# Opening Window Checklist")
    print()
    print("## Time Gates")
    print(
        format_markdown_table(
            TIME_GATES,
            [
                ("Time", "time"),
                ("Watch", "watch"),
                ("Bullish Read", "bullish"),
                ("Bearish Read", "bearish"),
            ],
        )
    )

    scoreboard = []
    for group in selected_groups:
        summary = summarize_group(watchlist[group], quotes)
        summary["group"] = group
        scoreboard.append(summary)

    print("\n## Group Scoreboard")
    print(
        format_markdown_table(
            scoreboard,
            [
                ("Group", "group"),
                ("Count", "count"),
                ("Above Prev Close", "above_prev_close"),
                ("Below Prev Close", "below_prev_close"),
                ("Flat", "flat"),
                ("Avg Chg%", "avg_change_pct"),
            ],
        )
    )

    print("\n## Quick Read")
    print(classify_state(scoreboard))

    for group in selected_groups:
        rows = build_detail_rows(watchlist[group], quotes, signal_lookup)
        print(f"\n## Watchlist: {group}")
        print(
            format_markdown_table(
                rows,
                [
                    ("Name", "name"),
                    ("Code", "code"),
                    ("Role", "role"),
                    ("Price", "price"),
                    ("Chg%", "chg%"),
                    ("Strong Signal", "strong_signal"),
                    ("Weak Signal", "weak_signal"),
                ],
            )
        )


if __name__ == "__main__":
    main()
