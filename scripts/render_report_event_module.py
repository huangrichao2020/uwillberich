#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path


DESKTOP_STYLE = """
/* report-event-enhancer:start */
.hero h1 {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.title-plus {
  font-size: clamp(2.1rem, 4vw, 3.2rem);
  font-weight: 900;
  color: #b45309;
  line-height: 1;
}

.source-list {
  list-style: none;
  padding: 0;
  margin: 18px 0 0;
  display: grid;
  gap: 14px;
}

.source-list li {
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 18px;
  background: #fffdf7;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
  padding: 16px 18px;
}

.news-title {
  margin: 0 0 10px;
  font-size: 1.14rem;
  font-weight: 900;
  line-height: 1.55;
}

.news-title a {
  color: #111827;
  text-decoration: none;
}

.news-title a:hover {
  color: #92400e;
}

.news-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
  font-size: 1.02rem;
  font-weight: 900;
  color: #92400e;
  text-decoration: none;
}

.news-link:hover {
  color: #7c2d12;
}

.source-translation {
  display: block;
  margin-top: 12px;
  font-size: 0.98rem;
  line-height: 1.7;
  color: #4b5563;
}

.news-matrix {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.news-matrix span {
  display: block;
  padding: 11px 13px;
  border-radius: 14px;
  background: #f8fafc;
  color: #1f2937;
  font-size: 0.95rem;
  line-height: 1.6;
}

.source-meta {
  display: block;
  margin-top: 12px;
  color: #6b7280;
  font-size: 0.92rem;
  font-weight: 700;
}

.event-outlook {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 22px 0 0;
}

.event-outlook-card {
  border-radius: 18px;
  background: linear-gradient(180deg, #fff8eb 0%, #fff 100%);
  border: 1px solid rgba(180, 83, 9, 0.12);
  padding: 16px 18px;
}

.event-outlook-card strong {
  display: block;
  margin-bottom: 10px;
  color: #92400e;
  font-size: 1rem;
}

.news-group {
  margin-top: 26px;
}
/* report-event-enhancer:end */
"""


MOBILE_STYLE = """
/* report-event-enhancer:start */
.hero h1 {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.title-plus {
  font-size: 1.7rem;
  font-weight: 900;
  color: var(--accent);
  line-height: 1;
}

.source-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.source-list li {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.94);
  border-radius: 16px;
  padding: 14px;
}

.news-title {
  margin: 0 0 10px;
  font-size: 1rem;
  font-weight: 900;
  line-height: 1.55;
}

.news-title a {
  color: var(--ink);
  text-decoration: none;
}

.news-link {
  display: inline-flex;
  margin-top: 2px;
  font-size: 0.97rem;
  font-weight: 900;
  color: var(--accent);
  text-decoration: none;
}

.source-translation {
  display: block;
  margin-top: 10px;
  color: var(--muted);
  line-height: 1.65;
}

.news-matrix {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.news-matrix span {
  display: block;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.04);
  color: var(--ink);
  font-size: 0.92rem;
  line-height: 1.55;
}

.source-meta {
  display: block;
  margin-top: 10px;
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 700;
}

.event-outlook {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}
/* report-event-enhancer:end */
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the standardized title and event-news module to report HTML pages."
    )
    parser.add_argument("--data", required=True, help="Path to the structured event payload JSON.")
    parser.add_argument("--desktop", required=True, help="Path to the desktop HTML page.")
    parser.add_argument("--mobile", required=True, help="Path to the mobile HTML page.")
    parser.add_argument(
        "--publish-dir",
        help="Optional directory to copy the rendered desktop/mobile pages into after patching.",
    )
    return parser


def load_payload(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def clean_text(value: object) -> str:
    text = str(value or "")
    while True:
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    return re.sub(r"\s+", " ", text).strip()


def ensure_prefixed_translation(text: str) -> str:
    clean = clean_text(text)
    if not clean:
        return ""
    if clean.startswith("中文译意："):
        return clean
    return f"中文译意：{clean}"


def build_title_markup(payload: dict) -> str:
    left = html.escape(clean_text(payload["title_left"]))
    right = html.escape(clean_text(payload["title_right"]))
    return f'<h1><span>{left}</span><span class="title-plus">+</span><span>{right}</span></h1>'


def render_news_item(item: dict) -> str:
    title = html.escape(clean_text(item.get("title", "")))
    link = html.escape(clean_text(item.get("link", "")), quote=True)
    link_label = html.escape(clean_text(item.get("link_label", "打开原文链接")))
    translation = html.escape(ensure_prefixed_translation(item.get("translation", "")))
    impact_sectors = html.escape(clean_text(item.get("impact_sectors", "待补充")))
    leaders = html.escape(clean_text(item.get("leaders", "待补充")))
    source = html.escape(clean_text(item.get("source", "")))
    score = item.get("score")
    meta = source if source else ""
    if score is not None:
        meta = f"{meta}｜分值 {score}" if meta else f"分值 {score}"
    meta_markup = f'<span class="source-meta">{html.escape(meta)}</span>' if meta else ""
    translation_markup = (
        f'<span class="source-translation">{translation}</span>' if translation else ""
    )
    return (
        "<li>"
        f'<div class="news-title"><a href="{link}">{title}</a></div>'
        f'<a class="news-link" href="{link}">{link_label}</a>'
        f"{translation_markup}"
        '<div class="news-matrix">'
        f"<span><strong>影响板块：</strong>{impact_sectors}</span>"
        f"<span><strong>观察龙头：</strong>{leaders}</span>"
        "</div>"
        f"{meta_markup}"
        "</li>"
    )


def render_event_section_desktop(payload: dict) -> str:
    event = payload["event"]
    summary_rows = "\n".join(
        f"<tr><td>{html.escape(clean_text(item['label']))}</td><td>{item['count']}</td><td>{item['score']}</td><td>{html.escape(clean_text(item['keywords']))}</td></tr>"
        for item in event.get("summary", [])
    )
    outlook_cards = "\n".join(
        (
            '<div class="event-outlook-card">'
            f"<strong>{html.escape(clean_text(card['title']))}</strong>"
            f"{html.escape(clean_text(card['text']))}"
            "</div>"
        )
        for card in event.get("outlook", [])
    )
    groups_markup = []
    for group in event.get("groups", []):
        items_markup = "\n".join(render_news_item(item) for item in group.get("items", []))
        groups_markup.append(
            '<div class="news-group">'
            f"<h3>{html.escape(clean_text(group['label']))}最重要 10 条信息源</h3>"
            f"<p>{html.escape(clean_text(group.get('intro', '')))}</p>"
            f'<ol class="source-list">{items_markup}</ol>'
            "</div>"
        )

    return (
        '<section class="section" id="event">\n'
        "  <h2>事件驱动层总结</h2>\n"
        f"  <p>{html.escape(clean_text(event.get('intro', '')))}</p>\n"
        "  <table>\n"
        "    <thead>\n"
        "      <tr>\n"
        "        <th>消息类别</th>\n"
        "        <th>条数</th>\n"
        "        <th>总分</th>\n"
        "        <th>高频关键词</th>\n"
        "      </tr>\n"
        "    </thead>\n"
        f"    <tbody>\n{summary_rows}\n    </tbody>\n"
        "  </table>\n"
        f'  <div class="event-outlook">\n{outlook_cards}\n  </div>\n'
        f"  {' '.join(groups_markup)}\n"
        "</section>"
    )


def render_event_section_mobile(payload: dict) -> str:
    event = payload["event"]
    summary_cards = "\n".join(
        (
            '<article class="card">'
            f'<div class="card-title">{html.escape(clean_text(item["label"]))}</div>'
            f"<p>{item['count']} 条，得分 {item['score']}</p>"
            f'<p class="card-muted">关键词：{html.escape(clean_text(item["keywords"]))}</p>'
            "</article>"
        )
        for item in event.get("summary", [])
    )
    outlook_cards = "\n".join(
        (
            '<article class="card">'
            f'<div class="card-title">{html.escape(clean_text(card["title"]))}</div>'
            f'<p class="card-muted">{html.escape(clean_text(card["text"]))}</p>'
            "</article>"
        )
        for card in event.get("outlook", [])
    )
    group_panels = []
    for group in event.get("groups", []):
        items_markup = "\n".join(render_news_item(item) for item in group.get("items", []))
        group_panels.append(
            '<details class="card source-panel" data-source-panel open>'
            "<summary>"
            "<div>"
            f'<div class="card-title">{html.escape(clean_text(group["label"]))}最重要 10 条信息源</div>'
            f'<p class="card-muted">{html.escape(clean_text(group.get("intro", "")))}</p>'
            "</div>"
            "</summary>"
            f'<div class="panel-body"><ol class="source-list">{items_markup}</ol></div>'
            "</details>"
        )

    return (
        '<section class="section" id="event">\n'
        "  <h2>事件驱动层</h2>\n"
        f'  <div class="cards">\n{summary_cards}\n  </div>\n'
        f"  <p>{html.escape(clean_text(event.get('intro', '')))}</p>\n"
        f'  <div class="event-outlook">\n{outlook_cards}\n  </div>\n'
        '  <div class="panel-tools">\n'
        '    <button type="button" data-source-action="expand">展开全部信息源</button>\n'
        '    <button type="button" data-source-action="collapse">收起全部信息源</button>\n'
        "  </div>\n"
        f'  <div class="cards">\n{"".join(group_panels)}\n  </div>\n'
        "</section>"
    )


def inject_style(document: str, css_block: str) -> str:
    start = "/* report-event-enhancer:start */"
    end = "/* report-event-enhancer:end */"
    if start in document and end in document:
        return re.sub(
            re.escape(start) + r".*?" + re.escape(end),
            css_block.strip(),
            document,
            flags=re.S,
        )
    if all(token in document for token in (".title-plus", ".news-title", ".news-link", ".news-matrix")):
        return document
    if "</style>" not in document:
        raise ValueError("cannot inject enhancer CSS: missing </style>")
    return document.replace("</style>", f"{css_block}\n</style>", 1)


def replace_hero_title(document: str, payload: dict) -> str:
    title_markup = build_title_markup(payload)
    pattern = re.compile(r'(<span class="eyebrow">.*?</span>\s*)<h1>.*?</h1>', re.S)
    if not pattern.search(document):
        raise ValueError("cannot replace hero title: missing eyebrow + h1 block")
    return pattern.sub(rf"\1{title_markup}", document, count=1)


def replace_event_section(document: str, section_markup: str) -> str:
    pattern = re.compile(r'<section class="section" id="event">.*?</section>', re.S)
    if not pattern.search(document):
        raise ValueError("cannot replace event section: missing #event section")
    return pattern.sub(section_markup, document, count=1)


def render_file(path: Path, payload: dict, mobile: bool) -> None:
    document = path.read_text(encoding="utf-8")
    document = inject_style(document, MOBILE_STYLE if mobile else DESKTOP_STYLE)
    document = replace_hero_title(document, payload)
    document = replace_event_section(
        document,
        render_event_section_mobile(payload) if mobile else render_event_section_desktop(payload),
    )
    path.write_text(document, encoding="utf-8")


def publish(paths: list[Path], publish_dir: Path) -> None:
    publish_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copy2(path, publish_dir / path.name)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    payload = load_payload(args.data)
    desktop = Path(args.desktop)
    mobile = Path(args.mobile)

    render_file(desktop, payload, mobile=False)
    render_file(mobile, payload, mobile=True)

    if args.publish_dir:
        publish([desktop, mobile], Path(args.publish_dir))


if __name__ == "__main__":
    main()
