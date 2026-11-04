# Choose and compare engines

A visitor picks FinBERT, Claude or both. An engine the server can't run is greyed out and can't be picked. With both, the score card shows a switch to compare their scores side by side.

## Sub-features

- `engines-toggle` turns each engine on or off; at least one must stay on.
- `engines-unavailable` greys out an engine whose health status is `unavailable` (Claude without a key): the button is `disabled`, `aria-pressed` is `false`, its hint reads `Available when you run the project locally.`, and Analyze leaves it out even if an earlier visit saved it in `pnm.engines`.
- `engines-status` shows `FinBERT is starting up, which can take a minute.` under FinBERT while it loads. In development only, an unavailable engine also gets a setup note (Claude's API key, FinBERT's `pip install`); the production build has none.
- `engines-compare` shows one tab per engine with its score when both ran.

## How to get to it (user POV)

- The `Engine` card at the top right, then the tabs at the top of the `Portfolio sentiment` card.

## Driving it with cdp.mjs

Preconditions:

- Baseline state from README.md. Claude is `unavailable` unless the user approved `VERIFY_CLAUDE=1`.

- **Unavailable with Claude off.** The Claude `.engine-toggle` (the first `div.engine` in `.engine-card`) is `disabled` and its `.muted` hint reads `Available when you run the project locally.` Clicking it leaves `aria-pressed` at `false`. Analyze a sample: `pnm.history[0].response.results` has only `finbert`.
- **Setup note.** On the dev server (:5174) a `.engine-card .notice` explains that Claude needs an API key. To check the production build, run `API_URL=http://localhost:8100 npx vite preview --port 5175 --strictPort` in `frontend/` after `npm run build`, drive :5175, and confirm there is no `.engine-card .notice`; stop that server afterwards (cleanup.sh doesn't know about it).
- **Toggle and compare with Claude on.** Only with `VERIFY_CLAUDE=1` and the user's approval: click the Claude toggle (`aria-pressed` becomes `true`, `pnm.engines` lists both), analyze a sample, and two `[role=tab]` buttons appear in `.engine-switch`, one per engine with its score. Click `.engine-switch [role=tab]:last-child` to switch; both `.result` and `.detail` change. Each run costs money and takes about 10 seconds.
- **Proof.** Screenshot both tabs and record each tab's text.

## Gotchas

- With Claude off the comparison tabs can't be reached from the page any more; report them as skipped rather than enabling Claude.
- `text=Claude` does not find a result tab: the tab's text also holds the score. Use `.engine-switch [role=tab]` instead.
- Tabs don't respond to arrow keys yet (a known open item); drive them by clicking.
- Never turn Claude on to make a journey pass. Report the Claude-on paths as skipped when it is off.
