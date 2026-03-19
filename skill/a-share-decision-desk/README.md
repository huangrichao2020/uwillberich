# A-Share Decision Desk

ClawHub/OpenClaw-ready skill folder for next-session A-share discretionary planning.

## What This Skill Contains

- `SKILL.md`: main instructions and trigger description
- `references/methodology.md`: decision framework
- `references/data-sources.md`: primary and market data sources
- `references/persona-prompt.md`: decision-maker persona prompt
- `references/trading-mode-prompt.md`: time-based pre-open trading mode prompt
- `scripts/fetch_market_snapshot.py`: index and sector breadth snapshot
- `scripts/fetch_quotes.py`: Tencent quote watchlist snapshot
- `scripts/morning_brief.py`: one-command markdown morning brief

## Local Smoke Test

```bash
python3 scripts/fetch_market_snapshot.py --format markdown
python3 scripts/fetch_quotes.py sz300502 sh688981 sh600938
python3 scripts/morning_brief.py --groups core10 tech_repair
```

## ClawHub Publish

From this folder:

```bash
clawhub login
clawhub publish . --slug a-share-decision-desk --name "A-Share Decision Desk" --version 0.1.0 --tags latest
```

## Notes

- ClawHub publishes a skill folder with `SKILL.md` plus supporting text files.
- This skill uses only text-based resources and Python standard library scripts.
