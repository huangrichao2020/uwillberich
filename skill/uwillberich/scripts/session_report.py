#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
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
from morning_brief import (
    DEFAULT_EVENT_WATCHLIST,
    DEFAULT_WATCHLIST,
    build_execution_list,
    build_human_nature_snapshot,
    build_path_tree,
    build_rows,
    category_display_name,
    format_keyword_list,
    format_yi,
    group_display_name,
    load_event_payload,
    load_watchlist,
    render_watchlist_table,
    safe_call,
    summarize_group_biases,
)
from opening_window_checklist import summarize_group


DEFAULT_GROUPS = ["core10", "tech_repair", "defensive_gauge", "policy_beta"]
DEFAULT_MARKET_FLOW = {
    "label": "未知",
    "main_net_yi": None,
    "big_order_inflow_yi": None,
    "medium_order_inflow_yi": None,
    "small_order_inflow_yi": None,
    "as_of": "",
}

SESSION_META = {
    "pre_market": {
        "title": "A股盘前日报",
        "summary_title": "盘前结论",
        "paths_title": "今日三路径",
        "gates_title": "今日时间门",
        "execution_title": "今日执行",
        "regime_posture": "开盘前先看谁有资格成为主线，不在弱修复里抢后排。",
        "gates": [
            {
                "time": "09:00",
                "watch": "政策门",
                "bullish": "LPR 或政策口径偏暖，政策敏感组先回到昨收之上",
                "bearish": "政策层没有增量，券商地产继续弱势",
            },
            {
                "time": "09:20-09:25",
                "watch": "集合竞价领导权",
                "bullish": "科技修复组与核心十股抢到竞价前排",
                "bearish": "只有油煤红利和防御权重抢量",
            },
            {
                "time": "09:30-10:00",
                "watch": "昨收与昨高回收",
                "bullish": "核心龙头站回昨收并带动中军跟涨",
                "bearish": "龙头始终压在昨收下方，反弹只剩脉冲",
            },
            {
                "time": "14:00-14:30",
                "watch": "午后扩散门",
                "bullish": "修复从龙头扩到中军和政策敏感方向",
                "bearish": "午后只剩防御和孤立强票，说明不是全天主线",
            },
        ],
    },
    "mid_market": {
        "title": "A股午盘日报",
        "summary_title": "午盘结论",
        "paths_title": "午后三路径",
        "gates_title": "午后时间门",
        "execution_title": "午后执行",
        "regime_posture": "午盘之后只看上午主线能不能扩散，不把上午没走出来的弱分支当补涨。",
        "gates": [
            {
                "time": "13:00-13:30",
                "watch": "午后回流门",
                "bullish": "上午强势方向回踩有承接，龙头率先再冲",
                "bearish": "上午强票一开盘就被兑现，说明承接不足",
            },
            {
                "time": "13:30-14:00",
                "watch": "板块扩散门",
                "bullish": "强势从龙头扩到中军和同链二线",
                "bearish": "只剩孤立强票，板块内部并未扩散",
            },
            {
                "time": "14:00-14:30",
                "watch": "风险偏好门",
                "bullish": "券商、平台、中军开始共振，说明风险偏好回升",
                "bearish": "防御权重重新占优，说明午后更像回落而不是加速",
            },
            {
                "time": "14:30-14:50",
                "watch": "尾盘定性门",
                "bullish": "最强方向尾盘继续被资金锁住",
                "bearish": "尾盘龙头跳水，说明全天只是情绪脉冲",
            },
        ],
    },
    "after_market": {
        "title": "A股盘后日报",
        "summary_title": "收盘结论",
        "paths_title": "明日三路径",
        "gates_title": "明日开盘时间门",
        "execution_title": "明日执行",
        "regime_posture": "盘后先给市场定性，再推明日开盘计划，重点不是复述涨跌，而是谁有资格带队。",
        "gates": [
            {
                "time": "09:00",
                "watch": "隔夜消息门",
                "bullish": "隔夜消息继续抬升主线关注度，政策或事件没有反向打脸",
                "bearish": "隔夜出现明显利空或主线催化失效",
            },
            {
                "time": "09:20-09:25",
                "watch": "次日竞价门",
                "bullish": "收盘最强方向次日竞价继续拿到领导权",
                "bearish": "尾盘最强股次日低于预期，说明强度无法延续",
            },
            {
                "time": "09:30-10:00",
                "watch": "承接与兑现门",
                "bullish": "龙头与中军同步承接，说明主线可延续",
                "bearish": "高位先兑现，中军没有接力，说明进入分歧或分配期",
            },
            {
                "time": "14:00-14:30",
                "watch": "次日扩散门",
                "bullish": "次日午后能从龙头扩到同链和风险偏好资产",
                "bearish": "次日午后强度仍只停留在孤立龙头",
            },
        ],
    },
}

DEFENSIVE_KEYWORDS = ("油", "煤", "银行", "红利", "电信", "公用事业", "运营商")
GROWTH_KEYWORDS = ("算力", "光模块", "芯片", "半导体", "AI", "机器人", "CPO")


@dataclass
class DeskContext:
    report_date: str
    report_date_label: str
    market_date_label: str
    generated_at: str
    watchlist: dict
    event_payload: dict
    event_groups: dict
    selected_groups: list[str]
    selected_event_groups: list[str]
    indices: list[dict]
    top_sectors: list[dict]
    bottom_sectors: list[dict]
    market_flow: dict
    inflow_items: list[dict]
    outflow_items: list[dict]
    flow_lookup: dict[str, dict]
    group_flow_rows: list[dict]
    sentiment: dict
    quotes: list[dict]
    group_scoreboard: list[dict]
    event_scoreboard: list[dict]
    chain_summary: list[dict]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate methodology-first A-share session reports.")
    parser.add_argument(
        "--session",
        choices=["all", "pre_market", "mid_market", "after_market"],
        default="all",
        help="Which session report to generate.",
    )
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST), help="Base watchlist JSON path.")
    parser.add_argument(
        "--event-watchlist",
        default=str(DEFAULT_EVENT_WATCHLIST),
        help="Path to event_watchlists.json generated by news_iterator.",
    )
    parser.add_argument(
        "--groups",
        nargs="+",
        default=DEFAULT_GROUPS,
        help="Base watchlist groups to include in the methodology report.",
    )
    parser.add_argument("--date", help="Optional report date in YYYYMMDD or YYYY-MM-DD.")
    parser.add_argument("--publish-dir", help="Optional output directory for generated markdown files.")
    parser.add_argument("--rebuild-static", metavar="API_URL",
                        help="After publishing, rebuild the static site from this reports API URL (e.g. http://127.0.0.1:3000).")
    parser.add_argument("--skip-event-pools", action="store_true", help="Skip event-driven watchlists.")
    parser.add_argument("--skip-industry-chain", action="store_true", help="Skip industry-chain enrichment.")
    parser.add_argument("--limit", type=int, default=6, help="Rows per leader table.")
    return parser


def normalize_date_digits(value: str | None) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:8]


def display_date(digits: str) -> str:
    if len(digits) != 8:
        return digits
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def detect_report_date(explicit_date: str | None, market_flow: dict) -> str:
    if explicit_date:
        digits = normalize_date_digits(explicit_date)
        if len(digits) == 8:
            return digits
    as_of_digits = normalize_date_digits(market_flow.get("as_of"))
    if len(as_of_digits) == 8:
        return as_of_digits
    return datetime.now().strftime("%Y%m%d")


def net_flow_lookup(rows: list[dict]) -> dict[str, dict]:
    return {row["group"]: row for row in rows}


def scoreboard_lookup(rows: list[dict]) -> dict[str, dict]:
    return {row["group"]: row for row in rows}


def sector_names(rows: list[dict], limit: int = 3) -> str:
    names = [str(item.get("name", "")).strip() for item in rows[:limit] if str(item.get("name", "")).strip()]
    return "、".join(names) if names else "暂无"


def match_sector_theme(rows: list[dict], keywords: tuple[str, ...]) -> bool:
    for item in rows:
        name = str(item.get("name", "")).strip()
        if any(keyword in name for keyword in keywords):
            return True
    return False


def classify_regime(context: DeskContext) -> tuple[str, str]:
    flows = net_flow_lookup(context.group_flow_rows)
    scoreboards = scoreboard_lookup(context.group_scoreboard)

    tech_flow = float((flows.get("tech_repair") or {}).get("net_flow_yi") or 0)
    defensive_flow = float((flows.get("defensive_gauge") or {}).get("net_flow_yi") or 0)
    policy_flow = float((flows.get("policy_beta") or {}).get("net_flow_yi") or 0)
    tech_above = int((scoreboards.get("tech_repair") or {}).get("above_prev_close") or 0)
    defensive_above = int((scoreboards.get("defensive_gauge") or {}).get("above_prev_close") or 0)
    policy_above = int((scoreboards.get("policy_beta") or {}).get("above_prev_close") or 0)
    breadth_ratio = context.sentiment.get("breadth", {}).get("ratio")

    if (
        context.sentiment.get("label") in {"修复扩散", "科技修复"}
        and tech_flow > 0
        and tech_above >= 2
        and policy_above >= 1
        and (breadth_ratio is None or breadth_ratio >= 0.32)
    ):
        return (
            "主线市场",
            "成长与政策敏感方向同时有资金和价格确认，说明市场不只是孤立强票，而是在尝试形成可交易主线。",
        )

    if (
        context.sentiment.get("label") == "抱团行情"
        or (defensive_above >= 3 and defensive_flow >= tech_flow)
        or (match_sector_theme(context.top_sectors, DEFENSIVE_KEYWORDS) and (breadth_ratio or 0) < 0.3)
    ):
        return (
            "区间防御市场",
            "市场没有给出统一进攻主线，强度更集中在防御或避险方向，交易上要把持仓周期和追价容忍度都收紧。",
        )

    return (
        "独立强票市场",
        "当前更像少数高辨识度方向在吸走有限流动性，能做的是盯住最强龙头和同链确认，而不是把局部强势误判成全面修复。",
    )


def build_external_layer(context: DeskContext, regime_label: str) -> list[str]:
    summary = context.event_payload.get("summary", [])
    if summary:
        ordered = sorted(
            summary,
            key=lambda item: (int(item.get("total_score", 0)), int(item.get("alert_count", 0))),
            reverse=True,
        )
        top_item = ordered[0]
        return [
            f"事件层最高关注来自「{category_display_name(top_item['category'])}」，关键词集中在 {format_keyword_list(top_item.get('top_keywords', []))}。",
            "先判断它能不能从信息圈扩散到板块和大资金，而不是只看消息本身够不够热。",
        ]

    if match_sector_theme(context.top_sectors, DEFENSIVE_KEYWORDS):
        return [
            "外部冲击层没有完全退场，资金仍愿意把油煤红利和低波防御当环境锚。",
            "这意味着进攻方向必须先靠自身强度拿证据，不能默认市场会自然扩散。",
        ]

    if match_sector_theme(context.top_sectors, GROWTH_KEYWORDS):
        return [
            "外部冲击层暂时没有压过内部结构，盘面主要由成长链自身强弱和资金选择主导。",
            "重点不是消息有没有，而是资金愿不愿意把消息翻译成板块级价格行为。",
        ]

    return [
        f"外部冲击层目前没有形成能压过盘面结构的新主导变量，当前更要按「{regime_label}」去看价格行为。",
        "没有外部统一催化时，最容易出现的是局部强、广度弱的结构。",
    ]


def build_policy_layer(context: DeskContext) -> list[str]:
    flows = net_flow_lookup(context.group_flow_rows)
    scoreboards = scoreboard_lookup(context.group_scoreboard)
    policy_flow = float((flows.get("policy_beta") or {}).get("net_flow_yi") or 0)
    policy_row = scoreboards.get("policy_beta") or {}
    above_prev_close = int(policy_row.get("above_prev_close") or 0)
    below_prev_close = int(policy_row.get("below_prev_close") or 0)
    main_net = context.market_flow.get("main_net_yi")

    if policy_flow > 0 and above_prev_close >= 2:
        return [
            "政策/流动性层给到了可交易的正反馈，政策敏感组不只是在口头上受益，而是已经体现在价格和资金里。",
            "这类环境下更要盯券商、地产链和消费地产链能不能跟上，而不是只看科技单点冲高。",
        ]

    if isinstance(main_net, (int, float)) and main_net <= -80 and below_prev_close >= 3:
        return [
            "政策/流动性层暂时没有提供承接，主力净流出仍大，政策敏感组也没有站出来。",
            "这种情况下先把政策链当验证器，不要先假设政策一定会救回风险偏好。",
        ]

    return [
        "政策/流动性层目前更偏中性，关键不是有没有口号，而是政策敏感组是否愿意先站回昨收并拿到量能。",
        "在信号没有变成价格之前，政策信息只能算辅助条件，不能替代盘面证据。",
    ]


def build_internal_layer(context: DeskContext, regime_label: str) -> list[str]:
    breadth = context.sentiment.get("breadth", {})
    up = breadth.get("up")
    down = breadth.get("down")
    top_names = sector_names(context.top_sectors)
    bottom_names = sector_names(context.bottom_sectors)
    return [
        f"内部结构上，强势集中在 {top_names}，弱势集中在 {bottom_names}；广度为 {up}/{down}。",
        f"这更接近「{regime_label}」的结构特征，真正要看的不是指数颜色，而是最强方向能不能从龙头扩到中军和风险偏好代理。",
    ]


def build_support_tables(context: DeskContext, limit: int) -> list[str]:
    parts: list[str] = []

    parts.append("## 指数看板")
    parts.append(
        format_markdown_table(
            context.indices,
            [
                ("指数", "name"),
                ("点位", "price"),
                ("涨跌幅", "change_pct"),
                ("上涨家数", "up_count"),
                ("下跌家数", "down_count"),
            ],
        )
    )

    parts.append("\n## 强势板块")
    parts.append(
        format_markdown_table(
            context.top_sectors,
            [
                ("板块", "name"),
                ("涨跌幅", "change_pct"),
                ("领涨股", "leader"),
            ],
        )
    )

    parts.append("\n## 弱势板块")
    parts.append(
        format_markdown_table(
            context.bottom_sectors,
            [
                ("板块", "name"),
                ("涨跌幅", "change_pct"),
                ("领跌股", "leader"),
            ],
        )
    )

    parts.append("\n## 主力资金快照")
    parts.append(
        format_markdown_table(
            render_flow_snapshot(context.market_flow),
            [
                ("状态", "label"),
                ("主力净额(亿)", "main_net_yi"),
                ("大单流入(亿)", "big_order_inflow_yi"),
                ("中单流入(亿)", "medium_order_inflow_yi"),
                ("小单流入(亿)", "small_order_inflow_yi"),
                ("截至", "as_of"),
            ],
        )
    )

    parts.append("\n## 主力流入前排")
    parts.append(
        format_markdown_table(
            context.inflow_items[:limit],
            [
                ("名称", "name"),
                ("代码", "code"),
                ("涨跌幅", "change_pct"),
                ("主力净额(亿)", "main_flow_yi"),
                ("板块", "board"),
            ],
        )
    )

    parts.append("\n## 主力流出前排")
    parts.append(
        format_markdown_table(
            context.outflow_items[:limit],
            [
                ("名称", "name"),
                ("代码", "code"),
                ("涨跌幅", "change_pct"),
                ("主力净额(亿)", "main_flow_yi"),
                ("板块", "board"),
            ],
        )
    )

    parts.append("\n## 观察池资金共振")
    group_flow_display_rows = []
    for row in context.group_flow_rows:
        group_flow_display_rows.append(
            {
                **row,
                "group_label": group_display_name(row["group"]),
            }
        )
    parts.append(
        format_markdown_table(
            group_flow_display_rows,
            [
                ("观察池", "group_label"),
                ("流入命中", "inflow_hits"),
                ("流出命中", "outflow_hits"),
                ("净流(亿)", "net_flow_yi"),
                ("资金倾向", "bias"),
                ("代表股", "leaders"),
            ],
        )
    )

    return parts


def build_watchlist_sections(context: DeskContext) -> list[str]:
    parts: list[str] = []
    for group in context.selected_groups:
        rows = attach_flow_tags(build_rows(context.watchlist[group], context.quotes), context.flow_lookup)
        parts.append(f"\n## 观察池：{group_display_name(group)}")
        parts.append(render_watchlist_table(rows, is_event=False))
    return parts


def build_event_sections(context: DeskContext) -> list[str]:
    parts: list[str] = []
    event_group_labels = {item["group"]: item["theme"] for item in context.chain_summary}
    summary = context.event_payload.get("summary", [])
    if summary:
        rows = [
            {
                "category": category_display_name(item["category"]),
                "alert_count": item["alert_count"],
                "total_score": item["total_score"],
                "top_keywords": format_keyword_list(item.get("top_keywords", [])),
            }
            for item in summary
        ]
        parts.append("\n## 事件驱动层")
        parts.append(
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

    if context.chain_summary:
        parts.append("\n## 产业链扩散焦点")
        parts.append(
            format_markdown_table(
                [
                    {
                        "theme": item["theme"],
                        "score": item["score"],
                        "group": item["group"],
                        "reasons": " / ".join(item.get("reasons", [])[:3]) or "暂无",
                    }
                    for item in context.chain_summary
                ],
                [
                    ("主题", "theme"),
                    ("分值", "score"),
                    ("映射池", "group"),
                    ("理由", "reasons"),
                ],
            )
        )

    for group in context.selected_event_groups:
        rows = attach_flow_tags(build_rows(context.event_groups[group], context.quotes), context.flow_lookup)
        group_label = event_group_labels.get(group, group_display_name(group))
        parts.append(f"\n## 事件观察池：{group_label}")
        parts.append(render_watchlist_table(rows, is_event=True))

    return parts


def build_execution_lines(context: DeskContext, session_key: str, regime_label: str) -> tuple[list[str], list[str]]:
    human_snapshot = build_human_nature_snapshot(
        context.sentiment,
        context.top_sectors,
        context.bottom_sectors,
        context.market_flow,
        context.group_flow_rows,
    )
    positives, negatives = summarize_group_biases(context.group_flow_rows)
    do_items, avoid_items = build_execution_list(human_snapshot, positives, negatives)
    do_items = [SESSION_META[session_key]["regime_posture"], *do_items]
    avoid_items = [
        f"如果盘面仍停留在「{regime_label}」，就不要把孤立强势误判成全面修复。",
        *avoid_items,
    ]
    return do_items, avoid_items


def build_meta_lines(context: DeskContext, session_key: str, regime_label: str, regime_read: str) -> list[str]:
    human_snapshot = build_human_nature_snapshot(
        context.sentiment,
        context.top_sectors,
        context.bottom_sectors,
        context.market_flow,
        context.group_flow_rows,
    )
    strong_names = human_snapshot["strong_sectors"]
    weak_names = human_snapshot["weak_sectors"]

    if session_key == "pre_market":
        summary = (
            f"盘前按方法论看，当前更接近「{regime_label}」，先把 {strong_names} 当作资金可能继续确认的方向，"
            f"再把 {weak_names} 当作仍在释放供给的区域。"
        )
    elif session_key == "mid_market":
        summary = (
            f"午盘复核后，上午资金主要围绕 {strong_names} 做确认，{weak_names} 仍是供给集中区，"
            f"盘面还没有给出可以无条件扩散的全面修复。"
        )
    else:
        summary = (
            f"收盘定性上，市场更接近「{regime_label}」，强度主要留在 {strong_names}，"
            f"而 {weak_names} 仍然拖累广度，明日先看最强方向能不能延续领导权。"
        )

    return [
        summary,
        f"> 数据交易日：{context.market_date_label}；生成时间：{context.generated_at}；当前定性：{regime_label}。{regime_read}",
    ]


def render_session_report(session_key: str, context: DeskContext, limit: int) -> str:
    session_meta = SESSION_META[session_key]
    regime_label, regime_read = classify_regime(context)
    paths = build_path_tree(
        context.sentiment,
        build_human_nature_snapshot(
            context.sentiment,
            context.top_sectors,
            context.bottom_sectors,
            context.market_flow,
            context.group_flow_rows,
        ),
    )
    do_items, avoid_items = build_execution_lines(context, session_key, regime_label)

    parts: list[str] = [f"# {context.report_date_label} {session_meta['title']}"]
    parts.extend(build_meta_lines(context, session_key, regime_label, regime_read))
    parts.append(f"\n## {session_meta['summary_title']}")
    parts.append(f"- 市场状态：{regime_label}")
    parts.append(f"- 状态解释：{regime_read}")
    parts.append(f"- 情绪快照：{context.sentiment['label']}，{context.sentiment['read']}")

    parts.append("\n## 三层框架")
    parts.append("### 外部冲击层")
    parts.extend(f"- {line}" for line in build_external_layer(context, regime_label))
    parts.append("\n### 国内政策 / 流动性层")
    parts.extend(f"- {line}" for line in build_policy_layer(context))
    parts.append("\n### 内部结构层")
    parts.extend(f"- {line}" for line in build_internal_layer(context, regime_label))

    parts.append("\n## 市场状态分类")
    parts.append(f"- 当前归类：{regime_label}")
    parts.append(f"- 交易姿态：{session_meta['regime_posture']}")
    parts.append("- 判断标准：先看是否板块共振，再看是否能从龙头扩到中军和风险偏好代理。")

    parts.append(f"\n## {session_meta['paths_title']}")
    for item in paths:
        parts.append(f"- {item['path']}：{item['read']}")

    parts.append(f"\n## {session_meta['gates_title']}")
    parts.append(
        format_markdown_table(
            session_meta["gates"],
            [
                ("时间", "time"),
                ("观察门", "watch"),
                ("偏强读法", "bullish"),
                ("偏弱读法", "bearish"),
            ],
        )
    )

    parts.append(f"\n## {session_meta['execution_title']}")
    parts.append("### Do")
    parts.extend(f"- {item}" for item in do_items)
    parts.append("\n### Avoid")
    parts.extend(f"- {item}" for item in avoid_items)

    parts.extend(build_support_tables(context, limit))
    parts.extend(build_watchlist_sections(context))
    parts.extend(build_event_sections(context))

    return "\n".join(parts).strip() + "\n"


def build_context(args: argparse.Namespace) -> DeskContext:
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
        selected_event_groups = list(event_payload.get("default_report_groups", []))
    selected_event_groups = list(dict.fromkeys(selected_event_groups))

    indices = safe_call(fetch_index_snapshot, [])
    top_sectors = safe_call(fetch_sector_movers, [], limit=5, rising=True)
    bottom_sectors = safe_call(fetch_sector_movers, [], limit=5, rising=False)
    market_flow = safe_call(fetch_market_flow_snapshot, dict(DEFAULT_MARKET_FLOW))
    inflow_items = safe_call(fetch_top_main_flows, [], "inflow", limit=max(args.limit, 8))
    outflow_items = safe_call(fetch_top_main_flows, [], "outflow", limit=max(args.limit, 8))
    flow_lookup = build_flow_lookup(inflow_items, outflow_items)
    group_flow_rows = build_group_flow_scoreboard(watchlist, selected_groups, flow_lookup)
    sentiment = build_sentiment_snapshot(
        group_flow_rows=group_flow_rows,
        indices=indices,
        top_sectors=top_sectors,
        bottom_sectors=bottom_sectors,
        flow_snapshot=market_flow,
    )

    all_symbols: list[str] = []
    for group in selected_groups:
        all_symbols.extend(item["symbol"] for item in watchlist[group])
    for group in selected_event_groups:
        all_symbols.extend(item["symbol"] for item in event_groups.get(group, []))
    quotes = safe_call(fetch_tencent_quotes, [], list(dict.fromkeys(all_symbols)))

    group_scoreboard = []
    for group in selected_groups:
        summary = summarize_group(watchlist[group], quotes)
        summary["group"] = group
        group_scoreboard.append(summary)

    event_scoreboard = []
    for group in selected_event_groups:
        summary = summarize_group(event_groups[group], quotes)
        summary["group"] = group
        event_scoreboard.append(summary)

    report_date = detect_report_date(args.date, market_flow)
    report_date_label = display_date(report_date)
    market_date = normalize_date_digits(market_flow.get("as_of")) or report_date
    market_date_label = display_date(market_date)

    return DeskContext(
        report_date=report_date,
        report_date_label=report_date_label,
        market_date_label=market_date_label,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        watchlist=watchlist,
        event_payload=event_payload,
        event_groups=event_groups,
        selected_groups=selected_groups,
        selected_event_groups=selected_event_groups,
        indices=indices,
        top_sectors=top_sectors,
        bottom_sectors=bottom_sectors,
        market_flow=market_flow,
        inflow_items=inflow_items,
        outflow_items=outflow_items,
        flow_lookup=flow_lookup,
        group_flow_rows=group_flow_rows,
        sentiment=sentiment,
        quotes=quotes,
        group_scoreboard=group_scoreboard,
        event_scoreboard=event_scoreboard,
        chain_summary=event_payload.get("chain_summary", []),
    )


SESSION_SLUG = {"pre_market": "pq", "mid_market": "pz", "after_market": "ph"}


def publish_reports(context: DeskContext, session_names: list[str], publish_dir: str, limit: int) -> list[Path]:
    target_dir = Path(publish_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for session_key in session_names:
        content = render_session_report(session_key, context, limit)
        file_path = target_dir / f"{context.report_date}_{session_key}_methodology.md"
        file_path.write_text(content, encoding="utf-8")
        written.append(file_path)
    return written


def rebuild_static_site(api_url: str, config_override: dict | None = None) -> str | None:
    """Rebuild the chaochao static site using the static-report-site skill.

    Looks for the build script in deploy-hub/skills/static-report-site/scripts/build.py.
    Returns the zip path on success, None on failure.
    """
    import subprocess as sp
    import tempfile

    # Find build.py relative to common locations
    candidates = [
        Path.home() / "deploy-hub" / "skills" / "static-report-site" / "scripts" / "build.py",
        Path("/root/deploy-hub/skills/static-report-site/scripts/build.py"),
    ]
    build_script = None
    for c in candidates:
        if c.exists():
            build_script = c
            break

    if not build_script:
        print("Warning: static-report-site build.py not found, skipping static rebuild.", file=sys.stderr)
        return None

    # Write a temp config
    config = config_override or {
        "site_title": "超超的交易笔记",
        "site_subtitle": "A 股决策引擎 | 盘前 · 盘中 · 盘后 日报系统",
        "footer": "Powered by chaochao",
        "sections": {
            "pre_market": {"slug": "pq", "label": "盘前日报", "icon": "\U0001f305"},
            "mid_market": {"slug": "pz", "label": "盘中日报", "icon": "\u2600\ufe0f"},
            "after_market": {"slug": "ph", "label": "盘后日报", "icon": "\U0001f319"},
        },
        "data_source": {"type": "api", "base_url": api_url},
    }

    config_path = Path(tempfile.mktemp(suffix=".json"))
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    output_dir = Path(tempfile.mkdtemp())

    try:
        result = sp.run(
            [sys.executable, str(build_script), "--config", str(config_path), "--output", str(output_dir)],
            capture_output=True if sys.version_info >= (3, 7) else False,
            stdout=sp.PIPE if sys.version_info < (3, 7) else None,
            stderr=sp.PIPE if sys.version_info < (3, 7) else None,
            text=True,
        )
        if result.returncode == 0:
            zip_path = str(output_dir) + ".zip"
            print(f"Static site built: {zip_path}")
            return zip_path
        else:
            print(f"Static build failed: {result.stderr}", file=sys.stderr)
            return None
    finally:
        config_path.unlink(missing_ok=True)


def main() -> int:
    args = build_parser().parse_args()
    context = build_context(args)
    session_names = (
        ["pre_market", "mid_market", "after_market"]
        if args.session == "all"
        else [args.session]
    )

    if args.publish_dir:
        written = publish_reports(context, session_names, args.publish_dir, args.limit)
        result = {"report_date": context.report_date, "written": [str(path) for path in written]}

        # Auto-rebuild static site if reports API is available
        if args.rebuild_static:
            zip_path = rebuild_static_site(args.rebuild_static)
            if zip_path:
                result["static_zip"] = zip_path

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    content = render_session_report(session_names[0], context, args.limit)
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
