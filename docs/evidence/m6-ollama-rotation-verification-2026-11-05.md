# M6 Ollama verification after key replacement — 5 November 2026

- Requirements: existing M6 cloud rotation/connection behavior, M6-A03/A07/A09.
- Primary owner: M02 registry, integrated through CTR-COL-010 2.0.0.
- Status: implementation and verification in progress; no completion claim.
- Authority: the [approved cloud plan](../plans/integration/m6-ollama-cloud-implementation-change.md).

## Observed failure

The first SDK binding produced a real successful partial balance collection at
13:42:49 UTC. A later active binding was generation 2, while the owner-confirmed
monitoring graph and successful receipt still referred to generation 1. The
current generation had no verification job or receipt. This correctly prevented
using the earlier key's result as authorization for the new key.

The owner clicked **Check connection**. A subsequent observed browser retry of
the same action returned HTTP 503 with the closed problem code
`ollama_cloud_connection_unavailable`; no generation-2 job was queued. The
atomic initiator reused the existing graph based only on account version and
graph presence. Its initial ownership-assertion path also supported only pending
accounts, so simply invoking it again could not repair active-account rotation.

A brief `worker_unavailable` response was also observed. Later reads returned
`can_verify=true`; read-only checks found a safe empty worker lock, active
service and no retained worker unit. No persistent quarantine was established,
and no service restart was performed for that transient observation.

The key was not inspected, re-entered, replaced or copied by an agent. Existing
EAIS collection continued. No local Ollama work was added to scope.

## Correction and test evidence

M02 now has a separate active-account binding reassertion policy and a
transaction-local update path. The pending-only initial-enrollment policy is
unchanged. Before M04 creates a new verification job, the current binding is
checked and the existing graph is updated with account/graph version fences.
Only versions, timestamps and the graph's binding/target/assertion metadata
change. Account name, organization, monitoring choice, profile/resource IDs and
history are preserved. The previous receipt remains attached to its original
binding; no successful receipt is fabricated for the replacement key.

Red used the actual outstanding SDK rotation copied with SQLite's backup API
into an owner-only temporary directory. Production verification initiation
failed with `ollama_cloud_verification_authority_unavailable`; the stale-account
version rejection already passed (one failed, one passed). No provider request,
credential read, seeded record or live-database write was involved. Green then
passed both real-copy tests, including preservation and idempotent replay.
The temporary copy is deleted after testing; future absence of a real
outstanding rotation is explicitly Not Run rather than seeded into existence.

The expanded domain/contract/binding selection passed 53 tests. The 15 new pure
reassertion cases were added before implementation but not separately executed
Red; the meaningful Red evidence is the actual boundary failure above.
Independent review found no blocking defect. The pure policy tests are included
in canonical M6 source-security selection, with corresponding catalog hashes
updated. Full quality initially found missing type annotations in the new tests;
those are being corrected before deployment. Installed verification is still
pending at this checkpoint.

Affected public contracts retain their existing shapes and versions:
CTR-COL-010 2.0.0 and the existing M02 cloud binding/verification contracts.
There is no schema/migration, credential-storage, dependency or license change.
The correction is local until the canonical current-update command and real
browser/provider verification succeed. M6 remains incomplete.

## Pre-deployment verification

After correcting test annotations, `AUTO-QUALITY` passed. The canonical
source-security selection passed 109 tests. The actual rotated-copy integration
and M6 direct/gate policy selection passed 74 tests with zero skips. Docs and
planning checks passed. OpenAPI/client generation updated source/artifact hashes
only: the schema digest and all 78 operations remained unchanged. No live
credential or account mutation was part of these tests. Deployment and the
owner-requested current-key check follow this clean candidate commit.

## Installed result

Implementation `e1fd838` passed `AUTO-M6-CURRENT-UPDATE`. Retrying the owner's
same SDK **Check connection** action in the real signed-in browser returned
HTTP 202 instead of 503. The current generation-2 key produced a successful
balance reading at 14:26:38 UTC. Normal worker reconciliation then reported
`access_valid_owner_confirmed` and `scheduled`; the exact active binding,
monitoring graph, scheduled proof and latest-run snapshot matched. No further
key entry, key replacement or account-setting change was required.

The canonical installed-dashboard producer passed account administration,
cloud capacity, history and dashboard continuity against this deployed
implementation. Both real cloud targets were confirmed, both current balances
matched their API lineage, and both history views matched. Local Ollama remained
explicitly deferred. The real snapshot independently reported two verified,
current cloud targets with history, but only one declared required organization
scope. This closes the observed key-replacement verification defect; it does
not close M6's organization-coverage, official comparison, cross-provider
recovery or owner-acceptance requirements. Subsequent scheduled observations
remain distinct from this successful connection-check reading.
