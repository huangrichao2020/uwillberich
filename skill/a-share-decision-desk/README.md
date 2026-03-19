# A-Share Decision Desk

A ClawHub/OpenClaw-ready skill for next-session A-share discretionary planning.

It is designed for one job: turn today’s tape and overnight developments into a concrete game plan for tomorrow’s open.

## Good Use Cases

- "What is the most likely A-share path tomorrow?"
- "Which sectors are most likely to repair first after today’s selloff?"
- "Give me a `09:00 / 09:25 / 09:30-10:00` opening checklist."
- "Build a watchlist-driven pre-open note for A-shares."
- "Tell me whether this is real repair or just defensive concentration."
- "Use the cross-cycle core stock pool to narrow tomorrow's key observation list."

## What This Skill Contains

- `SKILL.md`: main instructions and trigger description
- `references/methodology.md`: decision framework
- `references/data-sources.md`: primary and market data sources
- `references/persona-prompt.md`: decision-maker persona prompt
- `references/trading-mode-prompt.md`: time-based pre-open trading mode prompt
- `references/cross-cycle-watchlist.md`: how to use the cross-cycle core stock pool
- `scripts/fetch_market_snapshot.py`: index and sector breadth snapshot
- `scripts/fetch_quotes.py`: Tencent quote watchlist snapshot
- `scripts/morning_brief.py`: one-command markdown morning brief
- `scripts/opening_window_checklist.py`: first-30-minute decision sheet
- `scripts/smoke_test.py`: local smoke test for the bundled scripts

## Local Smoke Test

```bash
python3 scripts/smoke_test.py
python3 scripts/fetch_market_snapshot.py --format markdown
python3 scripts/fetch_quotes.py sz300502 sh688981 sh600938
python3 scripts/morning_brief.py --groups core10 tech_repair
python3 scripts/morning_brief.py --groups cross_cycle_anchor12
python3 scripts/morning_brief.py --groups cross_cycle_ai_hardware cross_cycle_semis cross_cycle_software_platforms cross_cycle_defense_industrial
python3 scripts/opening_window_checklist.py --groups tech_repair defensive_gauge policy_beta
```

## ClawHub Publish

From this folder:

```bash
clawhub login
clawhub publish /absolute/path/to/a-share-decision-desk --slug a-share-decision-desk --name "A-Share Decision Desk" --version 0.1.3 --tags latest,finance,a-share,china,markets
```

## Notes

- ClawHub publishes a skill folder with `SKILL.md` plus supporting text files.
- This skill uses only text-based resources and Python standard library scripts.
- If `clawhub publish .` misreads the folder, use an absolute path or pass `--workdir` explicitly.
- The opening-window script is intended for `09:00-10:00` use, especially the first 30 minutes after the A-share cash open.
- For the larger quality pool, use `cross_cycle_anchor12` daily and reserve `cross_cycle_core` for weekly or phase-rotation review.
