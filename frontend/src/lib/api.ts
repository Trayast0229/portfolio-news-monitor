import type { Label } from "./gauge";

export type EngineName = "claude" | "finbert";
export type EngineStatus = "ready" | "not_loaded" | "unavailable";

export interface HoldingInput {
  ticker: string;
  weight: number;
}

export interface HoldingScore {
  ticker: string;
  name: string | null;
  weight: number;
  relevant: boolean;
  assessed?: boolean; // missing in history saved before it existed
  effective_weight: number;
  bullish: number | null;
  neutral: number | null;
  bearish: number | null;
  score: number | null;
  label: Label | null;
  reason: string;
  confidence: number | null;
}

export interface PortfolioResult {
  engine: EngineName;
  status: "ok" | "unrelated" | "error";
  score: number | null;
  label: Label | null;
  bullish: number | null;
  neutral: number | null;
  bearish: number | null;
  exposure: number;
  holdings: HoldingScore[];
  summary: string | null;
  key_points: string[];
  time_horizon: string[];
  risks: string[];
  watch_items: string[];
  error: string | null;
}

export interface AnalyzeResponse {
  weights_adjusted: boolean;
  results: PortfolioResult[];
}

export interface TickerMatch {
  ticker: string;
  name: string;
}

export const ENGINE_NAMES: Record<EngineName, string> = { claude: "Claude", finbert: "FinBERT" };

// Analyze gets longer because Claude can retry a slow call. A rare run that
// needs more, such as FinBERT's first model download, shows the timeout
// message and can be run again.
const TIMEOUT_MS = 30_000;
const ANALYZE_TIMEOUT_MS = 2 * 60_000;

// Visitors to the live site can't start the backend, so the port hint is for development only.
const BACKEND_HINT = import.meta.env.DEV ? " In development, make sure the backend is running on port 8000." : "";

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = TIMEOUT_MS): Promise<T> {
  const ctrl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    ctrl.abort();
  }, timeoutMs);
  const cancel = () => ctrl.abort();
  if (init.signal?.aborted) cancel();
  init.signal?.addEventListener("abort", cancel, { once: true });
  try {
    return await send<T>(path, { ...init, signal: ctrl.signal });
  } catch (e) {
    if (timedOut) throw new Error("The analysis server took too long to answer. Try again.");
    throw e;
  } finally {
    clearTimeout(timer);
    init.signal?.removeEventListener("abort", cancel);
  }
}

// Sends one request and reads the reply, body included, so the timeout and
// the caller's cancel in `request` cover a reply that stalls halfway too.
async function send<T>(path: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new Error(`Can't reach the analysis server. Check your connection and try again.${BACKEND_HINT}`);
  }
  if (!res.ok) {
    // The dev proxy answers 5xx with a plain-text body when the backend is down.
    let detail =
      res.status >= 500
        ? `The analysis server isn't available right now. Try again in a few minutes.${BACKEND_HINT}`
        : `The server returned an error (${res.status}).`;
    try {
      const body = await res.json();
      const first = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
      if (first) detail = String(first).replace(/^Value error, /, "");
    } catch {
      // keep the generic message
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function getHealth() {
  return request<{ engines: Record<EngineName, EngineStatus> }>("/api/health");
}

export function searchTickers(q: string, signal?: AbortSignal) {
  return request<TickerMatch[]>(`/api/tickers?q=${encodeURIComponent(q)}`, { signal });
}

export function analyze(holdings: HoldingInput[], news: string, engines: EngineName[]) {
  return request<AnalyzeResponse>(
    "/api/analyze",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ holdings, news, engines }),
    },
    ANALYZE_TIMEOUT_MS,
  );
}

export interface Article {
  url: string;
  title: string | null;
  text: string;
  truncated: boolean;
}

export function fetchArticle(url: string) {
  return request<Article>("/api/article", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}
