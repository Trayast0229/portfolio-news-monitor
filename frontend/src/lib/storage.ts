// Browser-only conveniences. Storage can be missing or throw (private mode,
// blocked site data), so every access falls back quietly.

import { ENGINE_NAMES, type AnalyzeResponse, type EngineName, type HoldingInput, type PortfolioResult } from "./api";
import { mergeHistory } from "./history";

const HOLDINGS_KEY = "pnm.holdings";
const ENGINES_KEY = "pnm.engines";
const HISTORY_KEY = "pnm.history";
const HISTORY_LIMIT = 20;

export interface HistoryEntry {
  id: string;
  at: string;
  news: string;
  /** The article link the story was fetched from, if any. */
  url?: string;
  holdings: HoldingInput[];
  response: AnalyzeResponse;
}

// Saved data can be from an older version or edited by hand, so `parse` gets
// whatever JSON is there and returns null when it can't be used.
function read<T>(key: string, fallback: T, parse: (value: unknown) => T | null): T {
  try {
    const raw = localStorage.getItem(key);
    return (raw ? parse(JSON.parse(raw)) : null) ?? fallback;
  } catch {
    return fallback;
  }
}

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;

function parseHolding(v: unknown): HoldingInput | null {
  if (!isObject(v) || typeof v.ticker !== "string") return null;
  // A cleared weight is NaN in the app, which JSON saves as null.
  if (v.weight === null) return { ticker: v.ticker, weight: NaN };
  return typeof v.weight === "number" ? { ticker: v.ticker, weight: v.weight } : null;
}

function parseHoldings(v: unknown): HoldingInput[] | null {
  if (!Array.isArray(v)) return null;
  const holdings = v.map(parseHolding);
  return holdings.every((h) => h !== null) ? holdings : null;
}

const isEngine = (v: unknown): v is EngineName => typeof v === "string" && Object.hasOwn(ENGINE_NAMES, v);

// Checks the fields the history list and result panel read.
function isResult(v: unknown): v is PortfolioResult {
  return (
    isObject(v) &&
    isEngine(v.engine) &&
    ["ok", "unrelated", "error"].includes(v.status as string) &&
    ["holdings", "key_points", "time_horizon", "risks", "watch_items"].every((k) => Array.isArray(v[k]))
  );
}

function parseEntry(v: unknown): HistoryEntry | null {
  if (!isObject(v) || !isObject(v.response) || !Array.isArray(v.response.results)) return null;
  const holdings = parseHoldings(v.holdings);
  const ok =
    typeof v.id === "string" &&
    typeof v.at === "string" &&
    typeof v.news === "string" &&
    (v.url === undefined || typeof v.url === "string") &&
    holdings !== null &&
    v.response.results.every(isResult);
  return ok ? ({ ...v, holdings } as HistoryEntry) : null;
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage full or unavailable; nothing to do
  }
}

export const DEFAULT_HOLDINGS: HoldingInput[] = [
  { ticker: "BHP", weight: 40 },
  { ticker: "CBA", weight: 30 },
  { ticker: "CSL", weight: 30 },
];

export const loadHoldings = () => read(HOLDINGS_KEY, DEFAULT_HOLDINGS, parseHoldings);
export const saveHoldings = (h: HoldingInput[]) => write(HOLDINGS_KEY, h);

function parseEngines(v: unknown): EngineName[] | null {
  if (!Array.isArray(v)) return null;
  const engines = [...new Set(v.filter(isEngine))];
  // An empty list is a real choice; a list of only unknown names is not.
  return engines.length || !v.length ? engines : null;
}

export const loadEngines = () => read<EngineName[]>(ENGINES_KEY, ["finbert"], parseEngines);
export const saveEngines = (e: EngineName[]) => write(ENGINES_KEY, e);

export const loadHistory = () =>
  read<HistoryEntry[]>(HISTORY_KEY, [], (v) =>
    Array.isArray(v) ? v.map(parseEntry).filter((e): e is HistoryEntry => e !== null) : null,
  );

export function addHistory(entry: Omit<HistoryEntry, "id" | "at">): HistoryEntry[] {
  const full: HistoryEntry = { ...entry, id: crypto.randomUUID(), at: new Date().toISOString() };
  const next = mergeHistory(loadHistory(), full, HISTORY_LIMIT);
  write(HISTORY_KEY, next);
  return next;
}

export function clearHistory(): HistoryEntry[] {
  write(HISTORY_KEY, []);
  return [];
}
