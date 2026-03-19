#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "assets" / "news_iterator_config.json"
DEFAULT_STATE_DIR = Path.home() / ".a-share-decision-desk" / "news-iterator"
DEFAULT_DB = DEFAULT_STATE_DIR / "news_iterator.sqlite3"
DEFAULT_MARKDOWN = DEFAULT_STATE_DIR / "latest_alerts.md"
DEFAULT_JSONL = DEFAULT_STATE_DIR / "alerts.jsonl"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}


@dataclass
class FeedItem:
    item_key: str
    feed_key: str
    feed_label: str
    source: str
    title: str
    link: str
    summary: str
    published_at: str


def load_config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ensure_state_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def open_db(path: Path) -> sqlite3.Connection:
    ensure_state_dir(path.parent)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            item_key TEXT PRIMARY KEY,
            feed_key TEXT NOT NULL,
            feed_label TEXT NOT NULL,
            source TEXT,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            summary TEXT,
            published_at TEXT,
            inserted_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_key TEXT NOT NULL,
            category TEXT NOT NULL,
            score INTEGER NOT NULL,
            signal TEXT NOT NULL,
            impacted_watchlists_json TEXT NOT NULL,
            matched_entities_json TEXT NOT NULL,
            matched_keywords_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(item_key, category)
        )
        """
    )
    return conn


def normalize_text(value: str) -> str:
    cleaned = value or ""
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_match_text(value: str) -> str:
    cleaned = normalize_text(value)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\bnews\.google\.com\b", " ", cleaned, flags=re.IGNORECASE)
    return cleaned.lower()


def term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(normalize_match_text(term))
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def text_contains_term(text: str, term: str) -> bool:
    return bool(term_pattern(term).search(normalize_match_text(text)))


def parse_datetime(raw: str) -> str:
    if not raw:
        return ""
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()
    except Exception:
        return raw


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def build_item_key(feed_key: str, guid: str, link: str, title: str) -> str:
    base = guid or link or title
    return hashlib.sha256(f"{feed_key}|{base}".encode("utf-8")).hexdigest()


def parse_feed(feed: dict) -> list[FeedItem]:
    payload = fetch_url(feed["url"])
    root = ET.fromstring(payload)
    items: list[FeedItem] = []

    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            title = normalize_text(item.findtext("title"))
            link = normalize_text(item.findtext("link"))
            summary = normalize_text(item.findtext("description"))
            source = normalize_text(item.findtext("source")) or feed["label"]
            guid = normalize_text(item.findtext("guid"))
            published = parse_datetime(normalize_text(item.findtext("pubDate")))
            items.append(
                FeedItem(
                    item_key=build_item_key(feed["key"], guid, link, title),
                    feed_key=feed["key"],
                    feed_label=feed["label"],
                    source=source,
                    title=title,
                    link=link,
                    summary=summary,
                    published_at=published,
                )
            )
        return items

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns):
        title = normalize_text(entry.findtext("atom:title", default="", namespaces=ns))
        link_el = entry.find("atom:link", ns)
        link = normalize_text(link_el.attrib.get("href", "")) if link_el is not None else ""
        summary = normalize_text(entry.findtext("atom:summary", default="", namespaces=ns))
        source = feed["label"]
        guid = normalize_text(entry.findtext("atom:id", default="", namespaces=ns))
        published = parse_datetime(
            normalize_text(entry.findtext("atom:updated", default="", namespaces=ns))
        )
        items.append(
            FeedItem(
                item_key=build_item_key(feed["key"], guid, link, title),
                feed_key=feed["key"],
                feed_label=feed["label"],
                source=source,
                title=title,
                link=link,
                summary=summary,
                published_at=published,
            )
        )
    return items


def match_terms(text: str, terms: list[str]) -> list[str]:
    return sorted({term for term in terms if text_contains_term(text, term)})


def derive_watchlists(
    text: str,
    matched_entities: list[str],
    config: dict,
    categories: list[str],
) -> list[str]:
    watchlists: set[str] = set()

    for entity in matched_entities:
        watchlists.update(config.get("entity_watchlists", {}).get(entity.lower(), []))

    for keyword, groups in config.get("keyword_watchlists", {}).items():
        if text_contains_term(text, keyword):
            watchlists.update(groups)

    if "huge_future" in categories:
        watchlists.update(
            [
                "cross_cycle_anchor12",
                "cross_cycle_ai_hardware",
                "cross_cycle_semis",
                "cross_cycle_software_platforms",
            ]
        )
    if "huge_name_release" in categories:
        watchlists.update(["cross_cycle_anchor12"])
    if "huge_conflict" in categories:
        watchlists.update(
            [
                "war_shock_core12",
                "war_benefit_oil_coal",
                "war_headwind_compute_power",
                "defensive_gauge",
            ]
        )
    return sorted(watchlists)


def score_to_signal(score: int) -> str:
    if score >= 10:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def classify_item(item: FeedItem, config: dict) -> list[dict]:
    title_text = item.title.strip()
    text = f"{item.title} {item.summary}".strip()
    matched_entities = match_terms(title_text, config.get("big_name_entities", []))
    matched_conflict_entities = match_terms(text, config.get("conflict_entities", []))
    matched_future = match_terms(text, config.get("future_keywords", []))
    matched_release = match_terms(title_text, config.get("release_verbs", []))
    matched_conflict = match_terms(text, config.get("conflict_keywords", []))
    matched_energy = match_terms(text, config.get("energy_keywords", []))
    matched_compute_power = match_terms(text, config.get("compute_power_keywords", []))

    alerts: list[dict] = []

    if matched_future and not matched_conflict and not matched_conflict_entities:
        score = len(matched_future) * 2 + (2 if matched_entities else 0)
        categories = ["huge_future"]
        watchlists = derive_watchlists(text, matched_entities, config, categories)
        alerts.append(
            {
                "category": "huge_future",
                "score": score,
                "signal": score_to_signal(score),
                "matched_entities": matched_entities,
                "matched_keywords": matched_future,
                "impacted_watchlists": watchlists,
            }
        )

    if matched_entities and matched_release:
        score = len(matched_entities) * 3 + len(matched_release) * 2
        categories = ["huge_name_release"]
        watchlists = derive_watchlists(text, matched_entities, config, categories)
        alerts.append(
            {
                "category": "huge_name_release",
                "score": score,
                "signal": score_to_signal(score),
                "matched_entities": matched_entities,
                "matched_keywords": matched_release,
                "impacted_watchlists": watchlists,
            }
        )

    if matched_conflict or matched_conflict_entities:
        score = len(matched_conflict) * 3 + len(matched_conflict_entities) * 3
        if matched_energy:
            score += 2
        if matched_compute_power:
            score += 1
        categories = ["huge_conflict"]
        all_entities = sorted(set(matched_conflict_entities + matched_entities))
        watchlists = derive_watchlists(text, all_entities, config, categories)
        alerts.append(
            {
                "category": "huge_conflict",
                "score": score,
                "signal": score_to_signal(score),
                "matched_entities": all_entities,
                "matched_keywords": sorted(set(matched_conflict + matched_energy + matched_compute_power)),
                "impacted_watchlists": watchlists,
            }
        )

    return [alert for alert in alerts if alert["score"] >= 4]


def item_exists(conn: sqlite3.Connection, item_key: str) -> bool:
    row = conn.execute("SELECT 1 FROM items WHERE item_key = ?", (item_key,)).fetchone()
    return row is not None


def insert_item(conn: sqlite3.Connection, item: FeedItem) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO items (
            item_key, feed_key, feed_label, source, title, link, summary, published_at, inserted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.item_key,
            item.feed_key,
            item.feed_label,
            item.source,
            item.title,
            item.link,
            item.summary,
            item.published_at,
            datetime.now(UTC).isoformat(),
        ),
    )


def insert_alert(conn: sqlite3.Connection, item: FeedItem, alert: dict) -> bool:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO alerts (
            item_key, category, score, signal, impacted_watchlists_json, matched_entities_json,
            matched_keywords_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.item_key,
            alert["category"],
            alert["score"],
            alert["signal"],
            json.dumps(alert["impacted_watchlists"], ensure_ascii=False),
            json.dumps(alert["matched_entities"], ensure_ascii=False),
            json.dumps(alert["matched_keywords"], ensure_ascii=False),
            datetime.now(UTC).isoformat(),
        ),
    )
    return cursor.rowcount > 0


def fetch_and_classify(conn: sqlite3.Connection, config: dict) -> list[dict]:
    new_alerts: list[dict] = []
    for feed in config.get("feeds", []):
        try:
            items = parse_feed(feed)
        except Exception as exc:
            new_alerts.append(
                {
                    "system_error": True,
                    "feed_key": feed["key"],
                    "feed_label": feed["label"],
                    "error": str(exc),
                }
            )
            continue

        for item in items:
            is_new_item = not item_exists(conn, item.item_key)
            if is_new_item:
                insert_item(conn, item)
            alerts = classify_item(item, config)
            for alert in alerts:
                if insert_alert(conn, item, alert):
                    row = {"item": item, "alert": alert}
                    new_alerts.append(row)
    conn.commit()
    return new_alerts


def row_to_markdown(row: dict) -> str:
    item: FeedItem = row["item"]
    alert = row["alert"]
    return (
        f"- [{item.title}]({item.link})\n"
        f"  source: {item.source}\n"
        f"  category: `{alert['category']}` | signal: `{alert['signal']}` | score: `{alert['score']}`\n"
        f"  watchlists: {', '.join(alert['impacted_watchlists']) or 'n/a'}\n"
        f"  entities: {', '.join(alert['matched_entities']) or 'n/a'}\n"
        f"  keywords: {', '.join(alert['matched_keywords']) or 'n/a'}"
    )


def append_jsonl(new_alerts: list[dict], jsonl_path: Path) -> None:
    ensure_state_dir(jsonl_path.parent)
    json_lines: list[str] = []

    for row in new_alerts:
        if row.get("system_error"):
            json_lines.append(json.dumps(row, ensure_ascii=False))
        else:
            item = row["item"]
            alert = row["alert"]
            json_lines.append(
                json.dumps(
                    {
                        "item_key": item.item_key,
                        "title": item.title,
                        "link": item.link,
                        "source": item.source,
                        "published_at": item.published_at,
                        "category": alert["category"],
                        "score": alert["score"],
                        "signal": alert["signal"],
                        "impacted_watchlists": alert["impacted_watchlists"],
                        "matched_entities": alert["matched_entities"],
                        "matched_keywords": alert["matched_keywords"],
                    },
                    ensure_ascii=False,
                )
            )
    with jsonl_path.open("a", encoding="utf-8") as handle:
        for line in json_lines:
            handle.write(line + "\n")


def fetch_recent_alerts(conn: sqlite3.Connection, hours: int) -> list[dict]:
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        """
        SELECT
            a.category,
            a.score,
            a.signal,
            a.impacted_watchlists_json,
            a.matched_entities_json,
            a.matched_keywords_json,
            i.title,
            i.link,
            i.source,
            i.published_at
        FROM alerts a
        JOIN items i ON i.item_key = a.item_key
        WHERE a.created_at >= ?
        ORDER BY a.score DESC, a.created_at DESC
        """,
        (cutoff,),
    ).fetchall()

    result = []
    for row in rows:
        result.append(
            {
                "category": row[0],
                "score": row[1],
                "signal": row[2],
                "watchlists": json.loads(row[3]),
                "entities": json.loads(row[4]),
                "keywords": json.loads(row[5]),
                "title": row[6],
                "link": row[7],
                "source": row[8],
                "published_at": row[9],
            }
        )
    return result


def render_report(alerts: list[dict], hours: int) -> str:
    lines = [f"# News Iterator Report", f"", f"Window: last {hours} hours"]
    if not alerts:
        lines.append("\nNo alerts in the selected window.")
        return "\n".join(lines) + "\n"

    current_category = None
    for alert in alerts:
        if alert["category"] != current_category:
            current_category = alert["category"]
            lines.append(f"\n## {current_category}")
        lines.append(f"- [{alert['title']}]({alert['link']})")
        lines.append(
            f"  source: {alert['source']} | signal: `{alert['signal']}` | score: `{alert['score']}`"
        )
        lines.append(f"  watchlists: {', '.join(alert['watchlists']) or 'n/a'}")
        lines.append(f"  entities: {', '.join(alert['entities']) or 'n/a'}")
        lines.append(f"  keywords: {', '.join(alert['keywords']) or 'n/a'}")
    return "\n".join(lines) + "\n"


def render_system_errors(rows: list[dict]) -> str:
    if not rows:
        return ""
    lines = ["\n## system_error"]
    for row in rows:
        lines.append(f"- feed: `{row['feed_key']}` ({row['feed_label']}) | error: {row['error']}")
    return "\n".join(lines) + "\n"


def run_poll(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    conn = open_db(Path(args.db_path))
    try:
        new_alerts = fetch_and_classify(conn, config)
        append_jsonl(new_alerts, Path(args.jsonl_path))
        recent_alerts = fetch_recent_alerts(conn, args.report_hours)
        markdown = render_report(recent_alerts, args.report_hours)
        system_errors = [row for row in new_alerts if row.get("system_error")]
        markdown += render_system_errors(system_errors)
        Path(args.markdown_path).write_text(markdown, encoding="utf-8")
        if args.format == "json":
            serializable = []
            for row in new_alerts:
                if row.get("system_error"):
                    serializable.append(row)
                    continue
                item: FeedItem = row["item"]
                serializable.append(
                    {
                        "title": item.title,
                        "link": item.link,
                        "source": item.source,
                        "published_at": item.published_at,
                        **row["alert"],
                    }
                )
            print(json.dumps(serializable, ensure_ascii=False, indent=2))
        else:
            print(markdown)
        return 0
    finally:
        conn.close()


def run_loop(args: argparse.Namespace) -> int:
    interval = max(args.interval_seconds, 30)
    while True:
        run_poll(args)
        time.sleep(interval)


def run_report(args: argparse.Namespace) -> int:
    conn = open_db(Path(args.db_path))
    try:
        alerts = fetch_recent_alerts(conn, args.hours)
        print(render_report(alerts, args.hours))
        return 0
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persistent RSS-based news iterator for A-share idea intake.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to news iterator config JSON.")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="State directory for reports and DB.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_io(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--db-path",
            default=str(DEFAULT_DB),
            help="SQLite database path. Defaults under the state directory.",
        )
        subparser.add_argument(
            "--markdown-path",
            default=str(DEFAULT_MARKDOWN),
            help="Markdown alert output path.",
        )
        subparser.add_argument(
            "--jsonl-path",
            default=str(DEFAULT_JSONL),
            help="JSONL alert output path.",
        )
        subparser.add_argument(
            "--report-hours",
            type=int,
            default=24,
            help="Lookback window for the markdown snapshot report.",
        )
        subparser.add_argument("--format", choices=["markdown", "json"], default="markdown")

    poll = subparsers.add_parser("poll", help="Fetch feeds once and store new alerts.")
    add_common_io(poll)
    poll.set_defaults(func=run_poll)

    loop = subparsers.add_parser("loop", help="Continuously fetch feeds on an interval.")
    add_common_io(loop)
    loop.add_argument("--interval-seconds", type=int, default=300, help="Polling interval in seconds.")
    loop.set_defaults(func=run_loop)

    report = subparsers.add_parser("report", help="Render a report from stored alerts.")
    report.add_argument(
        "--db-path",
        default=str(DEFAULT_DB),
        help="SQLite database path. Defaults under the state directory.",
    )
    report.add_argument("--hours", type=int, default=12, help="Lookback window in hours.")
    report.set_defaults(func=run_report)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    state_dir = Path(args.state_dir)
    ensure_state_dir(state_dir)

    if getattr(args, "db_path", None) == str(DEFAULT_DB):
        args.db_path = str(state_dir / DEFAULT_DB.name)
    if getattr(args, "markdown_path", None) == str(DEFAULT_MARKDOWN):
        args.markdown_path = str(state_dir / DEFAULT_MARKDOWN.name)
    if getattr(args, "jsonl_path", None) == str(DEFAULT_JSONL):
        args.jsonl_path = str(state_dir / DEFAULT_JSONL.name)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
