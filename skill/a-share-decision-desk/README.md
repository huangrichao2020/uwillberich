# A-Share Decision Desk

A ClawHub/OpenClaw-ready skill for next-session A-share discretionary planning.

It is designed for one job: turn today’s tape and overnight developments into a concrete game plan for tomorrow’s open.

GitHub is the main source of truth for installation and updates:

```text
https://github.com/huangrichao2020/a-share-decision-kit
```

## Good Use Cases

- "What is the most likely A-share path tomorrow?"
- "Which sectors are most likely to repair first after today’s selloff?"
- "Give me a `09:00 / 09:25 / 09:30-10:00` opening checklist."
- "Build a watchlist-driven pre-open note for A-shares."
- "Tell me whether this is real repair or just defensive concentration."
- "Use the cross-cycle core stock pool to narrow tomorrow's key observation list."
- "In a war-oil shock regime, tell me which A-share groups benefit and which ones get hurt."
- "Continuously watch public news and map major events into A-share watchlists."

## What This Skill Contains

- `SKILL.md`: main instructions and trigger description
- `references/methodology.md`: decision framework
- `references/data-sources.md`: primary and market data sources
- `references/persona-prompt.md`: decision-maker persona prompt
- `references/trading-mode-prompt.md`: time-based pre-open trading mode prompt
- `references/cross-cycle-watchlist.md`: how to use the cross-cycle core stock pool
- `references/event-regime-watchlists.md`: war-shock overlay watchlists
- `references/message-iterator.md`: persistent message iterator for high-attention news
- `scripts/fetch_market_snapshot.py`: index and sector breadth snapshot
- `scripts/fetch_quotes.py`: Tencent quote watchlist snapshot
- `scripts/morning_brief.py`: one-command markdown morning brief
- `scripts/opening_window_checklist.py`: first-30-minute decision sheet
- `scripts/news_iterator.py`: RSS polling, classification, SQLite state, markdown/jsonl outputs, and automatic event stock pools
- `scripts/install_news_iterator_launchd.py`: macOS launchd installer for scheduled polling
- `scripts/smoke_test.py`: local smoke test for the bundled scripts

## Agent Install

Install this folder into:

- `~/.codex/skills/a-share-decision-desk`
- `~/.openclaw/skills/a-share-decision-desk`

Example:

```bash
git clone https://github.com/huangrichao2020/a-share-decision-kit.git
mkdir -p ~/.codex/skills
cp -R a-share-decision-kit/skill/a-share-decision-desk ~/.codex/skills/a-share-decision-desk
```

## Keys And Credentials

Project-specific runtime keys required: `none`

This skill uses only public data sources and Python standard library modules.

Optional credentials:

- GitHub read access: only if the repo is private and an agent must clone it
- GitHub write access: only if an agent should push changes back
- Model-provider API keys: may be required by the host agent environment, but not by this skill itself

## Local Smoke Test

```bash
python3 scripts/smoke_test.py
python3 scripts/fetch_market_snapshot.py --format markdown
python3 scripts/fetch_quotes.py sz300502 sh688981 sh600938
python3 scripts/morning_brief.py --groups core10 tech_repair
python3 scripts/morning_brief.py --groups cross_cycle_anchor12
python3 scripts/morning_brief.py --groups cross_cycle_ai_hardware cross_cycle_semis cross_cycle_software_platforms cross_cycle_defense_industrial
python3 scripts/morning_brief.py --groups war_shock_core12
python3 scripts/morning_brief.py --groups war_benefit_oil_coal war_headwind_compute_power
python3 scripts/opening_window_checklist.py --groups tech_repair defensive_gauge policy_beta
python3 scripts/news_iterator.py poll
python3 scripts/news_iterator.py report --hours 12
python3 scripts/install_news_iterator_launchd.py install --interval-seconds 300
python3 scripts/morning_brief.py
python3 scripts/opening_window_checklist.py
```

## Optional ClawHub Publish

From this folder:

```bash
clawhub login
clawhub publish /absolute/path/to/a-share-decision-desk --slug a-share-decision-desk --name "A-Share Decision Desk" --version 0.1.7 --tags latest,finance,a-share,china,markets
```

## Notes

- ClawHub publishes a skill folder with `SKILL.md` plus supporting text files.
- This skill uses only text-based resources and Python standard library scripts.
- If `clawhub publish .` misreads the folder, use an absolute path or pass `--workdir` explicitly.
- The opening-window script is intended for `09:00-10:00` use, especially the first 30 minutes after the A-share cash open.
- For the larger quality pool, use `cross_cycle_anchor12` daily and reserve `cross_cycle_core` for weekly or phase-rotation review.
- For geopolitical shocks, treat `war_benefit_oil_coal` and `war_headwind_compute_power` as temporary regime overlays, not permanent core watchlists.
- If you only want one wartime overlay, start with `war_shock_core12`.
- For continuous event intake, run `news_iterator.py` as a local service and treat the alert stream as an overlay, not a replacement for tape and breadth.
- The morning brief and opening checklist can automatically append event-driven stock pools when `event_watchlists.json` exists in the default state directory.
