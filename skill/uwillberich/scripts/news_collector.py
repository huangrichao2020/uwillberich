#!/usr/bin/env python3
"""
A-share News Collector — 国内新闻聚合器

从百度资讯、东方财富、新浪财经等国内源采集财经新闻，
每 5 分钟更新一次，输出到 uwillberich-reports 可读的格式。

数据源:
  1. 百度千帆 AI 搜索 — 综合各大财经平台的热点摘要
  2. 东方财富快讯 — 实时财经快讯
  3. 新浪财经要闻 — 7x24 小时滚动资讯

用法:
  python3 news_collector.py poll           # 单次采集
  python3 news_collector.py poll --loop    # 持续采集 (每 5 分钟)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STATE_DIR = Path(os.environ.get("UWILLBERICH_NEWS_DIR", "")) or (Path.home() / ".uwillberich" / "news-collector")
DB_NAME = "news.sqlite3"
OUTPUT_MD = "latest_news.md"
OUTPUT_JSON = "latest_news.json"
OUTPUT_BAIDU_JSON = "baidu_insights.json"
POLL_INTERVAL = 300  # 5 minutes
MARKET_HOURS = (9, 21)  # 09:00 - 21:00

# Baidu Qianfan AI Search
BAIDU_API_URL = "https://qianfan.baidubce.com/v2/ai_search/web_summary"

# EastMoney live news (kuaixun JSONP)
EM_LIVE_URL = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"

# Sina 7x24
SINA_LIVE_URL = "https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=30&zhibo_id=152&tag_id=0&dire=f&dpc=1"

# 财联社电报
CLS_LIVE_URL = "https://www.cls.cn/nodeapi/updateTelegraphList?app=CailianpressWeb&os=web&sv=8.4.6&rn=30"

# 同花顺快讯
THS_LIVE_URL = "https://news.10jqka.com.cn/tapp/news/push/stock/?page=1&tag=&track=website&pagesize=30"
THS_HEADERS = {"Referer": "https://news.10jqka.com.cn/"}

BAIDU_QUERIES = [
    {"query": "雪球 知乎 A股大V 最新看法 看好什么方向 操作建议", "label": "大V看盘"},
    {"query": "A股 知名博主 分析师 板块观点 主线判断 龙头推荐", "label": "主线研判"},
    {"query": "东方财富 同花顺 股吧 热议话题 散户情绪 市场讨论", "label": "市场情绪"},
]

# SSL context that skips verification (some CN sites have cert issues)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def get_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            category TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            published_at TEXT,
            collected_at TEXT NOT NULL,
            raw_json TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_collected ON news(collected_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_source ON news(source)")
    conn.commit()
    return conn


def news_exists(conn: sqlite3.Connection, news_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM news WHERE id = ?", (news_id,)).fetchone()
    return row is not None


def insert_news(conn: sqlite3.Connection, item: dict) -> bool:
    if news_exists(conn, item["id"]):
        return False
    conn.execute(
        "INSERT INTO news (id, source, category, title, summary, url, published_at, collected_at, raw_json) VALUES (?,?,?,?,?,?,?,?,?)",
        (item["id"], item["source"], item.get("category", ""),
         item["title"], item.get("summary", ""), item.get("url", ""),
         item.get("published_at", ""), item["collected_at"],
         json.dumps(item, ensure_ascii=False)),
    )
    return True

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def http_get(url: str, headers: dict | None = None, timeout: int = 15) -> str | None:
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; uwillberich/1.0)")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            data = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return data.decode(charset, errors="replace")
    except Exception as e:
        print(f"  [WARN] GET {url[:80]}... failed: {e}", file=sys.stderr)
        return None


def http_post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 20) -> dict | None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    h = {"Content-Type": "application/json", "User-Agent": "uwillberich/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  [WARN] POST {url[:80]}... failed: {e}", file=sys.stderr)
        return None

# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def make_id(source: str, text: str) -> str:
    return hashlib.md5(f"{source}:{text}".encode()).hexdigest()[:16]


def collect_eastmoney() -> list[dict]:
    """东方财富快讯 (JSONP endpoint)"""
    items = []
    raw = http_get(EM_LIVE_URL)
    if not raw:
        return items
    try:
        # Strip JSONP wrapper: var ajaxResult={...}
        json_str = raw
        if json_str.startswith("var "):
            json_str = json_str.split("=", 1)[1].strip()
            if json_str.endswith(";"):
                json_str = json_str[:-1]
        data = json.loads(json_str)
        news_list = data.get("LivesList", [])
        now = datetime.now().isoformat(timespec="seconds")
        for n in news_list:
            title = n.get("title", "").strip()
            if not title:
                continue
            digest = n.get("digest", "").strip()
            url = n.get("url_unique", "") or n.get("url_w", "") or ""
            pub_time = n.get("showtime", "")
            items.append({
                "id": make_id("eastmoney", title),
                "source": "eastmoney",
                "category": "快讯",
                "title": title,
                "summary": digest[:200] if digest != title else "",
                "url": url,
                "published_at": pub_time,
                "collected_at": now,
            })
    except Exception as e:
        print(f"  [WARN] eastmoney parse error: {e}", file=sys.stderr)
    return items


def collect_sina() -> list[dict]:
    """新浪财经 7x24"""
    items = []
    raw = http_get(SINA_LIVE_URL)
    if not raw:
        return items
    try:
        data = json.loads(raw)
        feed_list = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
        now = datetime.now().isoformat(timespec="seconds")
        for n in feed_list:
            rich_text = n.get("rich_text", "").strip()
            if not rich_text:
                continue
            # Extract first sentence as title
            title = re.split(r'[。！？\n]', rich_text)[0][:80]
            pub_time = n.get("create_time", "")
            items.append({
                "id": make_id("sina", rich_text[:100]),
                "source": "sina",
                "category": "7x24",
                "title": title,
                "summary": rich_text[:300],
                "url": "",
                "published_at": pub_time,
                "collected_at": now,
            })
    except Exception as e:
        print(f"  [WARN] sina parse error: {e}", file=sys.stderr)
    return items


def collect_cls() -> list[dict]:
    """财联社电报"""
    items = []
    raw = http_get(CLS_LIVE_URL)
    if not raw:
        return items
    try:
        data = json.loads(raw)
        news_list = data.get("data", {}).get("roll_data", [])
        now = datetime.now().isoformat(timespec="seconds")
        for n in news_list:
            title = (n.get("title", "") or "").strip()
            content = (n.get("content", "") or "").strip()
            if not title and not content:
                continue
            if not title:
                title = re.split(r'[。！？\n]', content)[0][:80]
            ctime = n.get("ctime", "")
            pub_time = datetime.fromtimestamp(int(ctime)).strftime("%Y-%m-%d %H:%M:%S") if ctime else ""
            items.append({
                "id": make_id("cls", title or content[:80]),
                "source": "cls",
                "category": "电报",
                "title": title,
                "summary": content[:300] if content != title else "",
                "url": "",
                "published_at": pub_time,
                "collected_at": now,
            })
    except Exception as e:
        print(f"  [WARN] cls parse error: {e}", file=sys.stderr)
    return items


def collect_ths() -> list[dict]:
    """同花顺快讯"""
    items = []
    raw = http_get(THS_LIVE_URL, headers=THS_HEADERS)
    if not raw:
        return items
    try:
        data = json.loads(raw)
        news_list = data.get("data", {}).get("list", [])
        now = datetime.now().isoformat(timespec="seconds")
        for n in news_list:
            title = (n.get("title", "") or "").strip()
            digest = (n.get("digest", "") or "").strip()
            if not title:
                continue
            ctime = n.get("ctime", "")
            pub_time = datetime.fromtimestamp(int(ctime)).strftime("%Y-%m-%d %H:%M:%S") if ctime else ""
            url = n.get("url", "") or ""
            # Extract tag names
            tags = [t.get("name", "") for t in n.get("tagInfo", [])]
            tag_str = "、".join(tags) if tags else ""
            items.append({
                "id": make_id("ths", title),
                "source": "ths",
                "category": tag_str or "快讯",
                "title": title,
                "summary": digest[:300] if digest != title else "",
                "url": url,
                "published_at": pub_time,
                "collected_at": now,
            })
    except Exception as e:
        print(f"  [WARN] ths parse error: {e}", file=sys.stderr)
    return items


BAIDU_INSTRUCTION = (
    "你是A股市场观点聚合专家。"
    "只提取和总结大V、知名博主、分析师的核心观点和判断，不要自行编造数据表格。"
    "重点关注：他们看好什么方向、看空什么板块、核心逻辑是什么、给出了什么操作建议。"
    "用简洁的中文分条列出，每条标注来源作者或平台。不需要罗列指数点位等可查数据。"
)
BAIDU_SITES = ["xueqiu.com", "www.zhihu.com", "www.eastmoney.com", "www.10jqka.com.cn", "cls.cn", "wallstreetcn.com"]


def collect_baidu(api_key: str) -> list[dict]:
    """百度千帆 AI 搜索（兼容 openclaw baidu-finance-search skill 格式）"""
    if not api_key:
        print("  [SKIP] baidu: no BAIDU_API_KEY", file=sys.stderr)
        return []

    items = []
    now = datetime.now().isoformat(timespec="seconds")

    # 计算 1 天前的日期用于时间过滤
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    for q in BAIDU_QUERIES:
        payload = {
            "instruction": BAIDU_INSTRUCTION,
            "messages": [{"role": "user", "content": q["query"]}],
            "resource_type_filter": [{"type": "web", "top_k": 8}],
            "search_filter": {
                "match": {"site": BAIDU_SITES},
                "range": {"page_time": {"gt": yesterday}},
            },
        }
        resp = http_post_json(
            BAIDU_API_URL,
            payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        if not resp:
            continue

        # Extract AI summary (choices[0].message.content)
        answer = ""
        for choice in resp.get("choices", []):
            msg = choice.get("message", {})
            answer += msg.get("content", "")

        # Extract references
        refs = resp.get("references", []) or resp.get("search_results", [])

        if answer:
            ref_items = []
            for r in refs[:8]:
                ref_title = r.get("title", "")
                ref_url = r.get("url", "")
                ref_site = r.get("website", "")
                ref_items.append({"title": ref_title, "url": ref_url, "site": ref_site})

            items.append({
                "id": make_id("baidu", q["query"] + now[:13]),  # 精确到小时去重
                "source": "baidu",
                "category": q["label"],
                "title": q["label"],
                "summary": answer,  # 保留完整内容，不截断
                "url": "",
                "published_at": now,
                "collected_at": now,
                "refs": ref_items,
            })

        time.sleep(3)  # 百度 API 每次 ~30s，间隔 3 秒避免 429

    return items

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def render_markdown(conn: sqlite3.Connection, hours: int = 4) -> str:
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT source, category, title, summary, url, published_at, collected_at FROM news "
        "WHERE collected_at >= ? ORDER BY collected_at DESC",
        (cutoff,)
    ).fetchall()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# A股新闻雷达",
        f"> 更新时间：{now_str} | 最近 {hours} 小时 | 共 {len(rows)} 条",
        "",
    ]

    # Group by source
    by_source: dict[str, list] = {}
    for row in rows:
        src = row[0]
        by_source.setdefault(src, []).append(row)

    source_labels = {
        "baidu": "百度 AI 搜索摘要",
        "cls": "财联社电报",
        "eastmoney": "东方财富快讯",
        "ths": "同花顺快讯",
        "sina": "新浪 7x24",
    }

    for src, label in source_labels.items():
        news = by_source.get(src, [])
        if not news:
            continue
        lines.append(f"## {label}")
        lines.append("")
        for row in news[:20]:
            _, cat, title, summary, url, pub_time, _ = row
            cat_tag = f"[{cat}] " if cat else ""
            time_tag = f" ({pub_time})" if pub_time else ""
            lines.append(f"### {cat_tag}{title}{time_tag}")
            if summary and summary != title:
                lines.append("")
                lines.append(summary[:400])
            if url:
                lines.append(f"\n[详情]({url})")
            lines.append("")

    return "\n".join(lines)


def render_json(conn: sqlite3.Connection, hours: int = 4) -> list[dict]:
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT id, source, category, title, summary, url, published_at, collected_at FROM news "
        "WHERE collected_at >= ? ORDER BY collected_at DESC",
        (cutoff,)
    ).fetchall()
    return [
        {"id": r[0], "source": r[1], "category": r[2], "title": r[3],
         "summary": r[4], "url": r[5], "published_at": r[6], "collected_at": r[7]}
        for r in rows
    ]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_env_key(name: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    env_path = Path.home() / ".uwillberich" / "runtime.env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _flush_outputs(conn: sqlite3.Connection, output_dir: Path, publish_dir: Path | None, report_hours: int):
    """Write JSON + MD to output_dir and optionally copy to publish_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    news_list = render_json(conn, report_hours)
    (output_dir / OUTPUT_JSON).write_text(json.dumps(news_list, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / OUTPUT_MD).write_text(render_markdown(conn, report_hours), encoding="utf-8")

    if publish_dir:
        publish_dir.mkdir(parents=True, exist_ok=True)
        for fname in [OUTPUT_JSON, OUTPUT_MD]:
            src = output_dir / fname
            if src.exists():
                (publish_dir / fname).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _flush_baidu(baidu_items: list[dict], output_dir: Path, publish_dir: Path | None):
    """Write baidu insights to a separate file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OUTPUT_BAIDU_JSON).write_text(
        json.dumps(baidu_items, ensure_ascii=False, indent=2), encoding="utf-8")
    if publish_dir:
        publish_dir.mkdir(parents=True, exist_ok=True)
        (publish_dir / OUTPUT_BAIDU_JSON).write_text(
            json.dumps(baidu_items, ensure_ascii=False, indent=2), encoding="utf-8")


def poll_once(db_path: Path, output_dir: Path, report_hours: int = 4,
              publish_dir: Path | None = None) -> dict:
    conn = get_db(db_path)
    db_lock = threading.Lock()
    baidu_key = load_env_key("BAIDU_API_KEY")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecting news (parallel)...")
    counters: dict[str, dict] = {}

    def run_collector(name: str, fn, is_baidu: bool = False):
        try:
            items = fn() if not is_baidu else fn(baidu_key)
            with db_lock:
                added = sum(1 for item in items if insert_news(conn, item))
                conn.commit()
                counters[name] = {"fetched": len(items), "added": added}
                print(f"  {name}: {len(items)} fetched, {added} new")

                # Flush outputs immediately so webpage gets data ASAP
                if is_baidu:
                    _flush_baidu(items, output_dir, publish_dir)
                _flush_outputs(conn, output_dir, publish_dir, report_hours)
        except Exception as e:
            counters[name] = {"fetched": 0, "added": 0, "error": str(e)}
            print(f"  {name}: ERROR {e}", file=sys.stderr)

    # Launch all collectors in parallel
    threads = []
    for name, fn in [
        ("eastmoney", collect_eastmoney),
        ("sina", collect_sina),
        ("cls", collect_cls),
        ("ths", collect_ths),
    ]:
        t = threading.Thread(target=run_collector, args=(name, fn), daemon=True)
        threads.append(t)
        t.start()

    # Baidu runs in parallel too (it's slow but shouldn't block others)
    baidu_thread = threading.Thread(target=run_collector, args=("baidu", collect_baidu, True), daemon=True)
    baidu_thread.start()
    threads.append(baidu_thread)

    # Wait for all
    for t in threads:
        t.join(timeout=180)

    total_new = sum(c.get("added", 0) for c in counters.values())
    news_list = render_json(conn, report_hours)
    conn.close()

    print(f"  Total new: {total_new}, total recent: {len(news_list)}")
    return {"new_count": total_new, "total_recent": len(news_list)}


def main():
    parser = argparse.ArgumentParser(description="A-share News Collector")
    sub = parser.add_subparsers(dest="command")

    poll_p = sub.add_parser("poll", help="Collect news once or in a loop")
    poll_p.add_argument("--loop", action="store_true", help="Run continuously every 5 minutes")
    poll_p.add_argument("--interval", type=int, default=POLL_INTERVAL, help="Poll interval in seconds (default: 300)")
    poll_p.add_argument("--db-path", type=Path, default=STATE_DIR / DB_NAME)
    poll_p.add_argument("--output-dir", type=Path, default=STATE_DIR)
    poll_p.add_argument("--report-hours", type=int, default=4, help="Hours of news to include in output")
    poll_p.add_argument("--publish-dir", type=Path, default=None,
                        help="Also copy output to this directory (e.g. uwillberich-reports/public/news/)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    if args.command == "poll":
        if args.loop:
            print(f"Starting news loop (interval={args.interval}s, hours={MARKET_HOURS[0]}-{MARKET_HOURS[1]})")
            while True:
                hour = datetime.now().hour
                if MARKET_HOURS[0] <= hour < MARKET_HOURS[1]:
                    poll_once(args.db_path, args.output_dir, args.report_hours, args.publish_dir)
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Outside market hours ({MARKET_HOURS[0]}-{MARKET_HOURS[1]}), sleeping...")
                time.sleep(args.interval)
        else:
            result = poll_once(args.db_path, args.output_dir, args.report_hours, args.publish_dir)
            print(json.dumps(result, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
