# M0 operation and assertion packet

- Template ID: `TPL-M0-OPERATION-PACKET`
- Schema: `OperationPacketV1` in `m0-g1-record.schema.json`
- Store completed record: external evidence root

Never include secrets or prohibited content. Use an argument array, never a
shell command string. Use opaque references for sensitive targets and paths.

## Identity and lifetime

- Packet ID:
- Operation ID:
- Scenario ID:
- Custody decision ID:
- Finalized UTC:
- Expires UTC:

## Exact operation

- Boundary:
- Executable/procedure reference:
- Ordered arguments:
- Target references:
- Timeout seconds:
- Network policy and exact allowed hosts:

## Assertions

| Assertion ID | Kind | Expected result |
|---|---|---|
| | | |

## Side-effect budget

- Maximum network/provider requests:
- Cost minor units: `0`
- Writes allowed: `false`
- Profile changes allowed: `false`
- Process signals allowed: `false`

## Stop conditions

Include every mandatory G1 stop code. Do not execute if any required condition
or approval is missing, expired, conflicting, or unknown.

## Detached approvals

| Role | Approval record ID | Subject SHA-256 | Decision | UTC time |
|---|---|---|---|---|
| Owner | | | | |
| Security/privacy | | | | |
| Test integrity | | | | |
| Root/integration | | | | |
| Provider system, when applicable | | | | |

Operator sign-off is a separate preflight record, not an `OperationPacketV1`
field. Record the operator's decision, reference, and UTC time in the external
evidence root before execution; the packet's detached approvals do not replace
that checkpoint.
