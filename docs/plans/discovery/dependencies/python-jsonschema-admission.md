# M0 G1 JSON Schema validator admission

- Admission ID: `DEP-M0-JSONSCHEMA-001`
- Status: **Approved and installed for the isolated local G1 gate**
- Review date: 2026-09-19
- Direct dependency: `jsonschema==4.26.0`
- Environment: `.venv-m0-g1` on CPython 3.12/Linux x86-64

## Decision and graph

`jsonschema` is required for real Draft 2020-12 metaschema validation; a
hand-written substitute is not acceptable. The hash-locked graph is:

| Package | Version | License |
|---|---:|---|
| jsonschema | 4.26.0 | MIT |
| attrs | 26.1.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| referencing | 0.35.1 | MIT |
| rpds-py | 2026.6.3 | MIT |

`referencing` is pinned below 0.36 to avoid adding the separately licensed
`typing-extensions` dependency. `rpds-py` is native Rust code; only its pinned
official Linux CPython 3.12 wheel is currently verified. macOS remains Not Run.

The source input is `tools/discovery/requirements-m0-g1.in`, SHA-256
`fcba1ea46e3adb701172586409b30734f9ef96366c5d91ecf5bfcbd434b23de0`.
The generated hash lock is `tools/discovery/requirements-m0-g1.lock`, SHA-256
`0aa9ce72263bbd68dbfd4626a260083e7cf59c1425eebe71d37c573092b12b9e`.
Existing local `uv==0.11.16` generated and synchronized the lock; it was not
added as an AgentMonitor dependency.

Sources: [jsonschema](https://pypi.org/project/jsonschema/),
[attrs](https://pypi.org/project/attrs/),
[jsonschema-specifications](https://pypi.org/project/jsonschema-specifications/),
[referencing](https://pypi.org/project/referencing/), and
[rpds-py](https://pypi.org/project/rpds-py/).

## Controls and evidence

- The validator rejects duplicate JSON keys and all non-local `$ref` values.
- Only the repository schema and packaged official metaschema are used; no
  remote schema retrieval occurs.
- UTC-`Z` timestamp syntax/calendar validity is enforced separately.
- `uv pip check` passed for the exact five-package environment.
- The exact G1 schema passed `Draft202012Validator.check_schema` under
  `jsonschema==4.26.0` through `AUTO-M0-G1-EXIT`.
- The environment is local/ignored and is not a distributable artifact.

Copyright © 2026 Pavlo Sidelov. All rights reserved.
