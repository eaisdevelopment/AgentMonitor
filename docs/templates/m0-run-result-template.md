# M0 run result

- Template ID: `TPL-M0-RUN-RESULT`
- Schema: `RunResultV1` in `m0-g1-record.schema.json`
- Created only after an authorized operation attempt

Never include secrets or prohibited content. Use sanitized opaque evidence
references; do not copy raw output into this record.

## Run

- Run, packet, operation, and scenario IDs:
- Started and ended UTC:
- Termination: completed / not started / timed out / cancelled / failed

## Assertions

| Assertion ID | Outcome | Sanitized evidence reference |
|---|---|---|
| | satisfied / violated / unknown | |

## Side-effect reconciliation

- Actual network/provider requests:
- Actual cost minor units:
- Writes observed:
- Profile changes observed:
- Process signals observed:
- Prohibited data observed: yes / no / unknown

## Outcome

- Incident ID or not applicable:
- Status: Passed / Failed / Blocked
- Evidence references:

Unknown or missing evidence never becomes `Passed`.
