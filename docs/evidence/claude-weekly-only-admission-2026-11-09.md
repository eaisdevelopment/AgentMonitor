# Claude weekly-only usage compatibility evidence

Requirements: FR-COL-004/006/007/008, NFR-COMP-001, M6-A07, AC-LIVE-004/007.
Authority: owner-approved [9 November correction](../plans/integration/m6-provider-display-compatibility-2026-11-09.md).
Owner: A01. Status: bounded source compatibility verified; installed persistence
and M6 completion are separate follow-up checks, not claimed here.

The owner authorized an existing managed Claude profile. Its identity matches
the existing registry account. With the retained official CLI `2.1.289`, the
real managed-quota test failed before implementation with
`usage_deadline_window_set_invalid` in 22.25 seconds. A bounded in-memory
diagnostic found a weekly all-models value and a model-specific weekly value,
but no current-session label in the whole capture. No raw output was retained.

The correction preserves the strict fast path. A weekly-only partial reading
is considered only at the existing capture deadline after at least one second
of silence, with valid current weekly data and completion marker observed after
the issued command. Parsing the post-command bytes must agree with the full
current terminal surface. A whole-capture session label, a visible truncated
session label, invalid terminal controls, recognized error/authentication/loading
text, malformed/duplicate fields or missing weekly data rejects the fallback.
This distinguishes genuinely unobserved session values from unfinished or
clipped known session data. No percentage or reset value is invented.

The V1 payload retains both structural window identities. The session value and
reset become unknown, and the outcome is partial with
`claude_current_session_not_reported` / unknown. The existing unsupported
model-specific omission remains unsupported. A01 adapter/parser version is
`1.0.4`, with a new hash-bound mapping; the historical `1.0.3` mapping and M3/M4
receipts are preserved. The public V1 schema, database schema, installed CLI,
OTLP admission, accounts, credentials and running user agents are unchanged.

Red/Green:

- The original real managed-quota test failed as above.
- New availability/render checks and the unknown-value mapper failed before
  implementation. Independent review found four additional unsafe cases:
  pre-command weekly values plus a fresh marker, and three truncated session
  labels. Their pure tests failed before the freshness correction.
- The complete A01 non-live selection passed **73 tests** after the additional
  erased cursor-assembled-label rejection. The terminal reducer now detects a
  session label as it is rendered, before a later clear can hide it.
- The real managed-quota test passed after the final freshness correction in
  **21.95 seconds**, including identity checks before/after for both managed
  and protected default profiles. It requires real weekly data; any absent
  session value must carry the explicit omission and unknown reset.
- The dedicated real weekly-only adapter test then passed in **31.49 seconds**:
  outcome partial, adapter provenance `1.0.4`, actual weekly percentage, session
  percentage unknown and an unknown omission, with both identities unchanged.

Commands used, with the explicit real managed account and owner data root
selected locally (their values are not needed in this evidence):

```bash
PYTHONPATH=backend/src python -m pytest \
  backend/tests/adapters/providers/claude/test_missing_session.py \
  backend/tests/adapters/providers/claude/test_subscription_source_parser.py \
  backend/tests/adapters/providers/claude/test_capacity_mapper.py -q --tb=short
PYTHONPATH=backend/src python -m pytest \
  backend/tests/adapters/providers/claude/live/test_managed_quota.py::test_real_managed_quota_uses_its_authenticated_identity \
  -q --tb=short
```

Source buffers remain transient. No new dependency, secret-storage behavior,
API/schema migration or licensing change is introduced. Installed projection,
history, browser and recovery evidence must be recorded separately after the
sealed deployment; this source-level result does not close M6.
