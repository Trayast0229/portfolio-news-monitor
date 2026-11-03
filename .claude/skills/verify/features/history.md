# Recent analyses

Every finished analysis is saved in the browser, newest first, up to 20. A visitor can reopen one to restore its story, holdings and result, or clear the list.

## Sub-features

- `history-save` adds a row with the story start, time and each engine's score, `Unrelated` or `Error`.
- `history-dedupe` keeps one row for the same story, holdings (in any order) and engines.
- `history-open` restores the story, holdings, link and result without re-running.
- `history-clear` empties the list.

## How to get to it (user POV)

- The `Recent analyses` section below the main panels. It only appears once there is at least one row.

## Driving it with cdp.mjs

Preconditions:

- Baseline state from README.md, then one analysis of `CommBank record profit` (as in analyze.md).

- **Save.** After the analysis, `.history li` contains `FinBERT 96` and `pnm.history` in localStorage has one entry whose `news` equals `#news`.
- **Dedupe.** Remove the BHP row (`[aria-label="Remove BHP"]`), `text=Add holding`, fill the new row with `BHP` and `40`, then `Analyze` again. `.history li` still has one row.
- **Open.** Change `#news` to another sample, then `page.click(".history li button")`. `#news`, the holdings and the gauge return to the saved run.
- **Clear.** `page.click("text=Clear")`. The `Recent analyses` section disappears and `pnm.history` is `[]`.
- **Proof.** Screenshot the history list after each step and record `JSON.parse(localStorage.getItem("pnm.history")).length`.

## Gotchas

- `text=Clear` must be clicked inside `.history`; it is the only `Clear` button today.
- Rows are capped at 20; older ones drop off.
- Times read `Just now` right after a run; don't assert on later wording.
