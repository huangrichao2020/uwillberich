#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from memory_layer import DEFAULT_ACTIVE_WINDOW_MINUTES, resolve_memory_home


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABEL = "com.tingchi.uwillberich-handoff-updater"
DEFAULT_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{DEFAULT_LABEL}.plist"


def run_command(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def build_plist(
    interval_seconds: int,
    memory_home: Path,
    python_bin: str,
    active_window_minutes: int,
    recent_limit: int,
) -> dict:
    (memory_home / "logs").mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": DEFAULT_LABEL,
        "ProgramArguments": [
            python_bin,
            str(ROOT / "scripts" / "memory_layer.py"),
            "--memory-home",
            str(memory_home),
            "build-handoff",
            "--active-window-minutes",
            str(active_window_minutes),
            "--recent-limit",
            str(recent_limit),
        ],
        "RunAtLoad": True,
        "StartInterval": interval_seconds,
        "WorkingDirectory": str(ROOT),
        "StandardOutPath": str(memory_home / "logs" / "handoff-updater.out.log"),
        "StandardErrorPath": str(memory_home / "logs" / "handoff-updater.err.log"),
    }
    runtime_env_path = os.environ.get("UWILLBERICH_RUNTIME_ENV") or os.environ.get("A_SHARE_RUNTIME_ENV")
    if runtime_env_path:
        plist["EnvironmentVariables"] = {"UWILLBERICH_RUNTIME_ENV": runtime_env_path}
    return plist


def unload_if_present(plist_path: Path) -> None:
    run_command(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)], check=False)


def install(args: argparse.Namespace) -> int:
    plist_path = Path(args.plist_path)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    memory_home = resolve_memory_home(args.memory_home)
    plist = build_plist(
        args.interval_seconds,
        memory_home,
        args.python_bin,
        args.active_window_minutes,
        args.recent_limit,
    )
    with plist_path.open("wb") as handle:
        plistlib.dump(plist, handle)
    unload_if_present(plist_path)
    domain = f"gui/{os.getuid()}"
    run_command(["launchctl", "bootstrap", domain, str(plist_path)], check=True)
    run_command(["launchctl", "kickstart", "-k", f"{domain}/{DEFAULT_LABEL}"], check=False)
    print(f"installed: {plist_path}")
    print(f"memory_home: {memory_home}")
    print(f"interval_seconds: {args.interval_seconds}")
    print(f"active_window_minutes: {args.active_window_minutes}")
    return 0


def uninstall(args: argparse.Namespace) -> int:
    plist_path = Path(args.plist_path)
    if plist_path.exists():
        unload_if_present(plist_path)
        plist_path.unlink()
        print(f"removed: {plist_path}")
    else:
        print(f"not found: {plist_path}")
    return 0


def status(args: argparse.Namespace) -> int:
    plist_path = Path(args.plist_path)
    print(f"plist: {plist_path}")
    print(f"exists: {plist_path.exists()}")
    if not plist_path.exists():
        return 0
    result = run_command(["launchctl", "print", f"gui/{os.getuid()}/{DEFAULT_LABEL}"], check=False)
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(result.stderr.strip() or result.stdout.strip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the hourly handoff updater as a launchd agent on macOS.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install and load the handoff updater.")
    install_parser.add_argument("--memory-home", help="Memory home directory. Defaults to ~/.uwillberich/memory")
    install_parser.add_argument("--interval-seconds", type=int, default=3600, help="Refresh interval in seconds.")
    install_parser.add_argument(
        "--active-window-minutes",
        type=int,
        default=DEFAULT_ACTIVE_WINDOW_MINUTES,
        help="Only refresh when activity exists within this window.",
    )
    install_parser.add_argument("--recent-limit", type=int, default=12, help="Recent interactions included in handoff.")
    install_parser.add_argument("--plist-path", default=str(DEFAULT_PLIST), help="LaunchAgent plist path.")
    install_parser.add_argument("--python-bin", default=sys.executable, help="Python interpreter path.")
    install_parser.set_defaults(func=install)

    uninstall_parser = subparsers.add_parser("uninstall", help="Unload and remove the handoff updater.")
    uninstall_parser.add_argument("--plist-path", default=str(DEFAULT_PLIST), help="LaunchAgent plist path.")
    uninstall_parser.set_defaults(func=uninstall)

    status_parser = subparsers.add_parser("status", help="Show the handoff updater status.")
    status_parser.add_argument("--plist-path", default=str(DEFAULT_PLIST), help="LaunchAgent plist path.")
    status_parser.set_defaults(func=status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
