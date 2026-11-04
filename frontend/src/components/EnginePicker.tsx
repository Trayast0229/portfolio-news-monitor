import { BACKEND_HINT, ENGINE_NAMES, type EngineName, type EngineStatus } from "../lib/api";
import { isUsable, usableEngines } from "../lib/engines";
import { Bolt } from "./Bolt";

const ENGINE_HINTS: Record<EngineName, string> = {
  claude: "Reads the story like an analyst, including indirect effects.",
  finbert: "Free. Scores only sentences that name your companies.",
};

const UNAVAILABLE_HINTS: Record<EngineName, string> = {
  claude: "Available when you run the project locally.",
  finbert: "Not available right now. Try again later.",
};

interface Props {
  engines: EngineName[];
  status: Partial<Record<EngineName, EngineStatus>>;
  waking: boolean; // the server hasn't answered its first health check after a few seconds
  onToggle: (name: EngineName) => void;
  error: string | null;
  loading: boolean;
  onAnalyze: () => void;
}

export function EnginePicker({ engines, status, waking, onToggle, error, loading, onAnalyze }: Props) {
  const names = Object.keys(ENGINE_NAMES) as EngineName[];
  const chosen = usableEngines(engines, status);
  return (
    <section className="card engine-card">
      <fieldset className="engines">
        <legend>Engine</legend>
        {names.map((name) => {
          const usable = isUsable(name, status);
          return (
            <div key={name} className="engine">
              <button
                type="button"
                className="engine-toggle"
                aria-pressed={chosen.includes(name)}
                disabled={!usable}
                onClick={() => onToggle(name)}
              >
                <span className="engine-check" aria-hidden="true" />
                <span>
                  <strong>{ENGINE_NAMES[name]}</strong>
                  <span className="muted">{usable ? ENGINE_HINTS[name] : UNAVAILABLE_HINTS[name]}</span>
                </span>
              </button>
              <EngineNote name={name} status={status[name]} chosen={chosen.includes(name)} />
            </div>
          );
        })}
        {chosen.length === 2 && <p className="muted small">Both engines run side by side so you can compare them.</p>}
      </fieldset>

      {waking && (
        <p className="notice small" role="status">
          Waking up the analysis server. The first visit can take up to a minute.{BACKEND_HINT}
        </p>
      )}
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      <button type="button" className="primary" onClick={onAnalyze} disabled={loading}>
        <Bolt className="button-bolt" />
        {loading ? "Analyzing…" : "Analyze"}
      </button>
    </section>
  );
}

// Setup steps only make sense to someone running the project, so the live site leaves them out.
function EngineNote({ name, status, chosen }: { name: EngineName; status?: EngineStatus; chosen: boolean }) {
  if (name === "finbert" && status === "not_loaded" && chosen)
    return <p className="notice small">FinBERT is starting up, which can take a minute.</p>;
  if (!import.meta.env.DEV || status !== "unavailable") return null;
  if (name === "claude")
    return (
      <p className="notice small">
        Claude needs an API key. Add <code>ANTHROPIC_API_KEY</code> to <code>backend/.env</code>, restart the
        backend, then reload this page. You can get a key at console.anthropic.com.
      </p>
    );
  return (
    <p className="notice small">
      FinBERT isn't installed. Run <code>pip install -e '.[finbert]'</code> in <code>backend</code>.
    </p>
  );
}
