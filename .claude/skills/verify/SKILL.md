---
name: verify
description: Launch a private copy of Portfolio News Monitor (FastAPI backend plus Vite/React web UI) and drive the web UI in headless Chrome the way a user does, capturing screenshots and saved browser state as proof. Use to confirm a UI or API change works in the real app, to reproduce a bug before fixing it, or to run the browser checks listed in docs/HANDOFF.md.
---

# Verify Portfolio News Monitor

The user-facing surface is the web page: a grid of cards (holdings, headline, engines with Analyze on top; news box with Fetch, the score card and the per-holding card below) and a Recent analyses drawer opened from the header. The backend API (`/api/health`, `/api/tickers`, `/api/article`, `/api/analyze`) sits behind the page. Drive the page. Use `curl` on the API only for checks the page cannot express (status codes, malformed bodies).

The user usually has their own dev servers on :8000 and :5173. Never drive, restart, or stop those. This skill runs its own copy on other ports:

| Part | Port | Notes |
|---|---|---|
| Backend | 8100 | `backend/.venv` uvicorn, no `--reload`, Claude off |
| Frontend | 5174 | Vite dev server, `API_URL` points `/api` at :8100 |
| Chrome | 9223 | headless, fresh profile per launch, so localStorage starts empty |

Only one verification instance can run at a time. All commands below run from the repo root.

## Launch

```bash
.claude/skills/verify/scripts/launch.sh
```

Ready means it printed `READY app=http://localhost:5174 health=...` with `"finbert":"ready"`. FinBERT takes a few seconds when the model is cached, and the first run on a new machine downloads about 440 MB. The script refuses to start if any of the three ports is busy.

Claude stays `unavailable`, matching the planned public deployment and costing nothing. To verify Claude itself, launch with `VERIFY_CLAUDE=1`. That uses the key in `backend/.env` and every Analyze costs money, so get the user's approval first. Never print the key.

## Doctor

```bash
.claude/skills/verify/scripts/doctor.sh
```

Read-only. Checks that each port belongs to the process `launch.sh` started, that FinBERT is ready and Claude is off, that the page is served, and that Chrome answers. Run it first whenever anything looks off. Exit 0 means every line is `OK`.

## Drive

`scripts/cdp.mjs` is a dependency-free Chrome DevTools driver. It clicks at an element's centre and types real text, so React sees the same events a user makes. Write a journey as a small Node script, like `scripts/journeys/analyze-finbert.mjs`:

```js
import { APP, connect, evidenceDir } from "../cdp.mjs";
const dir = evidenceDir("my-check");
const page = await connect();
await page.goto(APP);
await page.evaluate("localStorage.clear()");   // a clean visitor; reload after
await page.goto(APP);
await page.fill('[aria-label="Holding 1 weight in percent"]', "150");
await page.click("text=Analyze");
await page.waitForText("Keep each weight at 100% or less.");
await page.screenshot(dir, "weight-150");
page.close();
```

Targets are CSS selectors or `text=Exact label`, which matches the first visible button, label or tab with that text. `page.fill(target, "")` clears a field. `page.evaluate(js)` reads state such as `localStorage.getItem("pnm.history")`. Use it to read, never to set app state.

Stable handles in this app:

| What | Handle |
|---|---|
| Holding row N code / weight | `[aria-label="Holding N ASX code"]`, `[aria-label="Holding N weight in percent"]` |
| Remove row / add row | `[aria-label="Remove BHP"]`, `text=Add holding` |
| Article link / Fetch | `[aria-label="Article link"]`, `text=Fetch` |
| News text | `#news` |
| Samples | `text=Iron ore slides`, `text=CommBank record profit`, `text=CSL cuts guidance` |
| Engine toggles | `.engine-toggle` buttons with `aria-pressed`, named by their `<strong>` text `FinBERT` / `Claude`; an engine the server can't run is `disabled` |
| Analyze | `text=Analyze` (reads `Analyzing…` while busy) |
| Form or fetch error | `p.notice-error[role=alert]` |
| Score card | `.result` with `aria-busy`, gauge `.result svg[role=img]` aria-label `Sentiment score N of 100, Label`, `.result .exposure`, `.result .notice`, Claude's `.result .summary` |
| Per-holding card | `.detail`: `.detail .holding` rows, key points, `How this score was worked out`; `.detail .result-empty` before a result or after an engine error |
| Engine switch (two engines) | `[role=tab]` inside `.engine-switch` |
| History | `.history-toggle` in the header (hidden when nothing is saved, `aria-expanded`) opens `#history`; then `.history li button`, `text=Clear`; saved as `pnm.history` in localStorage |

The feature map in `features/` lists each user journey with its handles and proof. Read `features/README.md` first.

## Evidence

Every journey writes to `$TMPDIR/pnm-verify-evidence/<timestamp>-<name>/`: numbered screenshots of the action and the result, plus `result.json` with the values it asserted. Prove the real user path: click and type through the page, never call React setters or test-only endpoints. Capture the state before and after the action, and check side effects too, such as the history entry in localStorage and the card in Recent analyses (open the drawer first). Read at least the final screenshot yourself before reporting a pass. The FinBERT model is real; nothing is mocked.

## Cleanup

```bash
.claude/skills/verify/scripts/cleanup.sh
```

Stops only the three processes `launch.sh` recorded, copies their logs to `$TMPDIR/pnm-verify-evidence/logs-<timestamp>/`, and deletes the run directory and Chrome profile. Evidence stays. Run it after every session, including failed ones, before launching again.

## Helpers

| Script | Run |
|---|---|
| `scripts/launch.sh` | `.claude/skills/verify/scripts/launch.sh` (`VERIFY_CLAUDE=1` to turn Claude on) |
| `scripts/doctor.sh` | `.claude/skills/verify/scripts/doctor.sh` |
| `scripts/cleanup.sh` | `.claude/skills/verify/scripts/cleanup.sh` |
| `scripts/cdp.mjs` | imported by journeys |
| `scripts/journeys/analyze-finbert.mjs` | `node .claude/skills/verify/scripts/journeys/analyze-finbert.mjs` |

Logs while running: `$TMPDIR/pnm-verify/backend.log`, `frontend.log`, `chrome.log`.
