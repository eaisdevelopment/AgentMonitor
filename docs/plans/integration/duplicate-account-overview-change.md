# Duplicate Claude identity in Overview

Status: Approved bounded owner correction, 2026-09-29. Version: 1.0.0.
Primary owner: P02; contracts: generated V1 API, existing M02/A01 identity
and M05 capacity reads. No backend or registry mutation is authorized by this
presentation correction. The owner reported two identical verified Overview
rows and asked why.

Requirements: FR-ACC-006, FR-UI-001/003; existing account identity and quota
provenance acceptance criteria apply. Two real registry records currently
report the same Claude identity. An administrator label is not provider
identity. Group only successful, fresh, lineage-matched quota/identity reads
with the same provider, reported email, provider organization and dashboard
organization. Keep records separate when evidence is incomplete or conflicted.
Prefer the record whose administrator name matches the reported email, then
use stable account ID order. Show one quota row, the connection count and an
explicit link to review each additional record. Keep all admin records in
Accounts; do not delete, merge, reconnect or change a default provider profile.
Account details show the configured name alongside a different detected email.

Real Red: owner authenticated built Overview has two rows for one identity
and no additional-connection warning. Add a read-only real-browser verifier
requiring this genuine duplicate condition, no seeded telemetry. Green requires
one grouped quota row, visible connection provenance and correct record links.
Include it in AUTO-ACCOUNT-AGENTS and normal build/documentation checks.
No dependencies, secrets, migrations, provider writes or process control.
Rollback changes only frontend assets. Full M4 remains outside this increment.
