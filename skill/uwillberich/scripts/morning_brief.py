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
DEFAULT_EVENT_WATCHLIST = Path.home() / ".uwillberich" / "news-iterator" / "event_watchlists.json"
EVENT_CATEGORY_ORDER = ["huge_conflict", "huge_future", "huge_name_release"]
CATEGORY_LABELS = {
    "huge_conflict": "巨大冲突",
    "huge_future": "巨大前景",
    "huge_name_release": "巨头名人",
}
GROUP_LABELS = {
    "core10": "核心十股",
    "tech_repair": "科技修复组",
    "defensive_gauge": "防御对照组",
    "policy_beta": "政策敏感组",
    "cross_cycle_anchor12": "跨周期核心池",
    "cross_cycle_ai_hardware": "AI硬件组",
    "cross_cycle_semis": "半导体组",
    "cross_cycle_software_platforms": "软件平台组",
    "cross_cycle_defense_industrial": "军工制造组",
    "war_benefit_oil_coal": "战争受益油煤组",
    "war_headwind_compute_power": "战争受损算力电力组",
    "war_shock_core12": "战争冲击核心12",
    "event_focus_core": "事件核心池",
}
SIGNAL_LABELS = {"high": "高", "medium": "中", "low": "低"}
KEYWORD_LABELS = {
    "war": "战争",
    "oil": "原油",
    "energy": "能源",
    "chips": "芯片",
    "chip": "芯片",
    "robots": "机器人",
    "robot": "机器人",
    "launch": "发布",
    "launches": "发布",
    "announces": "宣布",
    "announce": "宣布",
    "unveils": "亮相",
    "unveil": "亮相",
    "data center": "数据中心",
}


def safe_call(fetcher, default, *args, **kwargs):
    try:
        return fetcher(*args, **kwargs)
    except Exception:
        return default


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


def category_display_name(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def signal_display_name(signal: str) -> str:
    return SIGNAL_LABELS.get(signal, signal)


def group_display_name(group: str) -> str:
    return GROUP_LABELS.get(group, group)


def format_keyword_list(keywords: list[str]) -> str:
    if not keywords:
        return "暂无"
    return ", ".join(KEYWORD_LABELS.get(keyword, keyword) for keyword in keywords)


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
        ("名称", "name"),
        ("代码", "code"),
        ("角色", "role"),
    ]
    if is_event:
        columns.extend(
            [
                ("事件分", "event_score"),
                ("触发数", "trigger_count"),
                ("驱动", "event_driver"),
            ]
        )
    columns.extend(
        [
            ("资金标签", "flow_tag"),
            ("主力净额(亿)", "flow_yi"),
            ("现价", "price"),
            ("涨跌幅", "change_pct"),
            ("最高", "high"),
            ("最低", "low"),
            ("成交额(亿)", "amount_100m"),
        ]
    )
    return format_markdown_table(rows, columns)


def sanitize_display_rows(rows: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for row in rows:
        item = dict(row)
        for key, value in list(item.items()):
            if value is None:
                item[key] = "--"
            elif value == "":
                item[key] = "--"
            elif value == "n/a":
                item[key] = "暂无"
            elif value == "mixed":
                item[key] = "混合"
        cleaned.append(item)
    return cleaned


def render_table_section(title: str, rows: list[dict], columns: list[tuple[str, str]], empty_note: str = "暂无数据") -> None:
    print(f"\n## {title}")
    if not rows:
        print(f"- {empty_note}")
        return
    print(format_markdown_table(sanitize_display_rows(rows), columns))


def render_event_summary(payload: dict) -> None:
    summary = payload.get("summary", [])
    if not summary:
        return
    rows = [
        {
            "category": category_display_name(item["category"]),
            "alert_count": item["alert_count"],
            "total_score": item["total_score"],
            "top_keywords": format_keyword_list(item.get("top_keywords", [])),
        }
        for item in summary
    ]
    print("\n## 事件驱动层总结")
    print(
        format_markdown_table(
            rows,
            [
                ("类别", "category"),
                ("条数", "alert_count"),
                ("总分", "total_score"),
                ("高频关键词", "top_keywords"),
            ],
        )
    )


def render_event_top_alerts(payload: dict) -> None:
    top_alerts = payload.get("top_alerts", {})
    if not top_alerts:
        return
    print("\n## 事件信息源链接")
    for category in EVENT_CATEGORY_ORDER:
        items = top_alerts.get(category, [])
        if not items:
            continue
        print(f"\n### {category_display_name(category)} Top 10 信息源")
        for index, item in enumerate(items, start=1):
            print(f"{index}. [{item['title']}]({item['link']})")
            print(
                f"   - 来源: {item['source']} | 信号: `{signal_display_name(item['signal'])}` | 分值: `{item['score']}`"
            )
            print(f"   - 实体: {', '.join(item.get('entities', [])) or '暂无'}")
            print(f"   - 关键词: {format_keyword_list(item.get('keywords', []))}")


def render_chain_summary(payload: dict) -> None:
    summary = payload.get("chain_summary", [])
    if not summary:
        return
    rows = [
        {
            "theme": item["theme"],
            "score": item["score"],
            "group": item["group"],
            "reasons": " / ".join(item.get("reasons", [])[:3]) or "暂无",
        }
        for item in summary
    ]
    print("\n## 产业链扩散焦点")
    print(
        format_markdown_table(
            rows,
            [
                ("主题", "theme"),
                ("分值", "score"),
                ("映射池", "group"),
                ("理由", "reasons"),
            ],
        )
    )


def format_yi(value: float | int | None) -> str:
    if value is None:
        return "--"
    return f"{float(value):.2f}亿"


def summarize_group_biases(group_flow_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    positives = sorted(
        [row for row in group_flow_rows if float(row.get("net_flow_yi") or 0) > 0],
        key=lambda item: float(item.get("net_flow_yi") or 0),
        reverse=True,
    )
    negatives = sorted(
        [row for row in group_flow_rows if float(row.get("net_flow_yi") or 0) < 0],
        key=lambda item: float(item.get("net_flow_yi") or 0),
    )
    return positives, negatives


def join_sector_names(sectors: list[dict], limit: int = 3) -> str:
    names = [str(item.get("name", "")).strip() for item in sectors[:limit] if str(item.get("name", "")).strip()]
    return "、".join(names) if names else "暂无"


def build_human_nature_snapshot(
    sentiment: dict,
    top_sectors: list[dict],
    bottom_sectors: list[dict],
    market_flow: dict,
    group_flow_rows: list[dict],
) -> dict:
    label = sentiment.get("label", "分化震荡")
    main_net_yi = market_flow.get("main_net_yi")
    positives, negatives = summarize_group_biases(group_flow_rows)
    positive_groups = "、".join(group_display_name(item["group"]) for item in positives[:2]) or "暂无明显强共振"
    negative_groups = "、".join(group_display_name(item["group"]) for item in negatives[:2]) or "暂无明显弱共振"
    strong_sectors = join_sector_names(top_sectors)
    weak_sectors = join_sector_names(bottom_sectors)

    if label == "抱团行情":
        phase = "稀缺抱团期"
        supply_demand = "增量需求只愿意挤向少数高确定性筹码，后排更多是流动性供给。"
        crowd = "多数人不敢全面进攻，只敢追最硬的少数方向；踏空资金追核心，被套资金在弱票里等反弹。"
        stance = "只做最强，不给后排幻想。"
    elif label == "科技修复":
        phase = "试错强化期"
        supply_demand = "需求开始回流成长核心，但新增买盘还没扩散到更广的中军和政策敏感方向。"
        crowd = "多数人刚开始重新相信成长修复，先修的是辨识度最高的核心票。"
        stance = "先盯核心龙头，再等扩散确认。"
    elif label == "修复扩散":
        phase = "共识扩散期"
        supply_demand = "需求正从龙头向中军扩散，优质筹码仍偏稀缺，但后排供给开始增加。"
        crowd = "多数人开始形成共识，愿意为主线支付更高溢价。"
        stance = "可以借多数抬轿，但必须盯龙头是否继续领涨。"
    elif label == "分化偏弱":
        phase = "住相松动期"
        supply_demand = "增量需求不足，解套盘、止损盘和跟风盘同时构成供给，供给压过需求。"
        crowd = "多数人还想抢反弹，但真正的增量资金不愿接弱票。"
        stance = "先减错，不抢弱反弹。"
    else:
        phase = "无统一执念期"
        supply_demand = "需求和供给都在试探，没有统一的群体执念，轮动快于趋势。"
        crowd = "多数人反复切换方向，没有统一信仰，容易追涨杀跌。"
        stance = "做确认，不做预判。"

    if isinstance(main_net_yi, (int, float)) and main_net_yi >= 80:
        supply_demand += " 当前主力净流入较强，说明需求端更主动。"
    elif isinstance(main_net_yi, (int, float)) and main_net_yi <= -80:
        supply_demand += " 当前主力净流出较强，说明供给端抛压更主动。"

    return {
        "phase": phase,
        "supply_demand": supply_demand,
        "crowd": crowd,
        "stance": stance,
        "positive_groups": positive_groups,
        "negative_groups": negative_groups,
        "strong_sectors": strong_sectors,
        "weak_sectors": weak_sectors,
    }


def build_path_tree(sentiment: dict, human_snapshot: dict) -> list[dict]:
    label = sentiment.get("label", "分化震荡")
    strong = human_snapshot["strong_sectors"]
    weak = human_snapshot["weak_sectors"]

    if label == "抱团行情":
        base = f"抱团延续。{strong} 继续吸走有限需求，后排方向仍偏弱。"
        bull = "抱团向修复扩散。核心强势不退，成长中军开始跟上，风险偏好回升。"
        bear = f"抱团松动。核心方向冲高回落，{weak} 继续拖累，市场重新进入兑现。"
    elif label == "科技修复":
        base = f"科技修复延续。强者继续强，资金先围绕 {strong} 做确认。"
        bull = "修复升级为扩散。龙头之外的中军、券商或政策敏感方向开始接力。"
        bear = f"修复失败。核心票冲高回落，{weak} 再次成为拖累，市场回到弱分化。"
    elif label == "修复扩散":
        base = "修复扩散延续。广度、资金和板块共振仍在，主线可继续演绎。"
        bull = "主线强化。新增需求继续涌入，板块内部形成更强梯队。"
        bear = "扩散转分化。龙头滞涨、后排乱动，说明供给开始增加。"
    elif label == "分化偏弱":
        base = f"弱分化延续。{weak} 持续承压，局部强势方向只给脉冲。"
        bull = f"局部修复。{strong} 先止跌，核心强于后排。"
        bear = "分化转杀。增量需求继续缺席，弱势股再度补跌。"
    else:
        base = f"轮动震荡延续。{strong} 与 {weak} 交替轮换，统一方向仍未形成。"
        bull = "轮动收敛为单一主线。最强方向获得资金持续确认。"
        bear = "轮动失灵。强势板块也失去承接，市场退回防守。"

    return [
        {"path": "基准情景", "read": base},
        {"path": "偏强情景", "read": bull},
        {"path": "偏弱情景", "read": bear},
    ]


def build_execution_list(human_snapshot: dict, positives: list[dict], negatives: list[dict]) -> tuple[list[str], list[str]]:
    if positives:
        first_do = f"优先盯 {human_snapshot['positive_groups']} 的领涨票，先看核心，不先铺开后排。"
    else:
        first_do = "暂未看到观察池级别的资金共振，先看板块核心，不做后排扩散预判。"

    do = [
        first_do,
        f"市场立场：{human_snapshot['stance']}",
    ]
    if negatives:
        first_avoid = f"先回避 {human_snapshot['negative_groups']} 里的弱共振方向，别把弱反弹当反转。"
    else:
        first_avoid = "弱势方向仍以板块拖累为主，没有资金确认前不去抢反弹。"

    avoid = [
        first_avoid,
        "没有扩散确认前，不追已经脱离板块支撑的单点脉冲。",
    ]
    if positives:
        do.append(f"强共振方向：{positive_groups_to_text(positives[:2])}")
    if negatives:
        avoid.append(f"弱共振方向：{negative_groups_to_text(negatives[:2])}")
    return do, avoid


def positive_groups_to_text(rows: list[dict]) -> str:
    return "；".join(
        f"{group_display_name(item['group'])}（净流 {format_yi(item.get('net_flow_yi'))}）" for item in rows
    )


def negative_groups_to_text(rows: list[dict]) -> str:
    return "；".join(
        f"{group_display_name(item['group'])}（净流 {format_yi(item.get('net_flow_yi'))}）" for item in rows
    )


def render_summary_sections(
    sentiment: dict,
    indices: list[dict],
    top_sectors: list[dict],
    bottom_sectors: list[dict],
    market_flow: dict,
    group_flow_rows: list[dict],
) -> None:
    human_snapshot = build_human_nature_snapshot(sentiment, top_sectors, bottom_sectors, market_flow, group_flow_rows)
    positives, negatives = summarize_group_biases(group_flow_rows)
    up = sentiment.get("breadth", {}).get("up")
    down = sentiment.get("breadth", {}).get("down")
    breadth_text = f"{up}/{down}" if up is not None and down is not None else "暂无"
    one_liner = (
        f"当前更接近「{sentiment['label']}」，强势主要集中在 {human_snapshot['strong_sectors']}，"
        f"弱势集中在 {human_snapshot['weak_sectors']}；市场广度 {breadth_text}，"
        f"{'主力净流 ' + format_yi(market_flow.get('main_net_yi')) if market_flow.get('main_net_yi') is not None else '主力净流数据暂缺'}。"
    )

    print("# A股盘前日报")
    print("\n## 一句话判断")
    print(f"- {one_liner}")

    print("\n## 人性与供需判断")
    print(f"- 当前阶段：{human_snapshot['phase']}")
    print(f"- 供需判断：{human_snapshot['supply_demand']}")
    print(f"- 群体心理：{human_snapshot['crowd']}")
    print(f"- 我们站位：{human_snapshot['stance']}")

    print("\n## 三种路径")
    for item in build_path_tree(sentiment, human_snapshot):
        print(f"- {item['path']}：{item['read']}")

    do_items, avoid_items = build_execution_list(human_snapshot, positives, negatives)
    print("\n## 今日执行")
    print("### Do")
    for item in do_items:
        print(f"- {item}")
    print("\n### Avoid")
    for item in avoid_items:
        print(f"- {item}")


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

    indices = safe_call(fetch_index_snapshot, [])
    top_sectors = safe_call(fetch_sector_movers, [], limit=5, rising=True)
    bottom_sectors = safe_call(fetch_sector_movers, [], limit=5, rising=False)

    flow_lookup: dict[str, dict] = {}
    group_flow_rows: list[dict] = []
    inflow_items: list[dict] = []
    outflow_items: list[dict] = []
    market_flow = {"label": "未知", "main_net_yi": None, "big_order_inflow_yi": None, "medium_order_inflow_yi": None, "small_order_inflow_yi": None, "as_of": ""}
    if not args.skip_capital_flow:
        market_flow = safe_call(
            fetch_market_flow_snapshot,
            {"label": "未知", "main_net_yi": None, "big_order_inflow_yi": None, "medium_order_inflow_yi": None, "small_order_inflow_yi": None, "as_of": ""},
        )
        inflow_items = safe_call(fetch_top_main_flows, [], "inflow", limit=8)
        outflow_items = safe_call(fetch_top_main_flows, [], "outflow", limit=8)
        flow_lookup = build_flow_lookup(inflow_items, outflow_items)
        group_flow_rows = build_group_flow_scoreboard(watchlist, selected_groups, flow_lookup)

    sentiment = (
        build_sentiment_snapshot(
            group_flow_rows=group_flow_rows,
            indices=indices,
            top_sectors=top_sectors,
            bottom_sectors=bottom_sectors,
            flow_snapshot=market_flow,
        )
        if not args.skip_sentiment
        else {
            "label": "分化震荡",
            "read": "未启用情绪快照。",
            "breadth": {"up": None, "down": None, "ratio": None},
            "components": [],
        }
    )

    render_summary_sections(sentiment, indices, top_sectors, bottom_sectors, market_flow, group_flow_rows)

    render_table_section(
        "指数看板",
        indices,
        [
            ("指数", "name"),
            ("点位", "price"),
            ("涨跌幅", "change_pct"),
            ("上涨家数", "up_count"),
            ("下跌家数", "down_count"),
        ],
    )

    render_table_section(
        "强势板块",
        top_sectors,
        [("板块", "name"), ("涨跌幅", "change_pct"), ("领涨股", "leader")],
    )

    render_table_section(
        "弱势板块",
        bottom_sectors,
        [("板块", "name"), ("涨跌幅", "change_pct"), ("领跌股", "leader")],
    )

    if not args.skip_capital_flow:
        render_table_section(
            "主力资金快照",
            render_flow_snapshot(market_flow) if market_flow.get("main_net_yi") is not None else [],
            [
                ("状态", "label"),
                ("主力净额(亿)", "main_net_yi"),
                ("大单流入(亿)", "big_order_inflow_yi"),
                ("中单流入(亿)", "medium_order_inflow_yi"),
                ("小单流入(亿)", "small_order_inflow_yi"),
                ("截至", "as_of"),
            ],
            empty_note="主力资金数据暂缺",
        )

        render_table_section(
            "主力流入前排",
            inflow_items[:5],
            [
                ("名称", "name"),
                ("代码", "code"),
                ("涨跌幅", "change_pct"),
                ("主力净额(亿)", "main_flow_yi"),
                ("板块", "board"),
            ],
        )

        render_table_section(
            "主力流出前排",
            outflow_items[:5],
            [
                ("名称", "name"),
                ("代码", "code"),
                ("涨跌幅", "change_pct"),
                ("主力净额(亿)", "main_flow_yi"),
                ("板块", "board"),
            ],
        )

        if group_flow_rows:
            display_rows = []
            for row in group_flow_rows:
                display_row = dict(row)
                display_row["group_label"] = group_display_name(row["group"])
                display_rows.append(display_row)
            render_table_section(
                "观察池资金共振",
                display_rows,
                [
                    ("观察池", "group_label"),
                    ("流入命中", "inflow_hits"),
                    ("流出命中", "outflow_hits"),
                    ("净流(亿)", "net_flow_yi"),
                    ("资金倾向", "bias"),
                    ("代表股", "leaders"),
                ],
            )

    if not args.skip_sentiment:
        render_table_section(
            "情绪快照",
            sentiment["components"],
            [
                ("组件", "component"),
                ("分值", "score"),
                ("说明", "detail"),
            ],
        )

    for group in selected_groups:
        items = watchlist[group]
        quotes = safe_call(fetch_tencent_quotes, [], (item["symbol"] for item in items))
        rows = attach_flow_tags(build_rows(items, quotes), flow_lookup)
        print(f"\n## 观察池：{group_display_name(group)}")
        print(render_watchlist_table(sanitize_display_rows(rows), is_event=False))

    if event_groups and selected_event_groups:
        render_event_summary(event_payload)
        render_event_top_alerts(event_payload)
        render_chain_summary(event_payload)
        for group in selected_event_groups:
            items = event_groups.get(group, [])
            if not items:
                continue
            quotes = safe_call(fetch_tencent_quotes, [], (item["symbol"] for item in items))
            rows = attach_flow_tags(build_rows(items, quotes), flow_lookup)
            print(f"\n## 事件观察池：{group_display_name(group)}")
            print(render_watchlist_table(sanitize_display_rows(rows), is_event=True))


if __name__ == "__main__":
    main()
