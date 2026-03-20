# A-Share Decision Kit

Reusable materials for a discretionary A-share decision workflow:

- `prompts/persona-prompt.md`: decision-maker persona prompt
- `prompts/trading-mode-prompt.md`: daily execution-mode prompt
- `skill/a-share-decision-desk/`: installable Codex skill
- `AGENT_QUICKSTART.md`: zero-to-run instructions for other agents

## Workflow Map

The repo is organized around a direct desk workflow instead of disconnected tools:

1. `Step 1: Overnight and policy scan`
   - `news_iterator.py`
   - `mx_toolkit.py preset --name preopen_policy`
   - `mx_toolkit.py preset --name preopen_global_risk`
2. `Step 2: Board resonance and candidate narrowing`
   - `fetch_market_snapshot.py`
   - `morning_brief.py`
   - `capital_flow.py`
   - `market_sentiment.py`
   - `mx_toolkit.py preset --name board_optical_module`
   - `mx_toolkit.py preset --name board_compute_power`
3. `Step 3: Structured validation on key names`
   - `fetch_quotes.py`
   - `mx_toolkit.py preset --name validate_inspur`
   - `mx_toolkit.py preset --name validate_luxshare`
4. `Step 4: Chain expansion and event overlays`
   - `industry_chain.py`
   - `news_iterator.py`
   - `opening_window_checklist.py`
5. `Source health check`
   - `benchmark_sources.py`

## GitHub Source Of Truth

Use the GitHub repo as the primary distribution source:

```bash
https://github.com/huangrichao2020/a-share-decision-kit
```

Agents only need the skill folder:

```bash
skill/a-share-decision-desk
```

## Quick Install For Agents

Clone or copy the repo, then place the skill folder into your local skill directory:

```bash
mkdir -p ~/.codex/skills
cp -R skill/a-share-decision-desk ~/.codex/skills/a-share-decision-desk
```

OpenClaw users can do the same with `~/.openclaw/skills/`.

One-line install from GitHub:

```bash
git clone https://github.com/huangrichao2020/a-share-decision-kit.git && cd a-share-decision-kit && ./install_skill.sh
```

For OpenClaw:

```bash
git clone https://github.com/huangrichao2020/a-share-decision-kit.git && cd a-share-decision-kit && ./install_skill.sh openclaw
```

## Runtime Keys

This repo hard-requires `EM_API_KEY`.

- Apply here:
  `https://ai.eastmoney.com/mxClaw`
- After opening the link, click download and you will see the key.
- Official site:
  `https://ai.eastmoney.com/nlink/`
- Store it locally in `~/.a-share-decision-desk/runtime.env`, not in Git.
- Use the bundled helper:

```bash
python3 skill/a-share-decision-desk/scripts/runtime_config.py status
printf '%s' 'your_em_api_key' | python3 skill/a-share-decision-desk/scripts/runtime_config.py set-em-key --stdin
```

Without `EM_API_KEY`, the desk scripts will stop and print the application URL plus setup command.

## Optional Credentials

- `GitHub read access`
  - Needed only if the repo is private and another agent wants to clone it directly.
  - Use either a GitHub PAT with `repo` read access or an SSH key with repo access.
- `GitHub write access`
  - Needed only if another agent should push changes back.
  - Use either a PAT with write access or an SSH key with write access.
- `OpenAI` or other model-provider API keys
  - Not required by this repo itself.
  - They may still be required by the agent platform running the skill.

## Included Scripts

All scripts live under `skill/a-share-decision-desk/scripts/` and use only the Python standard library.

- `install_skill.sh`: one-command installer for Codex/OpenClaw skill directories
- `runtime_config.py`: local runtime credential loader and required `EM_API_KEY` helper
- `mx_api.py`: Meixiang / Eastmoney API wrapper for news search, stock screen, and structured data queries
- `mx_toolkit.py`: CLI wrapper for real MX calls, presets, and artifact outputs
- `benchmark_sources.py`: public-source and MX-source latency / availability benchmark
- `capital_flow.py`: main-force inflow/outflow monitor plus watchlist resonance scoreboard
- `market_sentiment.py`: breadth + capital-flow + board-structure sentiment snapshot
- `industry_chain.py`: event-aware industry-chain expansion that turns themes into stock pools
- `fetch_quotes.py`: fetch Tencent quote snapshots for a watchlist
- `fetch_market_snapshot.py`: fetch Eastmoney index and sector breadth snapshots
- `morning_brief.py`: build a simple pre-open markdown brief from default watchlists
- `opening_window_checklist.py`: build an opening decision sheet
- `news_iterator.py`: poll public news and auto-build event-driven stock pools
- `install_news_iterator_launchd.py`: install the message iterator as a local macOS job

## Example Usage

```bash
python3 skill/a-share-decision-desk/scripts/fetch_market_snapshot.py --format markdown
python3 skill/a-share-decision-desk/scripts/fetch_quotes.py sz300502 sz300308 sh688981
python3 skill/a-share-decision-desk/scripts/runtime_config.py status
python3 skill/a-share-decision-desk/scripts/mx_toolkit.py list-presets
python3 skill/a-share-decision-desk/scripts/mx_toolkit.py preset --name preopen_repair_chain
python3 skill/a-share-decision-desk/scripts/mx_toolkit.py preset --name flow_main_force
python3 skill/a-share-decision-desk/scripts/mx_toolkit.py news-search --query '立讯精密 最新资讯'
python3 skill/a-share-decision-desk/scripts/mx_toolkit.py stock-screen --keyword 'A股 光模块概念股' --page-size 10 --csv-out /tmp/cpo.csv --desc-out /tmp/cpo-columns.md
python3 skill/a-share-decision-desk/scripts/mx_toolkit.py query --tool-query '浪潮信息 最新价 市值'
python3 skill/a-share-decision-desk/scripts/capital_flow.py --groups tech_repair defensive_gauge
python3 skill/a-share-decision-desk/scripts/market_sentiment.py
python3 skill/a-share-decision-desk/scripts/industry_chain.py --groups tech_repair defensive_gauge
python3 skill/a-share-decision-desk/scripts/benchmark_sources.py
python3 skill/a-share-decision-desk/scripts/morning_brief.py --groups core10 tech_repair
python3 skill/a-share-decision-desk/scripts/news_iterator.py poll
python3 skill/a-share-decision-desk/scripts/morning_brief.py
```

## Notes

- Market endpoints can change or throttle. Use the scripts as fast data collectors, then verify high-stakes conclusions with official or primary news sources.
- Generated benchmark and preset artifacts default to `~/.a-share-decision-desk/data/`.
- On monthly `LPR` days, the workflow assumes the `9:00` release window.
- On macOS, use `install_news_iterator_launchd.py`; on Linux or other environments, use `nohup` or the local scheduler of your choice.
