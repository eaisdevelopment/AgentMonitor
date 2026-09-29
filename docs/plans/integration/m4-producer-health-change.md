# Change plan: genuine producer health leaves for M4

- Status: **Approved**; version `1.0.0`; root integration review 2026-09-29.
- Authority: existing full M4 implementation authorization.
- Owners: M01, M02 and M04 each implement only their own SQLite health leaf;
  FND/composition maps actual lifecycle/configuration/PLAN-DB receipts.
- Requirements: `FR-OPS-002/005/006`, `NFR-RES-001`, `NFR-OBS-001`.
- Acceptance: `AC-OPS-003/006`, `AC-V1-005/006/007/008`, `AC-TEST-001/002`.
- Contracts: `CTR-OPS-006` V1, existing module health and PLAN-DB bounded-read
  mechanism. No cross-module table access or provider I/O.

Each producer reads only code-owned aggregate metadata from its own allowlisted
tables through the approved bounded read-only SQLite connection. IAM counts
administrator initialization without credential columns. Registry checks its
actual metadata/account inventory without labels or identities. Collection
reports actual due/running/blocked schedule counts; empty real inventory is
zero counts and does not prove provider collection success. Every query has
the operations request deadline and closes its own connection before returning.
Failures become bounded operations codes. No exception text or stored values
are diagnostics output.

The existing real HTTP operations tests are Red for absent endpoints/leaves.
Green requires the production Uvicorn service, actual migrated/initialized IAM,
live WAL and genuine leaf reads. Further owner-installation/browser and actual
optional failure-isolation tests remain required; unavailable conditions are
not passed. No dependencies, data migrations, secret access, provider changes
or user-agent control. Startup integrity is the genuine historical receipt;
health GET never checkpoints or reruns quick/full integrity.
