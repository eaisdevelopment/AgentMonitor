# M0 G1 review-mode metadata access — preliminary incident note

- Observed on 2026-09-21 during exact-subject role review.
- Boundary: external evidence-custody directory **metadata only**.
- Trigger: `m0_g1_approve.py --review-subjects` called the local custody
  selection validator, which statted the selected external root before printing
  three digest-only subject rows.
- Actual observed effects: owner-root metadata checked; no directory contents
  opened, no path or identity printed, no provider/account/profile/process
  operation, no write, and no network request reported by the reviewers.
- Authorization concern: the reviewer assignments prohibited external-root
  access, and the G1 implementation authority did not grant it. The earlier
  digest command therefore exceeded that narrow assignment. Previous
  provisional custody approval was withdrawn.
- Immediate stop: reviewers were told not to rerun the mode or touch the root.
  The finalizer is being changed to load only the owner-only local selection
  file before the explicit owner confirmation; external-root checks move to
  the owner-confirmed finalization path.
- Status: **open**. Owner acknowledgement/decision, reviewer recheck, and
  evidence of no further unexpected access remain required. This happened
  during G1 control review, not an authorized scenario/operation; the current
  `IncidentRecordV1` requires both IDs, so no scenario or operation ID will be
  invented to force this note into that schema. No live M0 gate is claimed
  passed by this note.

This note intentionally contains no root path, alias mapping, identity, or
unsanitized observation.
