#!/usr/bin/env python3
"""
涨停复盘报告生成器

功能:
  1. 今日涨停复盘 — 涨停股列表、连板梯队、首板/二板分布
  2. 5 日线承接选股 — 近 5 天有涨停 + 回踩 5 日线有承接 + 跌破拉回
  3. 每只股的上涨逻辑和事件驱动
  4. 人气估值打分

数据源: MX API (stock_screen) + K 线数据 (eastmoney push2his)
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import mx_api

# ---------------------------------------------------------------------------
# K-line fetcher (eastmoney)
# ---------------------------------------------------------------------------

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

KLINE_URL = (
    "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    "?fields1=f1,f2,f3,f4,f5,f6,f7,f8"
    "&fields2=f51,f52,f53,f54,f55,f56,f57"
    "&klt=101&fqt=1&end=20500101&lmt={lmt}"
    "&secid={secid}"
)


def market_prefix(code: str) -> str:
    """Return eastmoney secid prefix: 0=SZ, 1=SH."""
    if code.startswith(("6", "9")):
        return "1"
    return "0"


def fetch_klines(code: str, days: int = 10) -> list[dict]:
    """Fetch daily K-lines for a stock. Returns list of {date, open, close, high, low, vol, amount}."""
    secid = f"{market_prefix(code)}.{code}"
    url = KLINE_URL.format(secid=secid, lmt=days)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [WARN] kline {code}: {e}", file=sys.stderr)
        return []

    klines_raw = data.get("data", {}).get("klines", [])
    result = []
    for line in klines_raw:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        result.append({
            "date": parts[0],
            "open": float(parts[1]),
            "close": float(parts[2]),
            "high": float(parts[3]),
            "low": float(parts[4]),
            "vol": int(parts[5]),
            "amount": float(parts[6]),
        })
    return result


def calc_ma(klines: list[dict], period: int = 5) -> list[float]:
    """Calculate moving average for close prices."""
    closes = [k["close"] for k in klines]
    ma = []
    for i in range(len(closes)):
        if i < period - 1:
            ma.append(0)
        else:
            ma.append(sum(closes[i - period + 1:i + 1]) / period)
    return ma


# ---------------------------------------------------------------------------
# MX API queries
# ---------------------------------------------------------------------------

def query_zt_today(page_size: int = 100) -> dict:
    """今日涨停股票"""
    return mx_api.stock_screen("今日涨停股票", page_size=page_size)


def query_lianban(page_size: int = 50) -> dict:
    """今日连板股票"""
    return mx_api.stock_screen("今日连板股票", page_size=page_size)


def query_yesterday_zt(page_size: int = 100) -> dict:
    """昨日涨停今日表现"""
    return mx_api.stock_screen("昨日涨停今日表现", page_size=page_size)


def query_zt_concepts(page_size: int = 100) -> dict:
    """今日涨停股票的概念板块"""
    return mx_api.stock_screen("今日涨停股票的概念板块", page_size=page_size)


def query_recent_zt(days: int = 5, page_size: int = 100) -> dict:
    """最近N日有涨停的股票"""
    return mx_api.stock_screen(f"最近{days}个交易日有涨停的股票", page_size=page_size)


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------

def find_col_key(columns: list[dict], keyword: str) -> str | None:
    """Find column key by title keyword."""
    for c in columns:
        if keyword in c.get("title", ""):
            return c["key"]
    return None


def extract_field(row: dict, columns: list[dict], keyword: str) -> str:
    """Extract a field value from a row by column title keyword."""
    key = find_col_key(columns, keyword)
    if key:
        return str(row.get(key, ""))
    return ""


def get_code_name_from_row(row: dict, columns: list[dict]) -> tuple[str, str]:
    """Extract stock code and name from a row."""
    code = extract_field(row, columns, "代码") or extract_field(row, columns, "股票代码")
    name = extract_field(row, columns, "名称") or extract_field(row, columns, "股票名称") or extract_field(row, columns, "简称")
    # Clean up code
    code = code.strip().replace(".SZ", "").replace(".SH", "").replace(".BJ", "")
    if "." in code:
        code = code.split(".")[-1]
    return code, name


# ---------------------------------------------------------------------------
# 人气估值 scoring
# ---------------------------------------------------------------------------

def calc_popularity_score(row: dict, columns: list[dict], lianban: int = 0) -> dict:
    """
    人气估值打分 (0-100):
    - 连板数 (0-30): 越多越强
    - 换手率 (0-20): 适中最好 (5-15% 最佳)
    - 封单额 (0-20): 越大越强
    - 市值 (0-15): 中小市值更具人气
    - 量比 (0-15): 越大越热
    """
    score = 0
    details = {}

    # 连板
    if lianban >= 5:
        s = 30
    elif lianban >= 3:
        s = 25
    elif lianban >= 2:
        s = 18
    elif lianban >= 1:
        s = 10
    else:
        s = 0
    score += s
    details["连板"] = f"{lianban}板={s}分"

    # 换手率
    turnover_str = extract_field(row, columns, "换手率")
    try:
        turnover = float(turnover_str.replace("%", ""))
    except (ValueError, AttributeError):
        turnover = 0
    if 5 <= turnover <= 15:
        s = 20
    elif 3 <= turnover <= 25:
        s = 12
    elif turnover > 0:
        s = 5
    else:
        s = 0
    score += s
    details["换手率"] = f"{turnover:.1f}%={s}分"

    # 封单额
    seal_str = extract_field(row, columns, "封单额") or extract_field(row, columns, "封单")
    try:
        seal = float(seal_str)
        if seal > 500000000:  # > 5亿
            s = 20
        elif seal > 100000000:  # > 1亿
            s = 15
        elif seal > 30000000:  # > 3000万
            s = 10
        else:
            s = 5
        details["封单额"] = f"{seal/100000000:.1f}亿={s}分"
    except (ValueError, TypeError):
        s = 0
        details["封单额"] = f"无数据=0分"
    score += s

    # 市值 (流通市值)
    cap_str = extract_field(row, columns, "流通市值") or extract_field(row, columns, "总市值")
    try:
        cap = float(cap_str)
        if cap < 5000000000:  # < 50亿
            s = 15
        elif cap < 15000000000:  # < 150亿
            s = 12
        elif cap < 50000000000:  # < 500亿
            s = 8
        else:
            s = 3
        details["市值"] = f"{cap/100000000:.0f}亿={s}分"
    except (ValueError, TypeError):
        s = 0
        details["市值"] = f"无数据=0分"
    score += s

    # 量比
    vol_ratio_str = extract_field(row, columns, "量比")
    try:
        vol_ratio = float(vol_ratio_str)
        if vol_ratio > 3:
            s = 15
        elif vol_ratio > 2:
            s = 12
        elif vol_ratio > 1.5:
            s = 8
        else:
            s = 4
        details["量比"] = f"{vol_ratio:.1f}={s}分"
    except (ValueError, TypeError):
        s = 0
        details["量比"] = f"无数据=0分"
    score += s

    # 分级
    if score >= 75:
        grade = "S 极高人气"
    elif score >= 55:
        grade = "A 高人气"
    elif score >= 35:
        grade = "B 中等人气"
    else:
        grade = "C 一般"

    return {"score": score, "grade": grade, "details": details}


# ---------------------------------------------------------------------------
# 5 日线承接选股
# ---------------------------------------------------------------------------

def find_ma5_support_stocks(recent_zt_result: dict) -> list[dict]:
    """
    从近 5 日涨停股中筛选:
    - 股价回踩到 5 日均线附近 (±3%)
    - 有跌破 5 日线后拉回的迹象
    """
    if not recent_zt_result.get("rows"):
        return []

    columns = recent_zt_result["columns"]
    candidates = []

    for row in recent_zt_result["rows"]:
        code, name = get_code_name_from_row(row, columns)
        if not code or len(code) < 6:
            continue

        klines = fetch_klines(code, 10)
        if len(klines) < 5:
            continue

        ma5 = calc_ma(klines, 5)
        latest = klines[-1]
        latest_ma5 = ma5[-1]
        if latest_ma5 == 0:
            continue

        # 条件1: 最新收盘价在 5 日线 ±3% 范围内
        deviation = (latest["close"] - latest_ma5) / latest_ma5
        near_ma5 = abs(deviation) < 0.03

        # 条件2: 最近 3 天内有跌破 5 日线后拉回 (最低价 < ma5 但收盘价 >= ma5)
        bounce_back = False
        for i in range(-3, 0):
            if i + len(klines) < 0:
                continue
            idx = len(klines) + i
            if idx < 5:
                continue
            k = klines[idx]
            m = ma5[idx]
            if m > 0 and k["low"] < m * 0.99 and k["close"] >= m * 0.98:
                bounce_back = True
                break

        if near_ma5 or bounce_back:
            chg = extract_field(row, columns, "涨跌幅")
            candidates.append({
                "code": code,
                "name": name,
                "close": latest["close"],
                "ma5": round(latest_ma5, 2),
                "deviation": f"{deviation*100:+.1f}%",
                "near_ma5": near_ma5,
                "bounce_back": bounce_back,
                "signal": "跌破拉回" if bounce_back else "贴近5日线",
                "chg": chg,
            })

    return candidates


# ---------------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------------

def render_report(
    zt_data: dict,
    lianban_data: dict,
    concepts_data: dict,
    ma5_stocks: list[dict],
    report_date: str,
) -> str:
    lines = [
        f"# 涨停复盘报告",
        f"> 日期：{report_date} | 生成时间：{datetime.now().strftime('%H:%M')}",
        "",
    ]

    # --- Section 1: 涨停概览 ---
    zt_count = zt_data.get("security_count", len(zt_data.get("rows", [])))
    lb_rows = lianban_data.get("rows", [])
    lb_cols = lianban_data.get("columns", [])

    lines.append(f"## 涨停概览")
    lines.append(f"")
    lines.append(f"今日涨停 **{zt_count}** 只")
    lines.append("")

    # --- Section 2: 连板梯队 ---
    if lb_rows:
        lines.append("## 连板梯队")
        lines.append("")
        lines.append("| 股票 | 代码 | 连板数 | 封板时间 | 人气评分 |")
        lines.append("|------|------|--------|----------|----------|")

        for row in lb_rows:
            code, name = get_code_name_from_row(row, lb_cols)
            lb_str = extract_field(row, lb_cols, "连板")
            seal_time = extract_field(row, lb_cols, "封板时间") or extract_field(row, lb_cols, "首次封板")
            try:
                lb_num = int(lb_str)
            except (ValueError, TypeError):
                lb_num = 0
            pop = calc_popularity_score(row, lb_cols, lb_num)
            lines.append(f"| {name} | {code} | {lb_str}板 | {seal_time} | {pop['score']}分 {pop['grade']} |")
        lines.append("")

    # --- Section 3: 首板涨停 + 概念 ---
    zt_cols = concepts_data.get("columns", []) or zt_data.get("columns", [])
    zt_rows = concepts_data.get("rows", []) or zt_data.get("rows", [])

    if zt_rows:
        lines.append("## 今日首板 + 概念驱动")
        lines.append("")
        lines.append("| 股票 | 代码 | 涨跌幅 | 封板时间 | 概念/逻辑 | 人气 |")
        lines.append("|------|------|--------|----------|-----------|------|")

        for row in zt_rows[:30]:
            code, name = get_code_name_from_row(row, zt_cols)
            chg = extract_field(row, zt_cols, "涨跌幅")
            seal_time = extract_field(row, zt_cols, "封板时间") or extract_field(row, zt_cols, "首次封板")
            concept = extract_field(row, zt_cols, "概念") or extract_field(row, zt_cols, "行业")
            if concept and len(concept) > 30:
                concept = concept[:30] + "..."
            pop = calc_popularity_score(row, zt_cols, 1)
            try:
                chg_f = f"{float(chg.replace('%', '')):+.1f}%"
            except (ValueError, AttributeError):
                chg_f = chg
            lines.append(f"| {name} | {code} | {chg_f} | {seal_time} | {concept} | {pop['score']}分 |")
        lines.append("")

    # --- Section 4: 5 日线承接 ---
    if ma5_stocks:
        lines.append("## 5日线承接选股")
        lines.append("")
        lines.append("> 近5天内有涨停，回踩5日均线有承接或跌破后拉回的股票")
        lines.append("")
        lines.append("| 股票 | 代码 | 收盘价 | 5日线 | 偏离度 | 信号 |")
        lines.append("|------|------|--------|-------|--------|------|")
        for s in ma5_stocks:
            lines.append(f"| {s['name']} | {s['code']} | {s['close']} | {s['ma5']} | {s['deviation']} | {s['signal']} |")
        lines.append("")

    # --- Section 5: 人气估值说明 ---
    lines.append("## 人气估值说明")
    lines.append("")
    lines.append("| 维度 | 权重 | 逻辑 |")
    lines.append("|------|------|------|")
    lines.append("| 连板数 | 30分 | 连板越多，市场辨识度越高 |")
    lines.append("| 换手率 | 20分 | 5-15% 最健康，过低锁仓过高分歧 |")
    lines.append("| 封单额 | 20分 | 封单越大，资金认可度越高 |")
    lines.append("| 市值 | 15分 | 中小市值更易成为人气股 |")
    lines.append("| 量比 | 15分 | 量比越大，市场关注度越高 |")
    lines.append("")
    lines.append("| 评级 | 分数段 |")
    lines.append("|------|--------|")
    lines.append("| S 极高人气 | ≥75 |")
    lines.append("| A 高人气 | 55-74 |")
    lines.append("| B 中等人气 | 35-54 |")
    lines.append("| C 一般 | <35 |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="涨停复盘报告生成器")
    parser.add_argument("--date", help="报告日期 YYYYMMDD（默认今天）")
    parser.add_argument("--publish-dir", help="输出目录")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--skip-ma5", action="store_true", help="跳过 5 日线承接（较慢）")
    args = parser.parse_args()

    report_date = args.date or datetime.now().strftime("%Y%m%d")
    print(f"Generating 涨停复盘 for {report_date}...")

    # 1. 今日涨停
    print("  [1/5] 查询今日涨停...")
    zt_data = query_zt_today(args.page_size)

    # 2. 连板梯队
    print("  [2/5] 查询连板股票...")
    lianban_data = query_lianban(50)

    # 3. 涨停概念
    print("  [3/5] 查询涨停概念...")
    concepts_data = query_zt_concepts(args.page_size)

    # 4. 5 日线承接
    ma5_stocks = []
    if not args.skip_ma5:
        print("  [4/5] 查询近 5 日涨停 + K 线分析...")
        recent_data = query_recent_zt(5, args.page_size)
        ma5_stocks = find_ma5_support_stocks(recent_data)
        print(f"    找到 {len(ma5_stocks)} 只 5 日线承接股")
    else:
        print("  [4/5] 跳过 5 日线承接")

    # 5. 生成报告
    print("  [5/5] 生成报告...")
    report = render_report(zt_data, lianban_data, concepts_data, ma5_stocks, report_date)

    if args.publish_dir:
        out_dir = Path(args.publish_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{report_date}_zt_review.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"  Output: {out_path}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
