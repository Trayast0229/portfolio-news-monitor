import { ENGINE_NAMES, type EngineName, type EngineStatus } from "./api";

type Statuses = Partial<Record<EngineName, EngineStatus>>;

// Until the first health check answers, every engine counts as usable.
export const isUsable = (name: EngineName, status: Statuses): boolean => status[name] !== "unavailable";

// The engines to run: what the visitor chose, minus any the server can't run. The choice
// itself stays saved, so Claude comes back once a key is added.
export const usableEngines = (chosen: EngineName[], status: Statuses): EngineName[] =>
  chosen.filter((name) => isUsable(name, status));

// What to tell the visitor when there is nothing to run, or null when there is.
export function engineProblem(chosen: EngineName[], status: Statuses): string | null {
  const all = Object.keys(ENGINE_NAMES) as EngineName[];
  // Every toggle is greyed out then, so asking for a choice would point at nothing.
  if (!all.some((name) => isUsable(name, status))) return "No engine is available right now. Try again later.";
  return usableEngines(chosen, status).length ? null : "Choose at least one engine.";
}
