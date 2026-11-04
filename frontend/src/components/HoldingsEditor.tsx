import { useEffect, useRef, useState } from "react";
import { searchTickers, type HoldingInput, type TickerMatch } from "../lib/api";
import { lookUpName, namesFromSearch, tickerNote, tickersToLookUp, type CompanyNames } from "../lib/history";
import { weightTotal } from "../lib/holdings";

interface Props {
  holdings: HoldingInput[];
  onChange: (holdings: HoldingInput[]) => void;
}

const MAX_HOLDINGS = 30;

export function HoldingsEditor({ holdings, onChange }: Props) {
  const [names, setNames] = useState<CompanyNames>({});
  const [suggestions, setSuggestions] = useState<TickerMatch[]>([]);
  const abort = useRef<AbortController | null>(null);
  const requested = useRef(new Set<string>());

  const remember = (query: string) => (matches: TickerMatch[]) =>
    setNames((prev) => ({ ...prev, ...namesFromSearch(query, matches) }));

  // Look up names for holdings set from outside, such as storage or a history entry.
  const tickers = holdings.map((h) => h.ticker).join(",");
  useEffect(() => {
    tickersToLookUp(holdings, requested.current).forEach((t) => {
      requested.current.add(t);
      lookUpName(t, searchTickers, remember(t));
    });
  }, [tickers]);

  function lookup(q: string) {
    requested.current.add(q.trim());
    abort.current?.abort();
    if (!q.trim()) return setSuggestions([]);
    const ctrl = new AbortController();
    abort.current = ctrl;
    searchTickers(q, ctrl.signal)
      .then((m) => {
        setSuggestions(m);
        remember(q.trim())(m);
      })
      .catch(() => {
        if (!ctrl.signal.aborted) lookUpName(q.trim(), searchTickers, remember(q.trim()));
      });
  }

  const update = (i: number, patch: Partial<HoldingInput>) =>
    onChange(holdings.map((h, j) => (j === i ? { ...h, ...patch } : h)));

  const total = weightTotal(holdings);
  const offBy = Math.abs(total - 100) > 0.5;

  return (
    <fieldset className="holdings">
      <legend>Your holdings</legend>
      <datalist id="asx-tickers">
        {suggestions.map((s) => (
          <option key={s.ticker} value={s.ticker}>
            {s.name}
          </option>
        ))}
      </datalist>
      <div className="holdings-cols muted" aria-hidden="true">
        <span>ASX code</span>
        <span>Weight</span>
      </div>
      <ul>
        {holdings.map((h, i) => (
          <li key={i} className="holding-row">
            <div className="ticker-cell">
              <input
                aria-label={`Holding ${i + 1} ASX code`}
                list="asx-tickers"
                value={h.ticker}
                placeholder="BHP"
                maxLength={8}
                autoComplete="off"
                spellCheck={false}
                onChange={(e) => {
                  const ticker = e.target.value.toUpperCase();
                  update(i, { ticker });
                  lookup(ticker);
                }}
              />
              <span className="ticker-name muted">{tickerNote(h.ticker, names)}</span>
            </div>
            <div className="weight-cell">
              <input
                aria-label={`Holding ${i + 1} weight in percent`}
                type="number"
                inputMode="decimal"
                min={0}
                max={100}
                step={1}
                value={Number.isFinite(h.weight) ? h.weight : ""}
                onChange={(e) => update(i, { weight: e.target.value === "" ? NaN : Number(e.target.value) })}
              />
              <span aria-hidden="true">%</span>
            </div>
            <button
              type="button"
              className="icon-button"
              aria-label={`Remove ${h.ticker || `holding ${i + 1}`}`}
              onClick={() => onChange(holdings.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <div className="holdings-foot">
        <button
          type="button"
          className="text-button"
          onClick={() => holdings.length < MAX_HOLDINGS && onChange([...holdings, { ticker: "", weight: NaN }])}
        >
          Add holding
        </button>
        <span className={offBy ? "total total-off" : "total muted"}>
          Total {Math.round(total * 10) / 10}%{offBy && ". We'll scale it to 100%."}
        </span>
      </div>
    </fieldset>
  );
}
