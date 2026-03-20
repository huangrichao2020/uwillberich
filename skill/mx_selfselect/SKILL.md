---
name: mx_selfselect
description: Query, add, and remove Eastmoney self-selected stocks through natural-language requests backed by the user's Eastmoney account. Use when the user wants to inspect their watchlist, add names to it, remove names from it, or sync a generated A-share focus list into Eastmoney self-select.
---

# mx_selfselect

Use this skill as the execution-side companion to `uwillberich`.

Boundary:

- this skill owns Eastmoney self-select operations only
- this skill is useful after a report has already decided which names matter
- this skill does not generate the A-share daily report itself
- this skill does not own HTML rendering or deployment

## Good Use Cases

- query my Eastmoney self-select list
- add a stock to my Eastmoney self-select list
- remove a stock from my Eastmoney self-select list
- sync the strongest names from a `uwillberich` daily note into self-select

## Workflow

1. Ensure `MX_APIKEY` or `EM_API_KEY` is available.
   - The skill first checks local environment variables.
   - Then it checks `~/.uwillberich/runtime.env`.
2. For read-only inspection, use `scripts/mx_selfselect.py list`.
3. For natural-language mutations, use `scripts/mx_selfselect.py manage --query '把东方财富加入自选'`.
4. Only run add/remove actions when the user clearly asked to mutate the watchlist.

## Scripts

- `scripts/mx_selfselect.py`
  - `status`: show whether the API key is available
  - `list`: query the current self-select list
  - `manage --query ...`: send a natural-language add/remove/manage request

## Output Standard

- Default to concise markdown for humans.
- Use `--format json` when another tool or agent needs the raw response.
- If the returned list is empty, tell the user to verify it in the Eastmoney app.
