#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from runtime_config import DEFAULT_RUNTIME_HOME, build_status


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
DEFAULT_MEMORY_HOME = DEFAULT_RUNTIME_HOME / "memory"
LEGACY_MEMORY_HOME = Path.home() / ".a-share-decision-desk" / "memory"
DEFAULT_HANDOFF_DIR = DEFAULT_MEMORY_HOME / "handoff"
DEFAULT_HANDOFF_PATH = DEFAULT_HANDOFF_DIR / "latest.md"
DEFAULT_LOG_DIR = DEFAULT_MEMORY_HOME / "logs"
DEFAULT_DB_PATH = DEFAULT_MEMORY_HOME / "memory.sqlite3"
DEFAULT_SEED_PATH = ROOT / "assets" / "memory_seed.json"
MEMORY_HOME_ENV_VARS = ("UWILLBERICH_MEMORY_HOME",)
DEFAULT_ACTIVE_WINDOW_MINUTES = 60
DEFAULT_RECENT_LIMIT = 12
VALID_ROLES = {"user", "assistant", "system"}
FACT_SCOPE_ORDER = ("user", "project", "policy", "workflow", "environment", "open_item")


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def parse_iso8601(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def resolve_memory_home(memory_home: str | None = None) -> Path:
    if memory_home:
        return Path(memory_home).expanduser()
    for env_var in MEMORY_HOME_ENV_VARS:
        raw_value = (os.environ.get(env_var) or "").strip()
        if raw_value:
            return Path(raw_value).expanduser()
    if DEFAULT_MEMORY_HOME.exists() or not LEGACY_MEMORY_HOME.exists():
        return DEFAULT_MEMORY_HOME
    return LEGACY_MEMORY_HOME


def db_path(memory_home: Path) -> Path:
    return memory_home / "memory.sqlite3"


def handoff_path(memory_home: Path) -> Path:
    return memory_home / "handoff" / "latest.md"


def ensure_memory_home(memory_home: Path) -> None:
    memory_home.mkdir(parents=True, exist_ok=True)
    (memory_home / "handoff").mkdir(parents=True, exist_ok=True)
    (memory_home / "logs").mkdir(parents=True, exist_ok=True)


def open_db(memory_home: Path) -> sqlite3.Connection:
    ensure_memory_home(memory_home)
    conn = sqlite3.connect(db_path(memory_home))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS facts (
            scope TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (scope, key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            summary TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS handoff_runs (
            handoff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated INTEGER NOT NULL,
            reason TEXT NOT NULL,
            output_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    seed_defaults(conn)
    return conn


def seed_defaults(conn: sqlite3.Connection) -> None:
    if not DEFAULT_SEED_PATH.exists():
        return
    payload = json.loads(DEFAULT_SEED_PATH.read_text(encoding="utf-8"))
    timestamp = now_utc()
    for scope, mapping in payload.items():
        if not isinstance(mapping, dict):
            continue
        for key, value in mapping.items():
            conn.execute(
                "INSERT OR IGNORE INTO facts (scope, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (scope, key, str(value), timestamp),
            )
    conn.commit()


def upsert_fact(conn: sqlite3.Connection, scope: str, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO facts (scope, key, value, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(scope, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (scope, key, value, now_utc()),
    )
    conn.commit()


def delete_fact(conn: sqlite3.Connection, scope: str, key: str) -> None:
    conn.execute("DELETE FROM facts WHERE scope = ? AND key = ?", (scope, key))
    conn.commit()


def list_facts(conn: sqlite3.Connection, scope: str | None = None) -> list[dict]:
    query = "SELECT scope, key, value, updated_at FROM facts"
    params: tuple[str, ...] = ()
    if scope:
        query += " WHERE scope = ?"
        params = (scope,)
    query += " ORDER BY scope, key"
    rows = conn.execute(query, params).fetchall()
    return [
        {"scope": row[0], "key": row[1], "value": row[2], "updated_at": row[3]}
        for row in rows
    ]


def record_interaction(
    conn: sqlite3.Connection,
    role: str,
    summary: str,
    details: str = "",
    tags: list[str] | None = None,
) -> None:
    normalized_role = role.strip().lower()
    if normalized_role not in VALID_ROLES:
        raise ValueError(f"unsupported role: {role}")
    conn.execute(
        """
        INSERT INTO interactions (role, summary, details, tags_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (normalized_role, summary.strip(), details.strip(), json.dumps(tags or [], ensure_ascii=False), now_utc()),
    )
    conn.commit()


def latest_interaction_at(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT created_at FROM interactions ORDER BY created_at DESC, interaction_id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else ""


def latest_handoff_at(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT created_at
        FROM handoff_runs
        WHERE generated = 1
        ORDER BY created_at DESC, handoff_id DESC
        LIMIT 1
        """
    ).fetchone()
    return row[0] if row else ""


def recent_interactions(conn: sqlite3.Connection, limit: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT role, summary, details, tags_json, created_at
        FROM interactions
        ORDER BY created_at DESC, interaction_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "role": row[0],
                "summary": row[1],
                "details": row[2],
                "tags": json.loads(row[3] or "[]"),
                "created_at": row[4],
            }
        )
    return result


def record_handoff_run(conn: sqlite3.Connection, generated: bool, reason: str, output_path_value: Path) -> None:
    conn.execute(
        """
        INSERT INTO handoff_runs (generated, reason, output_path, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (1 if generated else 0, reason, str(output_path_value), now_utc()),
    )
    conn.commit()


def safe_git_summary(repo_path: Path) -> dict:
    if not repo_path.exists() or not (repo_path / ".git").exists():
        return {
            "path": str(repo_path),
            "exists": False,
            "branch": "",
            "status": "missing",
            "origin": "",
        }
    status = subprocess.run(
        ["git", "-C", str(repo_path), "status", "-sb"],
        text=True,
        capture_output=True,
        check=False,
    )
    first_line = status.stdout.strip().splitlines()[0] if status.stdout.strip() else ""
    origin = subprocess.run(
        ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "path": str(repo_path),
        "exists": True,
        "branch": first_line,
        "status": "clean" if status.returncode == 0 else "unknown",
        "origin": origin.stdout.strip(),
    }


def candidate_repos() -> list[Path]:
    repos = [REPO_ROOT, REPO_ROOT.parent / "uwillberich-reports"]
    deduped: list[Path] = []
    seen: set[str] = set()
    for repo_path in repos:
        resolved = str(repo_path)
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(repo_path)
    return deduped


def grouped_facts(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in list_facts(conn):
        groups.setdefault(item["scope"], []).append(item)
    return groups


def render_facts_markdown(groups: dict[str, list[dict]]) -> list[str]:
    lines: list[str] = []
    ordered_scopes = list(FACT_SCOPE_ORDER) + sorted(scope for scope in groups if scope not in FACT_SCOPE_ORDER)
    for scope in ordered_scopes:
        items = groups.get(scope, [])
        if not items:
            continue
        lines.append(f"### {scope}")
        lines.append("")
        for item in items:
            lines.append(f"- `{item['key']}`: {item['value']}")
        lines.append("")
    return lines


def render_repo_markdown() -> list[str]:
    lines = ["## Workspace State", ""]
    for repo_path in candidate_repos():
        summary = safe_git_summary(repo_path)
        if not summary["exists"]:
            continue
        lines.append(f"- `{summary['path']}`")
        lines.append(f"  status: `{summary['branch'] or 'unknown'}`")
        if summary["origin"]:
            lines.append(f"  origin: `{summary['origin']}`")
    lines.append("")
    return lines


def render_runtime_markdown(memory_home: Path) -> list[str]:
    lines = ["## Runtime State", ""]
    try:
        status = build_status()
        lines.append(f"- runtime env: `{status['runtime_env_path']}`")
        lines.append(f"- output root: `{status['output_root']}`")
    except Exception as exc:
        lines.append(f"- runtime status error: `{exc}`")
    lines.append(f"- memory home: `{memory_home}`")
    lines.append(f"- handoff doc: `{handoff_path(memory_home)}`")
    lines.append(f"- news iterator state: `{DEFAULT_RUNTIME_HOME / 'news-iterator'}`")
    lines.append(
        f"- handoff updater plist: `{Path.home() / 'Library' / 'LaunchAgents' / 'com.tingchi.uwillberich-handoff-updater.plist'}`"
    )
    lines.append("")
    return lines


def render_recent_interactions_markdown(items: list[dict]) -> list[str]:
    lines = ["## Recent Interactions", ""]
    if not items:
        lines.append("- none")
        lines.append("")
        return lines
    for item in items:
        lines.append(f"- `{item['created_at']}` `{item['role']}`: {item['summary']}")
        if item["details"]:
            lines.append(f"  details: {item['details']}")
        if item["tags"]:
            lines.append(f"  tags: `{', '.join(item['tags'])}`")
    lines.append("")
    return lines


def render_open_items_markdown(groups: dict[str, list[dict]]) -> list[str]:
    lines = ["## Open Items", ""]
    items = groups.get("open_item", [])
    if not items:
        lines.append("- none")
        lines.append("")
        return lines
    for item in items:
        lines.append(f"- `{item['key']}`: {item['value']}")
    lines.append("")
    return lines


def should_generate_handoff(conn: sqlite3.Connection, active_window_minutes: int, force: bool) -> tuple[bool, str]:
    if force:
        return True, "forced"
    last_interaction = parse_iso8601(latest_interaction_at(conn))
    if not last_interaction:
        return False, "no interactions recorded"
    cutoff = datetime.now(UTC) - timedelta(minutes=active_window_minutes)
    if last_interaction < cutoff:
        return False, f"idle for more than {active_window_minutes} minutes"
    return True, "active window"


def generate_handoff_document(
    conn: sqlite3.Connection,
    memory_home: Path,
    output_path: Path,
    active_window_minutes: int,
    recent_limit: int,
    force: bool,
) -> dict[str, object]:
    should_generate, reason = should_generate_handoff(conn, active_window_minutes, force)
    if not should_generate:
        record_handoff_run(conn, False, reason, output_path)
        return {"generated": False, "reason": reason, "output_path": str(output_path)}

    content = build_handoff_content(conn, memory_home, recent_limit, active_window_minutes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    record_handoff_run(conn, True, reason, output_path)
    return {"generated": True, "reason": reason, "output_path": str(output_path)}


def build_handoff_content(conn: sqlite3.Connection, memory_home: Path, recent_limit: int, active_window_minutes: int) -> str:
    latest_interaction = latest_interaction_at(conn) or "none"
    latest_handoff = latest_handoff_at(conn) or "none"
    recent_items = recent_interactions(conn, recent_limit)
    facts = grouped_facts(conn)

    lines = [
        "# uwillberich Handoff",
        "",
        f"- Generated: `{now_utc()}`",
        f"- Last interaction: `{latest_interaction}`",
        f"- Last generated handoff: `{latest_handoff}`",
        f"- Update policy: refresh hourly only when dialogue activity exists within the last `{active_window_minutes}` minutes",
        "",
        "## Stable Memory",
        "",
    ]
    lines.extend(render_facts_markdown(facts))
    lines.extend(render_open_items_markdown(facts))
    lines.extend(render_recent_interactions_markdown(recent_items))
    lines.extend(render_repo_markdown())
    lines.extend(render_runtime_markdown(memory_home))
    return "\n".join(lines).rstrip() + "\n"


def build_status_payload(conn: sqlite3.Connection, memory_home: Path) -> dict[str, object]:
    return {
        "memory_home": str(memory_home),
        "db_path": str(db_path(memory_home)),
        "handoff_path": str(handoff_path(memory_home)),
        "last_interaction_at": latest_interaction_at(conn),
        "last_handoff_at": latest_handoff_at(conn),
        "fact_count": conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
        "interaction_count": conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0],
        "handoff_refresh_minutes": DEFAULT_ACTIVE_WINDOW_MINUTES,
    }


def parse_tags(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def command_status(args: argparse.Namespace) -> int:
    memory_home = resolve_memory_home(args.memory_home)
    with open_db(memory_home) as conn:
        payload = build_status_payload(conn, memory_home)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0


def command_touch(args: argparse.Namespace) -> int:
    memory_home = resolve_memory_home(args.memory_home)
    with open_db(memory_home) as conn:
        record_interaction(conn, args.role, args.summary, args.details or "", parse_tags(args.tags or ""))
    print(f"recorded_interaction: {args.role}")
    print(f"memory_home: {memory_home}")
    return 0


def command_remember(args: argparse.Namespace) -> int:
    memory_home = resolve_memory_home(args.memory_home)
    with open_db(memory_home) as conn:
        upsert_fact(conn, args.scope, args.key, args.value)
    print(f"stored_fact: {args.scope}.{args.key}")
    return 0


def command_forget(args: argparse.Namespace) -> int:
    memory_home = resolve_memory_home(args.memory_home)
    with open_db(memory_home) as conn:
        delete_fact(conn, args.scope, args.key)
    print(f"removed_fact: {args.scope}.{args.key}")
    return 0


def command_list_facts(args: argparse.Namespace) -> int:
    memory_home = resolve_memory_home(args.memory_home)
    with open_db(memory_home) as conn:
        payload = list_facts(conn, args.scope)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in payload:
            print(f"{item['scope']}.{item['key']}={item['value']} ({item['updated_at']})")
    return 0


def command_build_handoff(args: argparse.Namespace) -> int:
    memory_home = resolve_memory_home(args.memory_home)
    output_path = Path(args.output_path).expanduser() if args.output_path else handoff_path(memory_home)
    with open_db(memory_home) as conn:
        result = generate_handoff_document(
            conn,
            memory_home,
            output_path,
            args.active_window_minutes,
            args.recent_limit,
            args.force,
        )
    if not result["generated"]:
        print(f"skipped: {result['reason']}")
        print(f"handoff_path: {output_path}")
        return 0
    print(f"generated: {output_path}")
    print(f"reason: {result['reason']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persistent memory and handoff manager for uwillberich.")
    parser.add_argument("--memory-home", help="Memory home directory. Defaults to ~/.uwillberich/memory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show memory-layer status.")
    status_parser.add_argument("--json", action="store_true", help="Render as JSON.")
    status_parser.set_defaults(func=command_status)

    touch_parser = subparsers.add_parser("touch", help="Record a dialogue interaction.")
    touch_parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES), help="Interaction role.")
    touch_parser.add_argument("--summary", required=True, help="Short summary for the interaction.")
    touch_parser.add_argument("--details", help="Optional longer details.")
    touch_parser.add_argument("--tags", help="Comma-separated tags.")
    touch_parser.set_defaults(func=command_touch)

    remember_parser = subparsers.add_parser("remember", help="Store or update a persistent fact.")
    remember_parser.add_argument("--scope", required=True, help="Fact scope, for example user or open_item.")
    remember_parser.add_argument("--key", required=True, help="Fact key.")
    remember_parser.add_argument("--value", required=True, help="Fact value.")
    remember_parser.set_defaults(func=command_remember)

    forget_parser = subparsers.add_parser("forget", help="Delete a stored fact.")
    forget_parser.add_argument("--scope", required=True, help="Fact scope.")
    forget_parser.add_argument("--key", required=True, help="Fact key.")
    forget_parser.set_defaults(func=command_forget)

    list_parser = subparsers.add_parser("list-facts", help="List stored facts.")
    list_parser.add_argument("--scope", help="Optional scope filter.")
    list_parser.add_argument("--json", action="store_true", help="Render as JSON.")
    list_parser.set_defaults(func=command_list_facts)

    handoff_parser = subparsers.add_parser("build-handoff", help="Generate the latest handoff document.")
    handoff_parser.add_argument("--output-path", help="Custom handoff output path.")
    handoff_parser.add_argument(
        "--active-window-minutes",
        type=int,
        default=DEFAULT_ACTIVE_WINDOW_MINUTES,
        help="Only update when an interaction exists within this window unless --force is set.",
    )
    handoff_parser.add_argument(
        "--recent-limit",
        type=int,
        default=DEFAULT_RECENT_LIMIT,
        help="Number of recent interactions to include in the handoff.",
    )
    handoff_parser.add_argument("--force", action="store_true", help="Generate even when the conversation is stale.")
    handoff_parser.set_defaults(func=command_build_handoff)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
