# Agent Quickstart

This repo is designed so another agent can take the GitHub URL and use it with minimal setup.

## Repo

```text
https://github.com/huangrichao2020/uwillberich
```

## What To Install

The only folder an agent needs is:

```text
skill/uwillberich
```

Install it into one of these locations:

- `~/.codex/skills/uwillberich`
- `~/.openclaw/skills/uwillberich`

Example:

```bash
git clone https://github.com/huangrichao2020/uwillberich.git
mkdir -p ~/.codex/skills
cp -R uwillberich/skill/uwillberich ~/.codex/skills/uwillberich
```

One-line install for Codex:

```bash
git clone https://github.com/huangrichao2020/uwillberich.git && cd uwillberich && ./install_skill.sh
```

One-line install for OpenClaw:

```bash
git clone https://github.com/huangrichao2020/uwillberich.git && cd uwillberich && ./install_skill.sh openclaw
```

## What The Skill Can Do

- build A-share morning briefs
- build opening-window checklists
- poll public news continuously
- convert high-attention news into event-driven stock pools
- expand those pools into industry-chain watchlists
- score the tape with breadth + capital-flow sentiment
- cross-check watchlists against main-force inflow and outflow lists
- append those event pools automatically to the brief and checklist
- persist stable memory and recent interactions in local SQLite state
- generate a rolling handoff document for the next session or agent
- call Meixiang / Eastmoney live APIs for news search, stock screening, and structured data queries
- run preset desk workflows that map `Step 1 / Step 2 / Step 3` into repeatable commands
- benchmark public and MX sources before assigning a source as primary

## Required Keys

`EM_API_KEY` is required.

- Apply here:
  `https://ai.eastmoney.com/mxClaw`
- After opening the link, click download and you will see the key.
- Official site:
  `https://ai.eastmoney.com/nlink/`
- Recommended local storage path:
  `~/.uwillberich/runtime.env`
- Setup command:

```bash
printf '%s' 'your_em_api_key' | python3 ~/.codex/skills/uwillberich/scripts/runtime_config.py set-em-key --stdin
```

Without `EM_API_KEY`, the skill exits with setup instructions and does not run.

## Optional Credentials

- GitHub PAT or SSH key with read access:
  needed only if the repo is private and the agent must clone it directly
- GitHub PAT or SSH key with write access:
  needed only if the agent should push changes back
- Model-provider API keys:
  may be needed by the host agent platform, but not by this repo itself

## First Run

```bash
python3 ~/.codex/skills/uwillberich/scripts/smoke_test.py
python3 ~/.codex/skills/uwillberich/scripts/runtime_config.py status
python3 ~/.codex/skills/uwillberich/scripts/mx_toolkit.py list-presets
python3 ~/.codex/skills/uwillberich/scripts/mx_toolkit.py preset --name preopen_repair_chain
python3 ~/.codex/skills/uwillberich/scripts/mx_toolkit.py preset --name flow_main_force
python3 ~/.codex/skills/uwillberich/scripts/mx_toolkit.py news-search --query '立讯精密 最新资讯'
python3 ~/.codex/skills/uwillberich/scripts/capital_flow.py --groups tech_repair defensive_gauge
python3 ~/.codex/skills/uwillberich/scripts/market_sentiment.py
python3 ~/.codex/skills/uwillberich/scripts/industry_chain.py --groups tech_repair defensive_gauge
python3 ~/.codex/skills/uwillberich/scripts/benchmark_sources.py
python3 ~/.codex/skills/uwillberich/scripts/news_iterator.py poll
python3 ~/.codex/skills/uwillberich/scripts/morning_brief.py
python3 ~/.codex/skills/uwillberich/scripts/opening_window_checklist.py
python3 ~/.codex/skills/uwillberich/scripts/memory_layer.py status --json
python3 ~/.codex/skills/uwillberich/scripts/memory_layer.py touch --role user --summary 'Asked for a next-session A-share plan'
python3 ~/.codex/skills/uwillberich/scripts/memory_layer.py build-handoff --force
```

## Long-Running News Iterator

On macOS:

```bash
python3 ~/.codex/skills/uwillberich/scripts/install_news_iterator_launchd.py install --interval-seconds 300
```

On Linux or other environments:

```bash
nohup python3 ~/.codex/skills/uwillberich/scripts/news_iterator.py loop --interval-seconds 300 > ~/uwillberich-news-iterator.log 2>&1 &
```

## Hourly Handoff Updater

On macOS:

```bash
python3 ~/.codex/skills/uwillberich/scripts/install_memory_handoff_launchd.py install
```

Behavior:

- updates `~/.uwillberich/memory/handoff/latest.md` every hour
- skips updates when no dialogue activity exists within the last 60 minutes
- reads and writes persistent memory in `~/.uwillberich/memory/`

## Output State

By default the iterator writes to:

```text
~/.uwillberich/news-iterator/
```

Important files:

- `latest_alerts.md`
- `alerts.jsonl`
- `event_watchlists.json`
- `news_iterator.sqlite3`

Generated artifact directories:

- `~/.uwillberich/data/mx-presets/`
- `~/.uwillberich/data/benchmarks/`
- `~/.uwillberich/memory/`
