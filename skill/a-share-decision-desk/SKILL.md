---
name: a-share-decision-desk
description: Build next-session A-share decision plans, repair-sector hypotheses, opening checklists, and watchlists using current index, breadth, sector, and watchlist data plus official policy and primary news sources. Use when the user asks what A-shares may do tomorrow, which sectors may repair, how to trade the open, or wants a reusable A-share discretionary workflow.
metadata: {"openclaw":{"emoji":"📈","homepage":"https://github.com/huangrichao2020/a-share-decision-kit","requires":{"bins":["python3"]}}}
---

# A-Share Decision Desk

## Overview

Use this skill for decision-oriented A-share analysis. The goal is not to explain the market mechanically, but to convert today’s tape and overnight developments into a concrete next-session plan.

## Core Workflow

1. Gather market structure first.
   - Run `scripts/fetch_market_snapshot.py` for indices, breadth, and sector leaders/laggards.
   - Run `scripts/fetch_quotes.py` or `scripts/morning_brief.py` for the watchlist.
2. Confirm the overnight and policy layer.
   - Use primary sources first for `PBOC`, `Federal Reserve`, and other central-bank decisions.
   - Use high-quality news sources for geopolitics, oil, and global risk sentiment.
3. Classify the market through three layers.
   - External shock: oil, rates, U.S. equities, geopolitics
   - Domestic policy/liquidity: `LPR`, PBOC posture, macro support
   - Internal structure: breadth, leadership, relative strength, style rotation
4. Build a scenario tree.
   - Provide `Base / Bull / Bear` paths with explicit triggers and invalidations.
5. Turn the view into an execution checklist.
   - Include `09:00`, `09:20-09:25`, `09:30-10:00`, and `14:00-14:30`.

## Decision Heuristics

- Prefer sectors that resisted best in a weak tape over sectors that merely fell the most.
- Treat defensive leadership as separate from broad market repair.
- On monthly `LPR` days, use the `09:00` release as a hard branch in the plan.
- A repair thesis is stronger when leadership broadens from core growth names into secondary names and brokers.
- A rebound without breadth is usually just a technical bounce.

## Scripts

Use these scripts before writing the decision note:

- `scripts/fetch_market_snapshot.py`
  - Pulls Eastmoney index and sector breadth data.
- `scripts/fetch_quotes.py`
  - Pulls Tencent quote snapshots for user-specified names.
- `scripts/morning_brief.py`
  - Builds a markdown brief from the default watchlists in `assets/default_watchlists.json`.

## References

Read only what you need:

- `references/methodology.md`
  - Trading philosophy, decision tree, and timing gates.
- `references/data-sources.md`
  - Source map for official and market data endpoints.
- `references/persona-prompt.md`
  - Decision-maker persona for desk-style answers.
- `references/trading-mode-prompt.md`
  - Time-boxed opening workflow for the next A-share session.

## Output Standard

Default to a compact desk-style answer:

- one-paragraph decision summary
- `Base / Bull / Bear` path
- most likely repair sectors
- defensive-only sectors
- opening checklist
- `do / avoid`
