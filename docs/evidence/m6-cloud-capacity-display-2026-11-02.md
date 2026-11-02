# M6 cloud capacity display slice

M6-A04/A08, `FR-QUOTA-001/002/004/006`, `AC-UI-002..006`: the M05 `CTR-CAP-001` window already persists `is_constraining`; the versioned capacity API now exposes it as an optional nullable additive field and the generated client follows. Overview and account details render exact native USD amounts without binary floating-point conversion, keep windows separate, and avoid low warnings and low-first sorting when the API identifies a window as non-constraining. Unknown constraint preserves existing display behavior. No provider-specific logic was added to the UI.

Constructed frontend and wire-projection presentation cases were removed because repository policy permits constructed values only in pure domain tests; they do not count as Red/Green evidence. Thirteen existing pure M05 capacity tests passed. Frontend typecheck, production build, Ruff and generated OpenAPI/client compatibility checks passed. A real empty-registry API regression check failed because background Ollama installation reconciliation changed the expected registry revision from 0 to 1. Real cloud balance, account display and browser verification are Not Run: no real cloud quota has been collected for this slice. No provider data was fabricated.


The API still does not expose source period start, verified team-pool identity, or shared-balance semantics. This slice does not implement cloud collection, deduplication, quota history or alerts, and does not establish M6 completion. No database migration or new dependency was introduced. Deployment and live validation remain outstanding.

The prepared Ollama cloud connection panel labels a successful access check as
owner-provided account information and accepts server-provided status only.
Frontend typecheck passed. The panel is not connected to an API or routed; a
real-data built-browser check and its required Red/Green evidence remain Not Run.
Earlier constructed presentation checks were removed as inadmissible under the
project's external-boundary test rule; they are not counted as evidence.

The candidate declares a bodyless Ollama cloud status/initiation API surface.
The actual application OpenAPI route check failed before the route existed and
passes afterwards; generated OpenAPI/client compatibility, frontend typecheck,
and targeted API type checking passed. The initiation route requires a signed-in
browser with CSRF, account version and idempotency headers and rejects a request
body; it returns unavailable until its application port is wired. No real
signed-in HTTP request, browser flow, account verification or key operation has
been performed for this surface. The panel remains disconnected.

The V2 cloud target now has separate account-capacity, quota and history wire
routes; V1's required installation identity remains unchanged. V1 routes return
an explicit V2-required problem for cloud targets. The dashboard client uses the
V2 routes. A pure V2 subject-mapping test failed before the mapper existed and
passes; eight focused API/mapping checks, generated OpenAPI compatibility,
targeted mypy, frontend typecheck and build passed. An independent review on a
private copy of real Claude/Codex data found identical V1/V2 wire output for
12 account-capacity views, 19 windows and 4,800 sampled history points at the
same observation time. No account values were printed and the copy was deleted.
Live authenticated browser verification and real cloud data remain Not Run.

A pure-domain regression check showed that an explicitly non-constraining window
with zero remaining ratio was incorrectly marked current and exhausted. The
change returns unavailable without a numeric threshold or exhaustion for that
case; all 13 alert-domain tests pass, and an independent reviewer found no
blocker in this scope. Legacy windows with unknown constraint status retain
their prior behavior. No real alert lifecycle was exercised by this check.

A follow-up pure-domain change distinguishes fresh, complete evidence that a
window is explicitly non-constraining from unknown or stale readings. It can
resolve an existing capacity alert as no longer applicable without inventing a
remaining percentage. Four new domain checks failed before the change; 59
related capacity/alerting domain checks pass. Independent review is pending;
no real alert lifecycle was exercised.

The candidate now defines an application-owned cloud freshness policy: at
least 15 minutes or two nominal round-robin turns including the bounded jitter,
whichever is longer. It is not a provider guarantee; an unknown/inconsistent
account count yields unknown freshness and a long cooldown may produce a stale
reading. Pure policy tests failed before the policy existed and pass afterward.
The repository has no existing audited general freshness-setting use case, so
the default is not yet administrator-editable. Real provider provenance,
registry-count races and live stale/current display remain Not Run.

V2 unresolved aggregate groups have no numeric totals in both the domain and
wire schema. The local candidate baseline initially rejected this correction
as `breaking_drift`; public GitHub main (1e325eb) and the running dashboard's
working tree (86f2701) contain no V2 group. The generated candidate artifacts
were therefore checked against that published GitHub baseline before the
unshipped candidate baseline was updated. V1 wire contracts were preserved.
