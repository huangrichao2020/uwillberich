#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HEADERS = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
LIST_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/get"
MANAGE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/manage"
RUNTIME_ENV_CANDIDATES = (
    Path.home() / ".uwillberich" / "runtime.env",
    Path.home() / ".a-share-decision-desk" / "runtime.env",
    ROOT / ".env.local",
    ROOT / ".env",
)


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return parse_env_text(path.read_text(encoding="utf-8"))


def load_api_key() -> tuple[str, str]:
    env_key = (os.environ.get("MX_APIKEY") or os.environ.get("EM_API_KEY") or "").strip()
    if env_key:
        return env_key, "environment"
    for path in RUNTIME_ENV_CANDIDATES:
        values = read_env_file(path)
        file_key = (values.get("MX_APIKEY") or values.get("EM_API_KEY") or "").strip()
        if file_key:
            os.environ.setdefault("MX_APIKEY", file_key)
            os.environ.setdefault("EM_API_KEY", file_key)
            return file_key, str(path)
    raise RuntimeError(
        "MX_APIKEY or EM_API_KEY is required for mx_selfselect. "
        "Apply at https://ai.eastmoney.com/mxClaw and store it in ~/.uwillberich/runtime.env or your environment."
    )


def redact_value(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def post_json(url: str, payload: dict | None = None, timeout: int = 20) -> dict:
    api_key, _ = load_api_key()
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={**DEFAULT_HEADERS, "apikey": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed: {exc}") from exc
    return json.loads(raw)


def list_watchlist() -> dict:
    return post_json(LIST_URL)


def manage_watchlist(query: str) -> dict:
    return post_json(MANAGE_URL, payload={"query": query})


def extract_list_rows(payload: dict) -> tuple[list[str], list[dict]]:
    result = (
        payload.get("data", {})
        .get("allResults", {})
        .get("result", {})
    )
    columns = result.get("columns", [])
    rows = result.get("dataList", [])
    visible_columns = [col for col in columns if not col.get("hide")]
    prioritized_keys = [
        "SECURITY_CODE",
        "SECURITY_SHORT_NAME",
        "MARKET_SHORT_NAME",
        "NEWEST_PRICE",
        "CHG",
        "PCHG",
    ]
    keys: list[str] = []
    for key in prioritized_keys:
        if any(col.get("key") == key for col in visible_columns):
            keys.append(key)
    for col in visible_columns:
        key = col.get("key")
        if key and key not in keys:
            keys.append(key)
    return keys, rows


def to_markdown_table(rows: list[dict], keys: list[str], max_rows: int = 20) -> str:
    if not rows or not keys:
        return "- 当前未返回自选股明细，请到东方财富 App 核对。"
    header_names = {
        "SECURITY_CODE": "代码",
        "SECURITY_SHORT_NAME": "名称",
        "MARKET_SHORT_NAME": "市场",
        "NEWEST_PRICE": "最新价",
        "CHG": "涨跌幅",
        "PCHG": "涨跌额",
    }
    display_keys = keys[: min(len(keys), 6)]
    header = "| " + " | ".join(header_names.get(key, key) for key in display_keys) + " |"
    sep = "| " + " | ".join(["---"] * len(display_keys)) + " |"
    body: list[str] = []
    for row in rows[:max_rows]:
        values = []
        for key in display_keys:
            values.append(str(row.get(key, "")).replace("|", "\\|").replace("\n", " "))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, sep, *body])


def render_list_markdown(payload: dict) -> str:
    status = payload.get("status")
    message = payload.get("message")
    title = payload.get("data", {}).get("title") or "我的自选"
    keys, rows = extract_list_rows(payload)
    lines = [
        f"# {title}",
        "",
        f"- status: `{status}`",
        f"- message: `{message}`",
        f"- count: `{len(rows)}`",
        "",
        to_markdown_table(rows, keys),
    ]
    if not rows:
        lines.extend(["", "- 当前接口返回空列表，请到东方财富 App 查询。"])
    return "\n".join(lines).rstrip() + "\n"


def render_manage_markdown(query: str, payload: dict) -> str:
    lines = [
        "# 自选股操作结果",
        "",
        f"- query: `{query}`",
        f"- status: `{payload.get('status')}`",
        f"- code: `{payload.get('code')}`",
        f"- message: `{payload.get('message')}`",
    ]
    if payload.get("data") is not None:
        lines.extend(["", "```json", json.dumps(payload.get("data"), ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines).rstrip() + "\n"


def command_status(args: argparse.Namespace) -> int:
    api_key, source = load_api_key()
    payload = {"configured": True, "source": source, "redacted_api_key": redact_value(api_key)}
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"configured: {payload['configured']}")
        print(f"source: {payload['source']}")
        print(f"api_key: {payload['redacted_api_key']}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    payload = list_watchlist()
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_list_markdown(payload))
    return 0


def command_manage(args: argparse.Namespace) -> int:
    payload = manage_watchlist(args.query)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_manage_markdown(args.query, payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Eastmoney self-select list management.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show API key status.")
    status_parser.add_argument("--format", choices=["text", "json"], default="text")
    status_parser.set_defaults(func=command_status)

    list_parser = subparsers.add_parser("list", help="Query the current self-select list.")
    list_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    list_parser.set_defaults(func=command_list)

    manage_parser = subparsers.add_parser("manage", help="Send a natural-language watchlist mutation request.")
    manage_parser.add_argument("--query", required=True, help="Natural-language query, for example 把东方财富加入自选")
    manage_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    manage_parser.set_defaults(func=command_manage)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"mx_selfselect failed: {exc}", file=sys.stderr)
        raise
