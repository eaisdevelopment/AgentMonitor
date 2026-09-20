import { getFoundationShellState } from "../shared/api/client";

export function App() {
  const state = getFoundationShellState();

  return (
    <main className="foundation-shell">
      <section aria-labelledby="agentmonitor-title" className="foundation-card">
        <p className="foundation-eyebrow">Local foundation</p>
        <h1 id="agentmonitor-title">AgentMonitor</h1>
        <p>{state.message}</p>
        <p className="foundation-build">Build {state.applicationVersion}</p>
      </section>
    </main>
  );
}
