import { ENGINE_NAMES } from "../lib/api";
import { timeAgo } from "../lib/format";
import { historyScore } from "../lib/history";
import type { HistoryEntry } from "../lib/storage";

interface ToggleProps {
  count: number;
  open: boolean;
  onToggle: () => void;
}

export function HistoryToggle({ count, open, onToggle }: ToggleProps) {
  if (!count) return null;
  return (
    <button
      type="button"
      className="history-toggle"
      aria-expanded={open}
      aria-controls="history"
      onClick={onToggle}
    >
      Recent analyses
      <span className="history-count">{count}</span>
      <svg className="history-caret" viewBox="0 0 12 12" aria-hidden="true" focusable="false">
        <path d="m2.5 4.5 3.5 3.5 3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      </svg>
    </button>
  );
}

interface Props {
  entries: HistoryEntry[];
  onOpen: (entry: HistoryEntry) => void;
  onClear: () => void;
}

export function HistoryList({ entries, onOpen, onClear }: Props) {
  return (
    <section id="history" className="history" aria-label="Recent analyses">
      <div className="history-head">
        <span className="muted">Newest first. Saved in this browser only.</span>
        <button type="button" className="text-button" onClick={onClear}>
          Clear
        </button>
      </div>
      <ul>
        {entries.map((e) => (
          <li key={e.id}>
            <button type="button" onClick={() => onOpen(e)}>
              <span className="history-text">{e.news.slice(0, 140)}</span>
              <span className="history-meta">
                <span className="muted">{timeAgo(e.at)}</span>
                {e.response.results.map((r) => {
                  const s = historyScore(r);
                  return (
                    <span key={r.engine} className="history-score" title={s.title}>
                      {ENGINE_NAMES[r.engine]} <strong className={s.className}>{s.text}</strong>
                    </span>
                  );
                })}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
