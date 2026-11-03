# Choose and compare engines

A visitor picks FinBERT, Claude or both. With both, the result panel shows a switch to compare their scores side by side.

## Sub-features

- `engines-toggle` turns each engine on or off; at least one must stay on.
- `engines-status` shows a note under a selected engine that can't run (Claude without a key, FinBERT loading).
- `engines-compare` shows one tab per engine with its score when both ran.

## How to get to it (user POV)

- The `Engine` box above `Analyze`, then the tabs at the top of `Portfolio sentiment`.

## Driving it with cdp.mjs

Preconditions:

- Baseline state from README.md. Claude is `unavailable` unless the user approved `VERIFY_CLAUDE=1`.

- **Toggle.** Click the `.engine-toggle` whose `<strong>` reads `Claude` (tag it with a `data-verify` attribute first, as analyze-finbert.mjs does). Its `aria-pressed` becomes `true` and `pnm.engines` in localStorage lists both.
- **Status with Claude off.** With Claude selected, a `.notice` under it explains that Claude needs an API key.
- **Compare with Claude off.** Analyze a sample with both selected. Two `[role=tab]` buttons appear, reading `FinBERT 96` and `Claude error` for the CommBank sample. To select a tab, tag the one whose first `span` reads `Claude` (`setAttribute("data-verify", "claude-tab")`) and click `[data-verify="claude-tab"]`; its `aria-selected` becomes `true` and `.result .notice-error` starts `Claude isn't set up.`
- **Compare with Claude on.** Only with `VERIFY_CLAUDE=1` and the user's approval: both tabs show scores; each run costs money and takes about 10 seconds.
- **Proof.** Screenshot both tabs and record each tab's text.

## Gotchas

- The Claude-off note currently tells visitors to edit `backend/.env`; it is due to be rewritten before the public launch (docs/HANDOFF.md section 6). Assert that a note exists, not its wording.
- `text=Claude` does not find a result tab: the tab's text also holds the score. Tag it as above.
- Tabs don't respond to arrow keys yet (a known open item); drive them by clicking.
- Never turn Claude on to make a journey pass. Report the Claude-on paths as skipped when it is off.
