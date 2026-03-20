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
REPO_ROOT = ROOT.parents[1]
DEFAULT_HEADERS = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
LIST_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/get"
MANAGE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/manage"
DEFAULT_EVENT_WATCHLIST = Path.home() / ".uwillberich" / "news-iterator" / "event_watchlists.json"
RUNTIME_ENV_CANDIDATES = (
    Path.home() / ".uwillberich" / "runtime.env",
    Path.home() / ".a-share-decision-desk" / "runtime.env",
    ROOT / ".env.local",
    ROOT / ".env",
)


def candidate_watchlist_paths() -> list[Path]:
    candidates = [
        REPO_ROOT / "skill" / "uwillberich" / "assets" / "default_watchlists.json",
        ROOT.parent / "uwillberich" / "assets" / "default_watchlists.json",
    ]
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        resolved = str(path.expanduser())
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(Path(resolved))
    return deduped


def resolve_default_watchlist_path() -> Path:
    for path in candidate_watchlist_paths():
        if path.exists():
            return path
    return candidate_watchlist_paths()[0]


DEFAULT_UWILLBERICH_WATCHLIST = resolve_default_watchlist_path()


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


def load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_payload_data(payload: dict) -> dict:
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def extract_list_rows(payload: dict) -> tuple[list[str], list[dict]]:
    result = (
        get_payload_data(payload)
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


def build_current_lookup(rows: list[dict]) -> tuple[set[str], set[str]]:
    current_names = {str(row.get("SECURITY_SHORT_NAME") or "").strip() for row in rows if row.get("SECURITY_SHORT_NAME")}
    current_codes = {str(row.get("SECURITY_CODE") or "").strip() for row in rows if row.get("SECURITY_CODE")}
    return current_names, current_codes


def collect_group_items(
    groups: list[str],
    watchlist_path: Path,
    event_watchlist_path: Path,
) -> tuple[list[dict], list[str]]:
    watchlists = load_json_file(watchlist_path)
    event_payload = load_json_file(event_watchlist_path)
    event_groups = event_payload.get("groups", {}) if isinstance(event_payload, dict) else {}
    selected: list[dict] = []
    missing: list[str] = []

    for group in groups:
        if group in watchlists:
            selected.extend(watchlists[group])
            continue
        if group in event_groups:
            selected.extend(event_groups[group])
            continue
        missing.append(group)

    deduped: list[dict] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()
    for item in selected:
        code = str(item.get("symbol", ""))[2:] if item.get("symbol") else ""
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if code and code in seen_codes:
            continue
        if not code and name in seen_names:
            continue
        if code:
            seen_codes.add(code)
        seen_names.add(name)
        deduped.append(item)
    return deduped, missing


def plan_sync(
    groups: list[str],
    watchlist_path: Path,
    event_watchlist_path: Path,
    limit: int | None = None,
) -> dict:
    target_items, missing_groups = collect_group_items(groups, watchlist_path, event_watchlist_path)
    if limit is not None and limit > 0:
        target_items = target_items[:limit]
    current_payload = list_watchlist()
    _, current_rows = extract_list_rows(current_payload)
    current_names, current_codes = build_current_lookup(current_rows)

    to_add: list[dict] = []
    already_present: list[dict] = []
    for item in target_items:
        code = str(item.get("symbol", ""))[2:] if item.get("symbol") else ""
        name = str(item.get("name") or "").strip()
        if code and code in current_codes:
            already_present.append(item)
        elif name and name in current_names:
            already_present.append(item)
        else:
            to_add.append(item)

    return {
        "groups": groups,
        "missing_groups": missing_groups,
        "target_items": target_items,
        "current_payload": current_payload,
        "to_add": to_add,
        "already_present": already_present,
    }


def run_sync(plan: dict) -> list[dict]:
    results: list[dict] = []
    for item in plan["to_add"]:
        name = str(item.get("name") or "").strip()
        query = f"把{name}加入自选"
        payload = manage_watchlist(query)
        results.append(
            {
                "name": name,
                "symbol": item.get("symbol", ""),
                "query": query,
                "status": payload.get("status"),
                "code": payload.get("code"),
                "message": payload.get("message"),
            }
        )
    return results


def render_sync_markdown(plan: dict, sync_results: list[dict] | None = None, dry_run: bool = False) -> str:
    lines = [
        "# 自选股同步结果",
        "",
        f"- groups: `{', '.join(plan['groups'])}`",
        f"- target_count: `{len(plan['target_items'])}`",
        f"- already_present: `{len(plan['already_present'])}`",
        f"- to_add: `{len(plan['to_add'])}`",
        f"- mode: `{'dry-run' if dry_run else 'apply'}`",
    ]
    if plan["missing_groups"]:
        lines.append(f"- missing_groups: `{', '.join(plan['missing_groups'])}`")

    if plan["to_add"]:
        lines.extend(["", "## 待加入列表", ""])
        for index, item in enumerate(plan["to_add"], start=1):
            lines.append(f"{index}. `{item.get('name')}` `{item.get('symbol', '')}`")

    if plan["already_present"]:
        lines.extend(["", "## 已存在", ""])
        for index, item in enumerate(plan["already_present"][:20], start=1):
            lines.append(f"{index}. `{item.get('name')}` `{item.get('symbol', '')}`")
        if len(plan["already_present"]) > 20:
            lines.append(f"- 其余 `{len(plan['already_present']) - 20}` 只已省略")

    if sync_results is not None:
        lines.extend(["", "## 实际执行结果", ""])
        for result in sync_results:
            lines.append(
                f"- `{result['name']}`: status=`{result['status']}` code=`{result['code']}` message=`{result['message']}`"
            )

    return "\n".join(lines).rstrip() + "\n"


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
    title = get_payload_data(payload).get("title") or "我的自选"
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
    if str(status) == "112":
        lines.extend(["", "- 接口当前提示请求频率过高，请稍后再试。"])
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


def command_sync_groups(args: argparse.Namespace) -> int:
    plan = plan_sync(
        groups=args.groups,
        watchlist_path=Path(args.watchlist).expanduser(),
        event_watchlist_path=Path(args.event_watchlist).expanduser(),
        limit=args.limit,
    )
    sync_results: list[dict] | None = None
    if not args.dry_run:
        sync_results = run_sync(plan)
    payload = {
        "groups": plan["groups"],
        "missing_groups": plan["missing_groups"],
        "target_count": len(plan["target_items"]),
        "already_present_count": len(plan["already_present"]),
        "to_add_count": len(plan["to_add"]),
        "to_add": plan["to_add"],
        "already_present": plan["already_present"],
        "sync_results": sync_results or [],
        "mode": "dry-run" if args.dry_run else "apply",
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_sync_markdown(plan, sync_results=sync_results, dry_run=args.dry_run))
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

    sync_parser = subparsers.add_parser(
        "sync-groups",
        help="Sync selected uwillberich watchlist groups into Eastmoney self-select. Defaults to add-only behavior.",
    )
    sync_parser.add_argument("--groups", nargs="+", required=True, help="uwillberich watchlist or event-pool groups.")
    sync_parser.add_argument("--watchlist", default=str(DEFAULT_UWILLBERICH_WATCHLIST), help="Path to uwillberich default watchlists.")
    sync_parser.add_argument(
        "--event-watchlist",
        default=str(DEFAULT_EVENT_WATCHLIST),
        help="Path to uwillberich dynamic event watchlists.",
    )
    sync_parser.add_argument("--limit", type=int, help="Only sync the first N deduped names.")
    sync_parser.add_argument("--dry-run", action="store_true", help="Preview adds without mutating Eastmoney self-select.")
    sync_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    sync_parser.set_defaults(func=command_sync_groups)

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
