#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from capital_flow import (
    attach_flow_tags,
    build_flow_lookup,
    build_group_flow_scoreboard,
    fetch_market_flow_snapshot,
    fetch_top_main_flows,
    render_flow_snapshot,
)
from industry_chain import enrich_event_payload_with_chain_focus
from market_data import fetch_index_snapshot, fetch_sector_movers, fetch_tencent_quotes, format_markdown_table
from market_sentiment import build_sentiment_snapshot


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WATCHLIST = ROOT / "assets" / "default_watchlists.json"
DEFAULT_EVENT_WATCHLIST = Path.home() / ".a-share-decision-desk" / "news-iterator" / "event_watchlists.json"


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
    parser.add_argument(
        "--event-watchlist",
        default=str(DEFAULT_EVENT_WATCHLIST),
        help="Path to dynamic event-driven watchlists JSON.",
    )
    parser.add_argument(
        "--skip-event-pools",
        action="store_true",
        help="Do not append event-driven watchlists from the news iterator state.",
    )
    parser.add_argument(
        "--skip-capital-flow",
        action="store_true",
        help="Do not append main-force capital-flow sections.",
    )
    parser.add_argument(
        "--skip-sentiment",
        action="store_true",
        help="Do not append the market-sentiment snapshot.",
    )
    parser.add_argument(
        "--skip-industry-chain",
        action="store_true",
        help="Do not enrich event pools with chain-focus groups.",
    )
    return parser


def load_watchlist(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_event_payload(path: str) -> dict:
    event_path = Path(path)
    if not event_path.exists():
        return {}
    return json.loads(event_path.read_text(encoding="utf-8"))


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
                "event_score": item.get("event_score"),
                "trigger_count": item.get("trigger_count"),
                "event_driver": item.get("event_driver", ""),
            }
        )
    return rows


def render_watchlist_table(rows: list[dict], is_event: bool) -> str:
    columns = [
        ("Name", "name"),
        ("Code", "code"),
        ("Role", "role"),
    ]
    if is_event:
        columns.extend(
            [
                ("EventScore", "event_score"),
                ("Triggers", "trigger_count"),
                ("Driver", "event_driver"),
            ]
        )
    columns.extend(
        [
            ("FlowTag", "flow_tag"),
            ("Flow(亿)", "flow_yi"),
            ("Price", "price"),
            ("Chg%", "change_pct"),
            ("High", "high"),
            ("Low", "low"),
            ("Amount(100m)", "amount_100m"),
        ]
    )
    return format_markdown_table(rows, columns)


def render_event_summary(payload: dict) -> None:
    summary = payload.get("summary", [])
    if not summary:
        return
    rows = [
        {
            "category": item["category"],
            "alert_count": item["alert_count"],
            "total_score": item["total_score"],
            "top_keywords": ", ".join(item.get("top_keywords", [])) or "n/a",
        }
        for item in summary
    ]
    print("\n## Event Summary")
    print(
        format_markdown_table(
            rows,
            [
                ("Category", "category"),
                ("Alerts", "alert_count"),
                ("Total Score", "total_score"),
                ("Top Keywords", "top_keywords"),
            ],
        )
    )


def render_chain_summary(payload: dict) -> None:
    summary = payload.get("chain_summary", [])
    if not summary:
        return
    rows = [
        {
            "theme": item["theme"],
            "score": item["score"],
            "group": item["group"],
            "reasons": " / ".join(item.get("reasons", [])[:3]) or "n/a",
        }
        for item in summary
    ]
    print("\n## Industry Chain Focus")
    print(
        format_markdown_table(
            rows,
            [
                ("Theme", "theme"),
                ("Score", "score"),
                ("Group", "group"),
                ("Reasons", "reasons"),
            ],
        )
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    watchlist = load_watchlist(args.watchlist)
    event_payload = {} if args.skip_event_pools else load_event_payload(args.event_watchlist)
    if event_payload and not args.skip_industry_chain:
        event_payload = enrich_event_payload_with_chain_focus(
            event_payload,
            watchlist,
            selected_groups=args.groups,
        )
    event_groups = event_payload.get("groups", {})
    selected_groups = [group for group in args.groups if group in watchlist]
    selected_event_groups = [group for group in args.groups if group in event_groups]
    if not selected_event_groups and event_groups:
        selected_event_groups = event_payload.get("default_report_groups", [])
    selected_event_groups = list(dict.fromkeys(selected_event_groups))

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

    flow_lookup: dict[str, dict] = {}
    group_flow_rows: list[dict] = []
    if not args.skip_capital_flow:
        market_flow = fetch_market_flow_snapshot()
        inflow_items = fetch_top_main_flows("inflow", limit=8)
        outflow_items = fetch_top_main_flows("outflow", limit=8)
        flow_lookup = build_flow_lookup(inflow_items, outflow_items)
        group_flow_rows = build_group_flow_scoreboard(watchlist, selected_groups, flow_lookup)

        print("\n## Capital Flow Snapshot")
        print(
            format_markdown_table(
                render_flow_snapshot(market_flow),
                [
                    ("State", "label"),
                    ("MainNet(亿)", "main_net_yi"),
                    ("BigInflow(亿)", "big_order_inflow_yi"),
                    ("MediumInflow(亿)", "medium_order_inflow_yi"),
                    ("SmallInflow(亿)", "small_order_inflow_yi"),
                    ("As Of", "as_of"),
                ],
            )
        )

        print("\n## Top Main-Force Inflow")
        print(
            format_markdown_table(
                inflow_items[:5],
                [
                    ("Name", "name"),
                    ("Code", "code"),
                    ("Chg%", "change_pct"),
                    ("MainFlow(亿)", "main_flow_yi"),
                    ("Board", "board"),
                ],
            )
        )

        print("\n## Top Main-Force Outflow")
        print(
            format_markdown_table(
                outflow_items[:5],
                [
                    ("Name", "name"),
                    ("Code", "code"),
                    ("Chg%", "change_pct"),
                    ("MainFlow(亿)", "main_flow_yi"),
                    ("Board", "board"),
                ],
            )
        )

        if group_flow_rows:
            print("\n## Watchlist Flow Resonance")
            print(
                format_markdown_table(
                    group_flow_rows,
                    [
                        ("Group", "group"),
                        ("InflowHits", "inflow_hits"),
                        ("OutflowHits", "outflow_hits"),
                        ("NetFlow(亿)", "net_flow_yi"),
                        ("Bias", "bias"),
                        ("Leaders", "leaders"),
                    ],
                )
            )

    if not args.skip_sentiment:
        sentiment = build_sentiment_snapshot(group_flow_rows=group_flow_rows)
        print("\n## Sentiment Snapshot")
        print(f"- state: {sentiment['label']}")
        print(f"- read: {sentiment['read']}")
        print(
            format_markdown_table(
                sentiment["components"],
                [
                    ("Component", "component"),
                    ("Score", "score"),
                    ("Detail", "detail"),
                ],
            )
        )

    for group in selected_groups:
        items = watchlist[group]
        quotes = fetch_tencent_quotes(item["symbol"] for item in items)
        rows = attach_flow_tags(build_rows(items, quotes), flow_lookup)
        print(f"\n## Watchlist: {group}")
        print(render_watchlist_table(rows, is_event=False))

    if event_groups and selected_event_groups:
        render_event_summary(event_payload)
        render_chain_summary(event_payload)
        for group in selected_event_groups:
            items = event_groups.get(group, [])
            if not items:
                continue
            quotes = fetch_tencent_quotes(item["symbol"] for item in items)
            rows = attach_flow_tags(build_rows(items, quotes), flow_lookup)
            print(f"\n## Event Watchlist: {group}")
            print(render_watchlist_table(rows, is_event=True))


if __name__ == "__main__":
    main()
