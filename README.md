# A-Share Decision Kit

Reusable materials for a discretionary A-share decision workflow:

- `prompts/persona-prompt.md`: decision-maker persona prompt
- `prompts/trading-mode-prompt.md`: daily execution-mode prompt
- `skill/a-share-decision-desk/`: installable Codex skill
- `AGENT_QUICKSTART.md`: zero-to-run instructions for other agents

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

Project-specific runtime keys required for public mode: `none`

This repo runs out of the box with:

- public RSS feeds
- public Eastmoney endpoints
- public Tencent quote endpoints
- Python standard library only

Optional enhancement mode:

- `EM_API_KEY`
  - Enables compatibility with the `MX_FinSearch`, `MX_StockPick`, `MX_MacroData`, and `MX_FinData` ecosystem.
  - Store it locally in `~/.a-share-decision-desk/runtime.env`, not in Git.
  - Use the bundled helper:

```bash
python3 skill/a-share-decision-desk/scripts/runtime_config.py status
printf '%s' 'your_em_api_key' | python3 skill/a-share-decision-desk/scripts/runtime_config.py set-em-key --stdin
```

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
- `runtime_config.py`: local runtime credential loader and EM enhancement status helper
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
python3 skill/a-share-decision-desk/scripts/morning_brief.py --groups core10 tech_repair
python3 skill/a-share-decision-desk/scripts/news_iterator.py poll
python3 skill/a-share-decision-desk/scripts/morning_brief.py
```

## Notes

- Market endpoints can change or throttle. Use the scripts as fast data collectors, then verify high-stakes conclusions with official or primary news sources.
- On monthly `LPR` days, the workflow assumes the `9:00` release window.
- On macOS, use `install_news_iterator_launchd.py`; on Linux or other environments, use `nohup` or the local scheduler of your choice.
