# A-Share Decision Kit

Reusable materials for a discretionary A-share decision workflow:

- `prompts/persona-prompt.md`: decision-maker persona prompt
- `prompts/trading-mode-prompt.md`: daily execution-mode prompt
- `skill/a-share-decision-desk/`: installable Codex skill

## Install The Skill

Copy `skill/a-share-decision-desk` into your local `$CODEX_HOME/skills/` directory.

## Included Scripts

All scripts live under `skill/a-share-decision-desk/scripts/` and use only the Python standard library.

- `fetch_quotes.py`: fetch Tencent quote snapshots for a watchlist
- `fetch_market_snapshot.py`: fetch Eastmoney index and sector breadth snapshots
- `morning_brief.py`: build a simple pre-open markdown brief from default watchlists

## Example Usage

```bash
python3 skill/a-share-decision-desk/scripts/fetch_market_snapshot.py --format markdown
python3 skill/a-share-decision-desk/scripts/fetch_quotes.py sz300502 sz300308 sh688981
python3 skill/a-share-decision-desk/scripts/morning_brief.py --groups core10 tech_repair
```

## Notes

- Market endpoints can change or throttle. Use the scripts as fast data collectors, then verify high-stakes conclusions with official or primary news sources.
- On monthly `LPR` days, the workflow assumes the `9:00` release window.
