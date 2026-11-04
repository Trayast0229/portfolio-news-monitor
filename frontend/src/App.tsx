import { useEffect, useRef, useState } from "react";
import { Bolt } from "./components/Bolt";
import { EnginePicker } from "./components/EnginePicker";
import { HistoryList, HistoryToggle } from "./components/HistoryList";
import { HoldingsEditor } from "./components/HoldingsEditor";
import { ResultPanel } from "./components/ResultPanel";
import {
  analyze,
  fetchArticle,
  watchHealth,
  type AnalyzeResponse,
  type EngineName,
  type EngineStatus,
  type HoldingInput,
} from "./lib/api";
import { engineProblem, usableEngines } from "./lib/engines";
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
// Below this width the cards stack in one column (matches styles.css).
const ONE_COLUMN = "(max-width: 1024px)";

function validate(holdings: HoldingInput[], news: string, engineIssue: string | null): string | null {
  const problem = holdingsProblem(holdings);
  if (problem) return problem;
  if (news.trim().length < MIN_NEWS) return `Paste a longer story. It needs at least ${MIN_NEWS} characters.`;
  return engineIssue;
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
  const [historyOpen, setHistoryOpen] = useState(false);
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
    const chosen = usableEngines(engines, status);
    const problem = validate(holdings, news, engineProblem(engines, status));
    setError(problem);
    if (problem) return;
    const cleaned = filledHoldings(holdings);
    const swaps = edits.current.swaps;
    const isCurrent = () => edits.current.swaps === swaps;
    setLoading(true);
    try {
      const res = await analyze(cleaned, news.trim(), chosen);
      const url = storySource(fetched, articleUrl, news);
      setHistory(addHistory({ news: news.trim(), url, holdings: cleaned, response: res }));
      // The run is saved either way, but its result no longer matches the form.
      if (!isCurrent()) return;
      setShown({ news: news.trim(), response: res });
      // On a single-column layout the result sits below the form.
      if (window.matchMedia(ONE_COLUMN).matches) {
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
    setHistoryOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="page">
      <header className="topbar">
        <h1 className="brand">
          <span className="logo">
            <Bolt />
          </span>
          Portfolio News Monitor
        </h1>
        <HistoryToggle count={history.length} open={historyOpen} onToggle={() => setHistoryOpen((o) => !o)} />
      </header>

      {historyOpen && history.length > 0 && (
        <HistoryList
          entries={history}
          onOpen={openHistory}
          onClear={() => {
            setHistory(clearHistory());
            setHistoryOpen(false);
          }}
        />
      )}

      <main className="layout">
        <section className="card holdings-card">
          <HoldingsEditor holdings={holdings} onChange={setHoldings} />
        </section>

        <div className="hero">
          <Bolt className="hero-bolt" />
          <p className="headline">
            <span className="underline">Efficiency</span> drives progress.
          </p>
          <p className="muted">Paste a news story and see whether it's good or bad for your ASX portfolio.</p>
        </div>

        <section className="card news">
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
            rows={11}
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
        </section>

        {/* After the story in the DOM so Tab follows holdings -> story -> engines; the grid places it top right. */}
        <EnginePicker
          engines={engines}
          status={status}
          onToggle={toggleEngine}
          error={error}
          loading={loading}
          onAnalyze={run}
        />

        <ResultPanel response={shown?.response ?? null} news={shown?.news ?? ""} loading={loading} />
      </main>

      <footer className="footer">
        For research and education only. Not investment advice. ASX company list from asx.com.au.
      </footer>
    </div>
  );
}
