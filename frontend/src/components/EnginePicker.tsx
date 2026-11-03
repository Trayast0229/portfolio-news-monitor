import { ENGINE_NAMES, type EngineName, type EngineStatus } from "../lib/api";

const ENGINE_HINTS: Record<EngineName, string> = {
  claude: "Reads the story like an analyst, including indirect effects.",
  finbert: "Free and local. Scores only sentences that name your companies.",
};

interface Props {
  engines: EngineName[];
  status: Partial<Record<EngineName, EngineStatus>>;
  onToggle: (name: EngineName) => void;
  error: string | null;
  loading: boolean;
  onAnalyze: () => void;
}

export function EnginePicker({ engines, status, onToggle, error, loading, onAnalyze }: Props) {
  return (
    <section className="card engine-card">
      <fieldset className="engines">
        <legend>Engine</legend>
        {(Object.keys(ENGINE_NAMES) as EngineName[]).map((name) => (
          <div key={name} className="engine">
            <button
              type="button"
              className="engine-toggle"
              aria-pressed={engines.includes(name)}
              onClick={() => onToggle(name)}
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
      <button type="button" className="primary" onClick={onAnalyze} disabled={loading}>
        {loading ? "Analyzing…" : "Analyze"}
      </button>
    </section>
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
