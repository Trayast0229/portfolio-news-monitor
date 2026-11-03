import { useEffect, useState } from "react";
import { ENGINE_NAMES, type AnalyzeResponse, type EngineName, type PortfolioResult } from "../lib/api";
import { languageNotice, skippedNotice } from "../lib/assessment";
import { zoneFor } from "../lib/gauge";
import { pct, signedPct } from "../lib/format";
import { Bolt } from "./Bolt";
import { HoldingBreakdown, ProbabilityBar } from "./HoldingBreakdown";
import { SentimentGauge } from "./SentimentGauge";

interface Props {
  response: AnalyzeResponse | null;
  news: string; // the story the response is about
  loading: boolean;
}

/** Two grid cards that share the engine switch: the score in the middle, the per-holding detail on the right. */
export function ResultPanel({ response, news, loading }: Props) {
  const results = response?.results ?? [];
  const [selected, setSelected] = useState<EngineName | null>(null);
  useEffect(() => setSelected(results[0]?.engine ?? null), [response]);

  const result = results.find((r) => r.engine === selected) ?? results[0];
  const scored = !loading && result && result.status !== "error" ? result : null;

  return (
    <>
      <section className="card result" aria-live="polite" aria-busy={loading}>
        <div className="result-head">
          <h2 className="title-with-bolt">
            Portfolio sentiment
            <Bolt className="title-bolt" />
          </h2>
          {results.length > 1 && (
            <div className="engine-switch" role="tablist" aria-label="Engine">
              {results.map((r) => (
                <button
                  key={r.engine}
                  role="tab"
                  aria-selected={r.engine === result?.engine}
                  onClick={() => setSelected(r.engine)}
                >
                  <span>{ENGINE_NAMES[r.engine]}</span>
                  <strong className={r.score !== null ? `tone-text-${zoneFor(r.score).tone}` : "muted"}>
                    {r.status === "ok" ? r.score : r.status === "unrelated" ? "n/a" : "error"}
                  </strong>
                </button>
              ))}
            </div>
          )}
        </div>

        {loading ? (
          <SentimentGauge score={null} caption="Reading the article…" />
        ) : !result ? (
          <>
            <SentimentGauge score={null} />
            <p className="result-empty">
              Add your holdings, paste a news story, and select Analyze to see how it lands on your portfolio.
            </p>
          </>
        ) : (
          <Verdict result={result} news={news} weightsAdjusted={response!.weights_adjusted} />
        )}
      </section>

      <section className="card detail">
        <h2>By holding</h2>
        {scored ? (
          <Detail result={scored} />
        ) : (
          <p className="result-empty">Each holding's score and the reason for it appear here.</p>
        )}
      </section>
    </>
  );
}

function Verdict({ result, news, weightsAdjusted }: { result: PortfolioResult; news: string; weightsAdjusted: boolean }) {
  if (result.status === "error") {
    return (
      <>
        <SentimentGauge score={null} caption="No score" />
        <p className="notice notice-error">{result.error}</p>
      </>
    );
  }

  const skipped = skippedNotice(result);
  const language = languageNotice(result, news);

  if (result.status === "unrelated") {
    return (
      <>
        <SentimentGauge score={null} caption="Not related" />
        <p className="result-empty">
          {skipped ? "This story doesn't touch any of the holdings that were assessed." : "This story doesn't touch any of your holdings."}
        </p>
        {language && <p className="notice">{language}</p>}
        {skipped && <p className="notice">{skipped}</p>}
        {result.engine === "finbert" && (
          <p className="notice">
            FinBERT only counts companies the article names. Claude can also pick up indirect effects, such as
            commodity prices or interest rates.
          </p>
        )}
      </>
    );
  }

  const related = result.holdings.filter((h) => h.relevant).length;
  return (
    <>
      <SentimentGauge score={result.score} />
      <div className="verdict">
        <ProbabilityBar bullish={result.bullish!} neutral={result.neutral!} bearish={result.bearish!} />
        <dl className="verdict-probs">
          <div>
            <dt>Bullish</dt>
            <dd className="tone-text-bull-strong">{pct(result.bullish!)}</dd>
          </div>
          <div>
            <dt>Neutral</dt>
            <dd>{pct(result.neutral!)}</dd>
          </div>
          <div>
            <dt>Bearish</dt>
            <dd className="tone-text-bear-strong">{pct(result.bearish!)}</dd>
          </div>
        </dl>
        <p className="exposure">
          Affects <strong>{pct(result.exposure)}</strong> of your portfolio ({related} of {result.holdings.length}{" "}
          holdings). Holdings the story doesn't touch are left out of the score.
        </p>
        {language && <p className="notice">{language}</p>}
        {skipped && <p className="notice">{skipped}</p>}
        {weightsAdjusted && <p className="notice">Your weights didn't add up to 100%, so they were scaled to fit.</p>}
      </div>

      {result.summary && <p className="summary">{result.summary}</p>}
    </>
  );
}

function Detail({ result }: { result: PortfolioResult }) {
  return (
    <>
      <HoldingBreakdown holdings={result.holdings} />
      {result.status === "ok" && (
        <>
          <Extras result={result} />
          <HowItsScored result={result} />
        </>
      )}
    </>
  );
}

function Extras({ result }: { result: PortfolioResult }) {
  const lists: [string, string[]][] = [
    ["Key points", result.key_points],
    ["Risks", result.risks],
    ["What to watch", result.watch_items],
  ];
  if (!lists.some(([, items]) => items.length) && !result.time_horizon.length) return null;
  return (
    <div className="extras">
      {result.time_horizon.length > 0 && (
        <p className="muted">
          Likely time frame: {result.time_horizon.map((t) => `${t} term`).join(", ")}
        </p>
      )}
      {lists.map(
        ([title, items]) =>
          items.length > 0 && (
            <div key={title}>
              <h3>{title}</h3>
              <ul>
                {items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ),
      )}
    </div>
  );
}

function HowItsScored({ result }: { result: PortfolioResult }) {
  const related = result.holdings.filter((h) => h.relevant);
  const net = result.bullish! - result.bearish!;
  return (
    <details className="how">
      <summary>How this score was worked out</summary>
      <ol>
        <li>
          {ENGINE_NAMES[result.engine]} rated each holding as bullish, neutral, or bearish.
          {result.engine === "finbert"
            ? " FinBERT only reads the sentences that name the company."
            : " Claude also looks for indirect effects."}
        </li>
        <li>
          Holdings the story doesn't touch were dropped, and the rest were reweighted to add up to 100%:{" "}
          {related.map((h) => `${h.ticker} ${pct(h.effective_weight)}`).join(", ")}.
        </li>
        <li>
          Those weights averaged the holdings into {pct(result.bullish!)} bullish and {pct(result.bearish!)} bearish.
        </li>
        <li>
          Score = 50 + 50 × (bullish − bearish) = 50 + 50 × {signedPct(net)} = <strong>{result.score}</strong>.
          Below 40 reads as bearish, above 60 as bullish.
        </li>
      </ol>
    </details>
  );
}
