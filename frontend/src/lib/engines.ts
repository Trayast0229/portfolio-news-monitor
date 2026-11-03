import type { EngineName, EngineStatus } from "./api";

type Statuses = Partial<Record<EngineName, EngineStatus>>;

// Until the first health check answers, every engine counts as usable.
export const isUsable = (name: EngineName, status: Statuses): boolean => status[name] !== "unavailable";

// The engines to run: what the visitor chose, minus any the server can't run. The choice
// itself stays saved, so Claude comes back once a key is added.
export const usableEngines = (chosen: EngineName[], status: Statuses): EngineName[] =>
  chosen.filter((name) => isUsable(name, status));
