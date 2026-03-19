---
name: a-share-decision-desk
description: Build next-session A-share game plans from market structure, overnight macro shocks, policy timing, and watchlist leadership. Use when the user asks what A-shares may do tomorrow, which sectors may repair first, how to read the open, or wants a reusable pre-open discretionary decision workflow.
metadata: {"openclaw":{"emoji":"📈","homepage":"https://github.com/huangrichao2020/a-share-decision-kit","requires":{"bins":["python3"]}}}
---

# A-Share Decision Desk

## Overview

Use this skill for decision-oriented A-share analysis. The goal is not to explain the market mechanically, but to convert today’s tape and overnight developments into a concrete next-session plan.

Best fit:

- next-session A-share outlook
- likely repair sectors after a selloff
- opening checklist for `09:00`, `09:25`, and `09:30-10:00`
- first-30-minute observation template for distinguishing true repair from defensive concentration
- watchlist-based decision notes
- distinguishing defensive leadership from true market repair

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
- `scripts/opening_window_checklist.py`
  - Builds a first-30-minute observation sheet with time gates, group scoreboards, and watchlist signal tables.
- `scripts/smoke_test.py`
  - Verifies that the bundled scripts and public endpoints are working.

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
- `references/opening-window-template.md`
  - A reusable first-30-minute decision template.
- `references/cross-cycle-watchlist.md`
  - How to use the cross-cycle core stock pool without turning it into an unfocused mega-list.

## Output Standard

Default to a compact desk-style answer:

- one-paragraph decision summary
- `Base / Bull / Bear` path
- most likely repair sectors
- defensive-only sectors
- opening checklist
- `do / avoid`
