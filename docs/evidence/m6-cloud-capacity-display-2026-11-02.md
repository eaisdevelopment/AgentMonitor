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
