import { useEffect, useState } from "react";

import { runtime, type LiveProcessLocationPageV1 } from "../../shared/api/client";

export function LiveClaudeProcesses({ onExpired }: Readonly<{ onExpired: () => void }>) {
  const [data, setData] = useState<LiveProcessLocationPageV1 | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let refreshing = false;
    const refresh = async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const result = await runtime.processLocations(controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") onExpired();
          setFailed(true);
          return;
        }
        setData(result.data);
        setFailed(false);
      } catch {
        if (!controller.signal.aborted) setFailed(true);
      } finally { refreshing = false; }
    };
    void refresh();
    const interval = window.setInterval(() => { void refresh(); }, 30_000);
    return () => { controller.abort(); window.clearInterval(interval); };
  }, [onExpired]);
  const unavailable = failed || (data !== null && data.availability.state !== "available");
  return (
    <section className="account-workspace live-processes" aria-labelledby="live-processes-title">
      <div className="workspace-heading">
        <div><h2 id="live-processes-title">Claude on this workstation</h2><p>Live processes and their working directories. Account ownership is unresolved.</p></div>
        {data !== null && !unavailable && <span className="process-count">{data.items.length}{data.truncated ? "+" : ""} running</span>}
      </div>
      {data === null && !failed ? <p role="status">Reading running Claude processes…</p>
        : unavailable ? <p className="workspace-notice" role="status">Live process information could not be refreshed.</p>
        : data?.items.length === 0 ? <p>{data.truncated ? "No Claude processes could be identified in this partial scan." : "No running Claude processes found for the supported installation."}</p>
        : <div className="workspace-table-scroll"><table className="workspace-table live-process-table" aria-label="Live Claude processes">
          <thead><tr><th scope="col">Account</th><th scope="col">State</th><th scope="col">Left</th><th scope="col">Path</th></tr></thead>
          <tbody>{data?.items.map((item) => <tr key={`${item.platform_scope_id}-${item.pid}-${item.start_time_ticks}`}>
            <th scope="row" data-label="Account"><span className="unresolved-account">Account unresolved</span></th>
            <td data-label="State"><span className="activity-state activity-running"><span aria-hidden="true">●</span>Running</span><small>PID {item.pid}</small></td>
            <td data-label="Left"><span className="unassigned-quota">—</span><small>Account not linked</small></td>
            <td data-label="Path" className="workspace-path"><code>{item.working_directory ?? "Unavailable"}</code></td>
          </tr>)}</tbody>
        </table></div>}
      {data !== null && <p className="live-process-note">Updated {new Date(data.availability.as_of).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })} · Running means the process is present; whether it is working or waiting is unknown.</p>}
      {data?.truncated && <p className="live-process-note">This scan is partial; some processes may be missing.</p>}
      {data !== null && <details className="live-process-source"><summary>Detection details</summary><p>Same-user processes matching Claude {data.provider_version ?? "unavailable"}. Working directories are read directly; they may differ from project roots. Other versions and other users are outside this view.</p></details>}
    </section>
  );
}
