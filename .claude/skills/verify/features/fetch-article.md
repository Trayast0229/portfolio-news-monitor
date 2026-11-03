# Fetch an article from a link

A visitor pastes a news link and chooses Fetch; the backend downloads the page and fills the news box with the headline and article text, or shows a readable reason it couldn't.

## Sub-features

- `fetch-ok` fills `#news` with the title and text of a public article.
- `fetch-long` keeps the first 20,000 characters and says `The article was long, so we kept the first 20,000 characters.`
- `fetch-blocked` explains paywalls, missing pages, non-pages, private addresses and slow sites.

## How to get to it (user POV)

- Paste a link into `Article link` and choose `Fetch`, or press Enter in the link field.

## Driving it with cdp.mjs

Preconditions:

- Baseline state from README.md, and the machine can reach the public site. Check with `curl -sI <url>` first.

- **Fetch.** Run `page.fill('[aria-label="Article link"]', url)` then `page.click("text=Fetch")`. Wait until the button reads `Fetch` again. `#news` now starts with the article title; no `p.notice-error[role=alert]` appears.
- **Refused address.** Fill `http://localhost:8100/` and Fetch. The alert reads `That address isn't allowed. Use a link to a public news site.`
- **Not a link.** Fill `bhp news` and Fetch. The alert reads `Enter a full web address starting with http:// or https://.`
- **Proof.** Screenshot after Fetch; record the first line of `#news` or the alert text.

## Gotchas

- Needs the public internet, and sites change. ABC News and Wikipedia worked on 2026-11-03; Reuters, AP and news.com.au are blocked or yield no text. If the network is unavailable, report `fetch-ok` as skipped.
- Wikipedia blocks rapid repeat requests for a short time and then shows the subscription/blocked message. Space retries out.
- The backend refuses every non-public address, so a local test page cannot be fetched through the UI; test those paths with `backend/tests/test_article.py` instead.
