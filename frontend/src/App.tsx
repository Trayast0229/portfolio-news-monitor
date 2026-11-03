import { useEffect, useRef, useState } from "react";
import { Bolt } from "./components/Bolt";
import { HistoryList } from "./components/HistoryList";
import { HoldingsEditor } from "./components/HoldingsEditor";
import { ResultPanel } from "./components/ResultPanel";
import {
  ENGINE_NAMES,
  analyze,
  fetchArticle,
  watchHealth,
  type AnalyzeResponse,
  type EngineName,
  type EngineStatus,
  type HoldingInput,
} from "./lib/api";
import { EXAMPLES } from "./lib/examples";
import { storySource } from "./lib/history";
import { filledHoldings, holdingsProblem } from "./lib/holdings";
import {
  addHistory,
  clearHistory,
  loadEngines,
  loadHistory,
  loadHoldings,
  saveEngines,
  saveHoldings,
  type HistoryEntry,
} from "./lib/storage";

const MIN_NEWS = 50;
const MAX_NEWS = 20000;

const ENGINE_HINTS: Record<EngineName, string> = {
  claude: "Reads the story like an analyst, including indirect effects.",
  finbert: "Free and local. Scores only sentences that name your companies.",
};

function validate(holdings: HoldingInput[], news: string, engines: EngineName[]): string | null {
  const problem = holdingsProblem(holdings);
  if (problem) return problem;
  if (news.trim().length < MIN_NEWS) return `Paste a longer story. It needs at least ${MIN_NEWS} characters.`;
  if (!engines.length) return "Choose at least one engine.";
  return null;
}

export default function App() {
  const [holdings, setHoldings] = useState<HoldingInput[]>(loadHoldings);
  const [news, setNews] = useState("");
  const [articleUrl, setArticleUrl] = useState("");
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [fetchNote, setFetchNote] = useState<string | null>(null);
  const [engines, setEngines] = useState<EngineName[]>(loadEngines);
  const [status, setStatus] = useState<Partial<Record<EngineName, EngineStatus>>>({});
  // The result on screen and the story it's about, which may differ from the text box by now.
  const [shown, setShown] = useState<{ news: string; response: AnalyzeResponse } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory);
  const [fetched, setFetched] = useState<{ url: string; text: string } | null>(null);
  // Lets a slow reply notice that the form moved on. Any edit makes a pending
  // fetch stale; only swapping in a whole new story makes a pending analysis stale.
  const edits = useRef({ story: 0, swaps: 0 });
  const editStory = () => (edits.current.story += 1);
  const swapStory = () => {
    edits.current.story += 1;
    edits.current.swaps += 1;
  };

  useEffect(() => saveHoldings(holdings), [holdings]);
  useEffect(() => saveEngines(engines), [engines]);

  useEffect(() => watchHealth(setStatus), []);

  function toggleEngine(name: EngineName) {
    setEngines((prev) => (prev.includes(name) ? prev.filter((e) => e !== name) : [...prev, name]));
  }

  async function fetchStory() {
    if (fetching) return;
    if (!articleUrl.trim()) return setFetchError("Paste a link to a news article first.");
    setFetching(true);
    setFetchError(null);
    setFetchNote(null);
    const story = edits.current.story;
    try {
      const article = await fetchArticle(articleUrl.trim());
      if (edits.current.story !== story) return;
      swapStory();
      setNews(article.text);
      setArticleUrl(article.url);
      setFetched({ url: article.url, text: article.text });
      if (article.truncated)
        setFetchNote(`The article was long, so we kept the first ${MAX_NEWS.toLocaleString()} characters.`);
    } catch (e) {
      if (edits.current.story !== story) return;
      setFetchError(e instanceof Error ? e.message : "We couldn't fetch that article. Paste the text instead.");
    } finally {
      setFetching(false);
    }
  }

  function pickSample(text: string) {
    swapStory();
    setFetched(null);
    setNews(text);
    setArticleUrl("");
    setFetchError(null);
    setFetchNote(null);
  }

  async function run() {
    const problem = validate(holdings, news, engines);
    setError(problem);
    if (problem) return;
    const cleaned = filledHoldings(holdings);
    const swaps = edits.current.swaps;
    const isCurrent = () => edits.current.swaps === swaps;
    setLoading(true);
    try {
      const res = await analyze(cleaned, news.trim(), engines);
      const url = storySource(fetched, articleUrl, news);
      setHistory(addHistory({ news: news.trim(), url, holdings: cleaned, response: res }));
      // The run is saved either way, but its result no longer matches the form.
      if (!isCurrent()) return;
      setShown({ news: news.trim(), response: res });
      // On a single-column layout the result sits below the form.
      if (window.matchMedia("(max-width: 860px)").matches) {
        document.querySelector(".result")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (e) {
      if (isCurrent()) setError(e instanceof Error ? e.message : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  function openHistory(entry: HistoryEntry) {
    swapStory();
    setFetched(entry.url ? { url: entry.url, text: entry.news } : null);
    setHoldings(entry.holdings);
    setNews(entry.news);
    setArticleUrl(entry.url ?? "");
    setFetchError(null);
    setFetchNote(null);
    setShown({ news: entry.news, response: entry.response });
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="page">
      <header className="masthead">
        <h1 className="brand">
          <span className="logo">
            <Bolt />
          </span>
          Portfolio News Monitor
        </h1>
        <p>Paste a news story and see whether it's good or bad for your ASX portfolio, weighted by what you hold.</p>
      </header>

      <main className="layout">
        <div className="inputs">
          <HoldingsEditor holdings={holdings} onChange={setHoldings} />

          <div className="news">
            <label htmlFor="news">News story</label>
            <div className="article-link">
              <input
                type="url"
                aria-label="Article link"
                placeholder="Paste a link to a news article"
                value={articleUrl}
                autoComplete="off"
                spellCheck={false}
                onChange={(e) => {
                  editStory();
                  setArticleUrl(e.target.value);
                  setFetchError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    fetchStory();
                  }
                }}
              />
              <button type="button" className="secondary" onClick={fetchStory} disabled={fetching}>
                {fetching ? "Fetching…" : "Fetch"}
              </button>
            </div>
            {fetchError && (
              <p className="notice notice-error small" role="alert">
                {fetchError}
              </p>
            )}
            <textarea
              id="news"
              value={news}
              maxLength={MAX_NEWS}
              rows={9}
              placeholder="Or paste the headline and article text here."
              onChange={(e) => {
                editStory();
                setNews(e.target.value);
              }}
            />
            <div className="news-foot">
              <div className="samples">
                <span className="muted">Try a sample:</span>
                {EXAMPLES.map((ex) => (
                  <button key={ex.title} type="button" className="chip" onClick={() => pickSample(ex.text)}>
                    {ex.title}
                  </button>
                ))}
              </div>
              <span className="muted">{news.length.toLocaleString()} characters</span>
            </div>
            {fetchNote && <p className="muted small">{fetchNote}</p>}
            <p className="muted small">
              Sample stories are made up for demonstration. Sites with a paywall or bot protection can't be fetched, so
              paste their text instead.
            </p>
          </div>

          <fieldset className="engines">
            <legend>Engine</legend>
            {(Object.keys(ENGINE_NAMES) as EngineName[]).map((name) => (
              <div key={name} className="engine">
                <button
                  type="button"
                  className="engine-toggle"
                  aria-pressed={engines.includes(name)}
                  onClick={() => toggleEngine(name)}
                >
                  <span className="engine-check" aria-hidden="true" />
                  <span>
                    <strong>{ENGINE_NAMES[name]}</strong>
                    <span className="muted">{ENGINE_HINTS[name]}</span>
                  </span>
                </button>
                {engines.includes(name) && <EngineNote name={name} status={status[name]} />}
              </div>
            ))}
            {engines.length === 2 && <p className="muted small">Both engines run side by side so you can compare them.</p>}
          </fieldset>

          {error && (
            <p className="notice notice-error" role="alert">
              {error}
            </p>
          )}
          <button type="button" className="primary" onClick={run} disabled={loading}>
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </div>

        <ResultPanel response={shown?.response ?? null} news={shown?.news ?? ""} loading={loading} />
      </main>

      <HistoryList entries={history} onOpen={openHistory} onClear={() => setHistory(clearHistory())} />

      <footer className="footer">
        For research and education only. Not investment advice. ASX company list from asx.com.au.
      </footer>
    </div>
  );
}

function EngineNote({ name, status }: { name: EngineName; status?: EngineStatus }) {
  if (name === "claude" && status === "unavailable")
    return (
      <p className="notice small">
        Claude needs an API key. Add <code>ANTHROPIC_API_KEY</code> to <code>backend/.env</code> and restart the
        backend. You can get a key at console.anthropic.com.
      </p>
    );
  if (name === "finbert" && status === "not_loaded")
    return <p className="notice small">FinBERT is loading. The first run downloads the model, which can take a minute.</p>;
  if (name === "finbert" && status === "unavailable")
    return (
      <p className="notice small">
        FinBERT isn't installed. Run <code>pip install -e '.[finbert]'</code> in <code>backend</code>.
      </p>
    );
  return null;
}
