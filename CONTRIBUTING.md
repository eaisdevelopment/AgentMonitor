# Contributing

AgentMonitor is source-available under the [Personal Use License](LICENSE).
Personal, non-commercial use is free; organizational, professional and
commercial use requires a written licence from
[Essential AI Solutions Ltd](https://essentialai.uk/).

## Before changing behavior

Agree the scope, owning module, contract impact and verification with the
maintainer before implementing production changes. Reuse an existing applicable
approval; do not invent extra approvals or claim an assumption is a requirement.
Read [AGENTS.md](AGENTS.md), [architecture](docs/architecture/system-architecture.md)
and [security](docs/architecture/security.md).

Keep changes within the agreed scope. Changes to public contracts, stored data,
credential custody or dependencies need explicit impact review. Record a
compatibility and migration path for breaking changes.

## Development inputs

Use the versions and lock files in `.python-version`, `.node-version`,
`backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json` and
`frontend/package-lock.json`. The current backend requires Python 3.12;
frontend engines and package-manager versions are pinned in its manifest.
Do not silently substitute dependencies or regenerate a lock to make a local
environment pass.

With the reviewed backend environment at `backend/.venv` and locked frontend
dependencies at `frontend/node_modules`, the existing checks are:

```bash
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-BUILD
```

These check source boundaries, types, pinned inputs, generated contracts and
the frontend build. They do not establish provider access or a complete live
deployment. Operational and milestone-verification commands may depend on the
maintainer's configured service, private historical inputs and governance
records; they are not general-purpose installation commands. Those private
records are intentionally excluded from this public source distribution.

## Testing

Use red-green-refactor: observe a meaningful expected failure, implement the
smallest correction, then verify the result. External boundaries use real
storage, HTTP, browsers, processes and provider data. Do not use mocks, fakes,
replayed provider responses, seeded telemetry or placeholder account values.
Constructed inputs are allowed only for pure calculations without I/O.

Select checks appropriate to the changed boundary. Live tests require explicit
real-system prerequisites and must report missing access or unexecuted cases
honestly. An empty provider report is not a populated-data test. A passed unit
test is not proof that an installed dashboard works.

## Pull requests

Explain the problem and resulting behavior, affected modules/contracts, tests
and their actual results, operational or compatibility effects, and limitations.
Update the relevant operator/API documentation with behavior changes. Preserve
the licence and third-party notices.

Never commit `.env`, provider profiles, credentials, session cookies, raw
responses, account databases, prompts, source content from monitored projects
or unredacted screenshots. Use [the private reporting route](SECURITY.md) for
security issues.
