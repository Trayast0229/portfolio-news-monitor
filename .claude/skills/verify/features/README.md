# Portfolio News Monitor verification map

This directory is the maintained source for verifying what a visitor can do in Portfolio News Monitor. Read this index before driving the app, then use the matching feature file as the recipe.

| Feature | File |
|---|---|
| Analyze a story and read the result | [analyze.md](analyze.md) |
| Edit holdings | [holdings-editor.md](holdings-editor.md) |
| Fetch an article from a link | [fetch-article.md](fetch-article.md) |
| Recent analyses | [history.md](history.md) |
| Choose and compare engines | [engines.md](engines.md) |

## Baseline preconditions

- Started with `.claude/skills/verify/scripts/launch.sh`, and `doctor.sh` exits 0.
- The page is `http://localhost:5174/` in the Chrome on :9223.
- Each journey clears localStorage and reloads, so it starts with holdings BHP 40, CBA 30, CSL 30, FinBERT selected, Claude not selected, and no history.
- Claude is off unless the user approved `VERIFY_CLAUDE=1`.
- Never drive the user's own servers on :8000 and :5173.

## Driving conventions

- Write each journey as a Node script that imports `../cdp.mjs`; see `scripts/journeys/analyze-finbert.mjs`.
- Prefer `aria-label`, `role`, `id` and visible button text over classes or position.
- Act only through `page.click`, `page.fill` and `page.goto`. Use `page.evaluate` to read state, never to change it, except `localStorage.clear()` at the start.
- Wait for an observable state (`.result[aria-busy="false"]`, a text) instead of sleeping.

## Proof and skip reporting

- Capture a screenshot before and after the action, in the journey's evidence directory.
- Assert the visible result and the saved side effect (for example `pnm.history` in localStorage).
- Read the final screenshot before reporting a pass.
- Report a journey that needs Claude, the network, or a public news site as skipped with the reason, not as passed through another path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with cdp.mjs`, and `Gotchas`.
