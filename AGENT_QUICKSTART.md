# Agent Quickstart

This repo is designed so another agent can take the GitHub URL and use it with minimal setup.

## Repo

```text
https://github.com/huangrichao2020/a-share-decision-kit
```

## What To Install

The only folder an agent needs is:

```text
skill/a-share-decision-desk
```

Install it into one of these locations:

- `~/.codex/skills/a-share-decision-desk`
- `~/.openclaw/skills/a-share-decision-desk`

Example:

```bash
git clone https://github.com/huangrichao2020/a-share-decision-kit.git
mkdir -p ~/.codex/skills
cp -R a-share-decision-kit/skill/a-share-decision-desk ~/.codex/skills/a-share-decision-desk
```

One-line install for Codex:

```bash
git clone https://github.com/huangrichao2020/a-share-decision-kit.git && cd a-share-decision-kit && ./install_skill.sh
```

One-line install for OpenClaw:

```bash
git clone https://github.com/huangrichao2020/a-share-decision-kit.git && cd a-share-decision-kit && ./install_skill.sh openclaw
```

## What The Skill Can Do

- build A-share morning briefs
- build opening-window checklists
- poll public news continuously
- convert high-attention news into event-driven stock pools
- append those event pools automatically to the brief and checklist

## Required Keys

Project-specific runtime keys: `none`

The repo uses only:

- Python standard library
- public RSS feeds
- public Tencent quote endpoints
- public Eastmoney endpoints

## Optional Credentials

- GitHub PAT or SSH key with read access:
  needed only if the repo is private and the agent must clone it directly
- GitHub PAT or SSH key with write access:
  needed only if the agent should push changes back
- Model-provider API keys:
  may be needed by the host agent platform, but not by this repo itself

## First Run

```bash
python3 ~/.codex/skills/a-share-decision-desk/scripts/smoke_test.py
python3 ~/.codex/skills/a-share-decision-desk/scripts/news_iterator.py poll
python3 ~/.codex/skills/a-share-decision-desk/scripts/morning_brief.py
python3 ~/.codex/skills/a-share-decision-desk/scripts/opening_window_checklist.py
```

## Long-Running News Iterator

On macOS:

```bash
python3 ~/.codex/skills/a-share-decision-desk/scripts/install_news_iterator_launchd.py install --interval-seconds 300
```

On Linux or other environments:

```bash
nohup python3 ~/.codex/skills/a-share-decision-desk/scripts/news_iterator.py loop --interval-seconds 300 > ~/a-share-news-iterator.log 2>&1 &
```

## Output State

By default the iterator writes to:

```text
~/.a-share-decision-desk/news-iterator/
```

Important files:

- `latest_alerts.md`
- `alerts.jsonl`
- `event_watchlists.json`
- `news_iterator.sqlite3`
