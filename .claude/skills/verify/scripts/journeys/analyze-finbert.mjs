// Journey: a first-time visitor runs FinBERT on the CommBank sample with the default holdings.
// Proves the score, the exposure line, the per-holding breakdown and the saved history entry.
//   node .claude/skills/verify/scripts/journeys/analyze-finbert.mjs
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { APP, connect, evidenceDir } from "../cdp.mjs";

const dir = evidenceDir("analyze-finbert");
const page = await connect();
const fail = (msg) => {
  throw new Error(`${msg} (evidence in ${dir})`);
};
try {
  await page.goto(APP);
  await page.evaluate("localStorage.clear()");
  await page.goto(APP);

  const holdings = await page.evaluate(
    `[1, 2, 3].map(i => [document.querySelector('[aria-label="Holding ' + i + ' ASX code"]')?.value,
                          document.querySelector('[aria-label="Holding ' + i + ' weight in percent"]')?.value].join(" "))`,
  );
  if (holdings.join() !== "BHP 40,CBA 30,CSL 30") fail(`default holdings were ${holdings.join(", ")}`);

  for (const [engine, want] of [["FinBERT", "true"], ["Claude", "false"]]) {
    const toggle = `[...document.querySelectorAll(".engine-toggle")].find(b => b.querySelector("strong")?.textContent === "${engine}")`;
    if ((await page.evaluate(`${toggle}?.getAttribute("aria-pressed")`)) !== want) {
      await page.evaluate(`${toggle}.setAttribute("data-verify", "${engine}")`);
      await page.click(`[data-verify="${engine}"]`);
    }
  }

  await page.click("text=CommBank record profit");
  const news = await page.evaluate(`document.querySelector("#news").value`);
  if (!news.includes("CommBank")) fail("the sample story did not fill the news box");
  await page.screenshot(dir, "1-before-analyze");

  await page.click("text=Analyze");
  await page.waitFor(`document.querySelector('.result[aria-busy="false"] .exposure, .result[aria-busy="false"] .notice-error')`, "a result", 120_000);
  const gauge = await page.attr(".result svg[role=img]", "aria-label");
  const exposure = await page.text(".result .exposure");
  const error = await page.text(".result .notice-error");
  await page.screenshot(dir, "2-result");
  if (error) fail(`the engine returned an error: ${error}`);
  if (!/^Sentiment score \d+ of 100, /.test(gauge)) fail(`gauge label was "${gauge}"`);
  if (!exposure?.startsWith("Affects 30%")) fail(`exposure line was "${exposure}"`);

  const saved = await page.evaluate(`JSON.parse(localStorage.getItem("pnm.history") ?? "[]")`);
  const listed = await page.text(".history li");
  if (saved.length !== 1 || saved[0].news !== news.trim()) fail(`saved history was ${JSON.stringify(saved).slice(0, 200)}`);
  if (!listed?.includes("FinBERT")) fail(`history list showed "${listed}"`);

  const proof = { gauge, exposure, historyEntries: saved.length, historyRow: listed };
  writeFileSync(join(dir, "result.json"), JSON.stringify(proof, null, 2));
  console.log(`PASS analyze-finbert ${JSON.stringify(proof)}\nevidence: ${dir}`);
} finally {
  page.close();
}
