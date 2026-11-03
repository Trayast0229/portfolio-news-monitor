# Analyze a story

A visitor pastes or picks a news story, selects Analyze, and sees how it lands on their whole portfolio: a 0–100 gauge with a label, bullish/neutral/bearish shares, how much of the portfolio the story affects, and a line per holding.

## Sub-features

- `analyze-score` shows a score, label and probabilities for a story that names a holding.
- `analyze-unrelated` shows `Not related` when no holding is named.
- `analyze-breakdown` lists each holding as scored or `Not affected`, with the quoted sentences as the reason.
- `analyze-language` warns `FinBERT reads English only, so it may have missed this story.` for mostly non-English text.
- `analyze-scaled` notes `Your weights didn't add up to 100%, so they were scaled to fit.` when weights are off by more than 0.5.

## How to get to it (user POV)

- Pick a sample chip under the news box, or type or paste text into `News story`, then choose `Analyze`.
- Fetch an article first (see fetch-article.md), then choose `Analyze`.
- Reopen a past run from Recent analyses (see history.md); that shows a saved result without re-running.

## Driving it with cdp.mjs

Preconditions:

- Baseline state from README.md. FinBERT is `ready` in `doctor.sh`.

- **Score.** Choose `CommBank record profit`, then `Analyze`. Run `page.click("text=CommBank record profit")`, `page.click("text=Analyze")`, then wait for `.result[aria-busy="false"] .exposure`. The gauge label reads `Sentiment score 96 of 100, Strongly bullish` and `.result .exposure` starts `Affects 30% of your portfolio (1 of 3 holdings)`. `scripts/journeys/analyze-finbert.mjs` does exactly this.
- **Unrelated.** Fill `#news` with a 50+ character story naming none of BHP, CBA or CSL, then `Analyze`. The gauge label is `No score yet`, the caption reads `Not related`, and `.result-empty` says `This story doesn't touch any of your holdings.`
- **Language.** Fill `#news` with Chinese text that includes `BHP`, then `Analyze`. The first `.result .notice` reads `FinBERT reads English only, so it may have missed this story.`
- **Scaled.** Fill holding weights `30`, `30`, `30`, then analyze a sample. A `.result .notice` reads `Your weights didn't add up to 100%, so they were scaled to fit.`
- **Proof.** Screenshot before `Analyze` and after the result; record the gauge label, exposure text and every `.result .notice`.

## Gotchas

- `Analyze` is disabled and reads `Analyzing…` while busy. Wait on `.result[aria-busy="false"]`, not on the button text.
- The news box needs at least 50 characters or the form shows an error instead of calling the backend.
- The FinBERT `Not related` view also says `Claude can also pick up indirect effects…`. That sentence is due to be rewritten before the public launch (docs/HANDOFF.md section 6), so do not assert on its wording.
- Scores come from the real model. Assert the label and zone, not an exact score, except for the samples whose scores are recorded here.
