# Edit holdings

A visitor lists up to 30 ASX holdings with a percentage weight each. The editor shows the company name under each code, a running total, and a note when the total will be scaled; the form blocks weights it would reject.

## Sub-features

- `holdings-edit` changes a code or weight; codes are upper-cased as typed.
- `holdings-name` shows the company name under a known code.
- `holdings-total` shows `Total N%` and adds `. We'll scale it to 100%.` when the total is off by more than 0.5.
- `holdings-add-remove` adds a blank row or removes a row.
- `holdings-validate` blocks a weight above 100, a missing weight and duplicate codes on `Analyze`.
- `holdings-persist` keeps the holdings after a reload.

## How to get to it (user POV)

- The `Your holdings` box at the top left.

## Driving it with cdp.mjs

Preconditions:

- Baseline state from README.md.

- **Edit.** Run `page.fill('[aria-label="Holding 3 ASX code"]', "wes")`. The field reads `WES` and `Wesfarmers Limited` appears under it.
- **Total.** Run `page.fill('[aria-label="Holding 3 ASX code"]', "")`. The total reads `Total 70%. We'll scale it to 100%.` because rows without a code are not sent.
- **Exact edge.** Fill weights `30.6`, `34.45`, `34.45`. The total reads `Total 99.5%` with no scaling note.
- **Validate.** Run `page.fill('[aria-label="Holding 1 weight in percent"]', "150")`, pick a sample, `page.click("text=Analyze")`. `p.notice-error[role=alert]` reads `Keep each weight at 100% or less.`
- **Add and remove.** `page.click("text=Add holding")` adds `Holding 4 ASX code`; `page.click('[aria-label="Remove BHP"]')` removes the BHP row.
- **Persist.** After editing, `page.goto(APP)` without clearing localStorage. The edited rows come back; `pnm.holdings` in localStorage matches.
- **Proof.** Screenshot the editor after each step and record the total text.

## Gotchas

- Find the total by its text (`Total …`); it has no dedicated handle.
- The company name comes from `/api/tickers`; it can lag a moment after typing. Wait for the text.
- The editor shows the total to one decimal, so 100.54 reads `100.5%` with a scaling note. That is a known, accepted quirk (docs/HANDOFF.md).
