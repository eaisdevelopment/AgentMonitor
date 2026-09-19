# M1 foundation dependency admission

- Record ID: `FND-I00-DEP-001`
- Status: Approved for M1 direct-selection scope; FND-I01 lock-graph admission remains required
- Research date: 2026-09-19
- Plan/increment: `PLAN-FND` 0.2.0-draft, `FND-I00`
- Requirements/scenarios: `NFR-LIC-001`, `FND-DEP-001..004`, `FND-VER-001`, `FND-ENV-001`, `UI-DEP-001`, `DB-DEP-001..002`
- Affected published contracts: None. No manifest, lockfile, package, browser, application, test, CI, or generated artifact exists or is changed by this record.
- Reviewer/date: M1 dependency steward (Codex), 2026-09-19. The task's owner-authorized M1 scope permits this direct-selection decision; this record does not purport to approve a future resolved graph or installation.

## Decision and scope

This is the exact direct dependency admission required before FND-I01. The
package pins below were the current stable registry releases researched on the
record date and are compatible with the observed local baseline: CPython 3.12.3,
Node.js 22.23.2, npm 10.9.8, and uv 0.11.16. The runtime/tool selections are the
exact local releases available for the FND-I01 clean-resolution prerequisite,
not a claim that an uninstalled later patch release was exercised. CPython's
selected support line is 3.12; FND-I01 must use the exact approved runtime
toolchain and reject a runtime outside the recorded compatibility policy instead
of silently choosing a different interpreter.

The record deliberately selects no extra HTTP client and no third-party
OpenAPI/client generator. T3 requests use Python's standard-library HTTP
facilities, and the generated client remains repository-owned and deterministic
under `CTR-FND-005`. FastAPI extras, Uvicorn `standard` extras, SQLAlchemy async
or database-driver extras, pytest extras, and every unlisted UI package are
excluded.

All direct versions are exact equality pins at manifest creation. A selected
version is not a license, provenance, installation-script, telemetry, or
vulnerability approval for a transitive package. FND-I01 is a separately
required lock-resolution review.

## Sources and research method

Only canonical project release channels were consulted:

- [PyPI package metadata](https://pypi.org/) for the exact Python distribution
  metadata and declared requirements; [npm registry package metadata](https://registry.npmjs.org/)
  for the exact JavaScript package metadata, direct dependencies, and published
  lifecycle scripts.
- The selected projects' canonical upstream repositories linked from those
  registries for their release-tag license and security-policy locations.
- [Playwright's tagged browser manifest](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright-core/browsers.json)
  for the Chromium revision and browser version.
- The [OSV API](https://osv.dev/) was queried for each 14 selected package/version
  pair on 2026-09-19. It returned zero direct-version advisories. This is a
  point-in-time direct-package result only; it neither proves absence of future
  advisories nor clears unresolved transitives.

Registry and upstream release metadata are rechecked on every direct-pin or
lockfile change. Security-policy signals mean a published `SECURITY.md` or
documented security reporting route where upstream provides one; absence or a
material change stops the update for review. The selected projects have active
official release channels on the research date. FND-I01 must record the exact
release dates, provenance hashes/signatures available from the selected resolver,
and any security-policy exception from the then-current upstream evidence.

## Runtime and resolver baseline

| Direct item and exact selection | Purpose / necessity and alternative considered | License and notice obligation | Platform, binary/install/network/telemetry assessment | Pin, update, removal, SBOM decision | Decision |
|---|---|---|---|---|---|
| CPython 3.12.3 (supported line: 3.12) | Backend runtime. Python is required by the approved backend architecture; no alternative runtime is in M1 scope. | PSF-2.0; retain its license/copyright material in release notices if redistributed. | Linux-first and macOS-compatible source/runtime. No AgentMonitor telemetry; obtaining runtime distributions is a network operation outside this increment. | FND-I01 records the exact distribution provenance and resolver compatibility. Upgrade only through a new admission and clean locked verification; removal means replacing the backend architecture. Include runtime in SBOM/release inventory. | Approved for M1. |
| Node.js 22.23.2 | Frontend build/browser-test runtime. Node 20/24 were considered; Node 22 is the required baseline and satisfies the selected package engine ranges. | MIT; preserve attribution in redistributed runtime material. npm bundled material needs its own notice inventory. | Linux/macOS official binaries; native runtime. No AgentMonitor telemetry. Registry access during install is network I/O. | FND-I01 pins node/npm provenance and fails unsupported engines. Upgrade/remove only by new admission; include runtime in SBOM/release inventory. | Approved for M1. |
| npm 10.9.8 | The one selected JavaScript package-manager and lock workflow. pnpm/yarn were rejected to avoid competing locks. | Artistic-2.0 for npm CLI; preserve required notices when redistributed. | Cross-platform Node CLI; package lifecycle scripts are an explicit lock-time gate. npm registry access is network I/O; no project analytics/crash service is permitted. | Commit one `package-lock.json` only after FND-I01 review. Frozen install and lock mismatch must fail. Upgrade/remove only with new admission and lock diff; inventory npm/tool components in SBOM/notices. | Approved for M1. |
| uv 0.11.16 | The one Python resolver/environment/lock workflow. pip/Poetry were rejected to prevent competing resolution state and weaker one-tool governance. | Dual MIT OR Apache-2.0, as published by Astral; preserve the chosen license text and attribution. | Native Rust binary for Linux/macOS; resolver downloads are network I/O. No AgentMonitor telemetry may be enabled or introduced. | FND-I01 must pin the uv binary provenance, generate the single Python lock, and inspect all resolver/download behavior. Update/remove only with new admission and clean resolve. Include uv in tooling SBOM/notices. | Approved for M1. |

## Python direct packages

The `Known direct impact` column is the exact-version distribution metadata
known before resolution, not a transitive inventory. Optional/extras paths are
not selected unless explicitly named. Every named package and all descendants
remain subject to FND-I01's license, provenance, script, telemetry, and OSV
review.

| Exact canonical package | Purpose / necessity; alternative | License / attribution | Known direct impact before lock | Support, binary/scripts, network/telemetry | Maintenance/security and advisory method | Exact pin, update/removal, SBOM/notices | Decision |
|---|---|---|---|---|---|---|---|
| [FastAPI 0.141.1](https://pypi.org/project/fastapi/0.141.1/) | Required versioned ASGI/OpenAPI boundary. A hand-built HTTP framework was rejected; no `standard`/`all` extra is selected. | MIT; retain license/copyright notice. | `starlette`, `pydantic`, `typing-extensions`, `typing-inspection`, `annotated-doc`; selected Pydantic is also listed directly below for explicit control. | Python >=3.10, compatible with 3.12. Pure Python package; no published lifecycle script. Runtime makes no telemetry/network calls by itself. | Canonical FastAPI release channel and upstream security route rechecked at update; OSV direct query on record date: 0. | Manifest equality pin only; lock every dependency and hashes in FND-I01. Remove by replacing API boundary. Add direct/transitive licenses to SBOM/notices. | Approved for M1. |
| [Uvicorn 0.53.0](https://pypi.org/project/uvicorn/0.53.0/) | Required real ASGI server. Hypercorn was considered and rejected to keep one server. No `standard` extra, reload, or worker convenience dependency is selected. | BSD-3-Clause; retain copyright and disclaimer. | `click`, `h11`; typing extensions is conditional only below Python 3.11 and does not apply to CPython 3.12. | Python >=3.10. Pure Python baseline; no lifecycle script. Network listener is product-controlled later, not telemetry; no outbound behavior is admitted. | Canonical release/security route recheck; OSV direct query: 0. | Exact pin/lock; update requires lifecycle/shutdown and security review. Remove by replacing approved ASGI server. SBOM/notices include all locked packages. | Approved for M1. |
| [Pydantic 2.13.5](https://pypi.org/project/pydantic/2.13.5/) | Transport/configuration validation required through FastAPI. Dataclasses alone were rejected for the approved schema boundary. No email/timezone extra is selected. | MIT; retain license/copyright notice. | `annotated-types`, exact `pydantic-core 2.46.5`, `typing-extensions`, `typing-inspection`. | Python >=3.9. `pydantic-core` has platform native wheels/source-build implications; no package lifecycle script known before lock. No runtime telemetry/network behavior admitted. | Canonical Pydantic release/security route recheck; OSV direct query: 0. | Exact pin; FND-I01 verifies the chosen wheel/source hash and native provenance on Linux/macOS. Remove only with transport model replacement. SBOM/notices include core and its native artifacts. | Approved for M1. |
| [SQLAlchemy 2.0.54](https://pypi.org/project/SQLAlchemy/2.0.54/) | Required synchronous persistence/UoW and PostgreSQL seam. `sqlite3` alone was rejected except its approved standard-library adapter use. No driver/async extras are selected. | MIT; retain license/copyright notice. | `greenlet` for common selected architectures; optional driver and async extras excluded. | Python >=3.7. `greenlet` can be native; SQLAlchemy has no network/telemetry role. No lifecycle script known before lock. | Canonical SQLAlchemy release/security route recheck; OSV direct query: 0. | Exact pin; lock and inspect greenlet wheel/source provenance. Removal requires a persistence-architecture decision. SBOM/notices cover ORM and resolved native artifacts. | Approved for M1. |
| [Alembic 1.20.0](https://pypi.org/project/alembic/1.20.0/) | Required explicit immutable migration chain. Hand-rolled migration history was rejected. | MIT; retain license/copyright notice. | `SQLAlchemy >=2.0`, `Mako`, `typing-extensions`; `tomli` is conditional below Python 3.11 and does not apply. | Python >=3.10. Pure Python; no package lifecycle script. No outbound/telemetry behavior admitted. | Canonical Alembic release/security route recheck; OSV direct query: 0. | Exact pin; locked graph must prove Mako and shared SQLAlchemy compatibility. Removal requires an approved migration replacement. SBOM/notices include all locked packages. | Approved for M1. |
| [pytest 9.1.1](https://pypi.org/project/pytest/9.1.1/) | Required Python test runner. `unittest` alone was considered but does not provide the planned test workflow; no mock/plugin extras are selected. | MIT; retain license/copyright notice. | `iniconfig`, `packaging`, `pluggy`, `pygments`; conditional Python <3.11 requirements do not apply. | Python >=3.10. Pure Python; no lifecycle script. No telemetry/network behavior admitted. | Canonical pytest release/security route recheck; OSV direct query: 0. | Exact development-group pin; lock minimal plugins only. Remove only by replacing the approved test workflow. SBOM/notices include dev graph. | Approved for M1. |
| [Ruff 0.16.8](https://pypi.org/project/ruff/0.16.8/) | Required one coherent formatter/linter. Black/Flake8/isort combination was rejected to minimize tools. | MIT; retain license/copyright notice. | No declared Python-package requirements. | Python >=3.7; native Rust executable wheels/source-build implications; no package lifecycle script. No telemetry/network behavior admitted. | Canonical Ruff release/security route recheck; OSV direct query: 0. | Exact development-group pin; FND-I01 records wheel/source hash per platform. Remove only by selecting a replacement toolchain. Include binary in SBOM/notices. | Approved for M1. |
| [mypy 2.3.1](https://pypi.org/project/mypy/2.3.1/) | Required strict Python type gate. Pyright was considered and rejected to keep the Python toolchain minimal. No optional report/cache extras are selected. | MIT; retain license/copyright notice. | `mypy-extensions`, `pathspec`, `librt` on non-PyPy; conditional typing extensions does not apply on 3.12. | Python >=3.10. May use compiled wheels; no lifecycle script. No telemetry/network behavior admitted. | Canonical mypy release/security route recheck; OSV direct query: 0. | Exact development-group pin; lock platform conditionals. Remove only with a replacement strict type-gate decision. SBOM/notices include dev graph. | Approved for M1. |

## JavaScript direct packages and browser binary

| Exact canonical package/project | Purpose / necessity; alternative | License / attribution | Known direct impact before lock | Support, binary/scripts, network/telemetry | Maintenance/security and advisory method | Exact pin, update/removal, SBOM/notices | Decision |
|---|---|---|---|---|---|---|---|
| [react 19.3.0](https://www.npmjs.com/package/react/v/19.3.0) | Required UI runtime; no substitute is planned by P02. | MIT; retain license/copyright notice. | No declared runtime dependency. | Node engine metadata allows the selected Node 22. Pure JavaScript; no package lifecycle script. No external analytics/crash dependency is admitted. | Canonical React release/security route recheck; OSV direct query: 0. | Exact production pin and npm integrity lock. Removal requires a UI architecture decision. SBOM/notices include React. | Approved for M1. |
| [react-dom 19.3.0](https://www.npmjs.com/package/react-dom/v/19.3.0) | Required DOM renderer for React. Direct DOM-only UI was rejected as incompatible with the approved architecture. | MIT; retain license/copyright notice. | `scheduler ^0.28.0`; its version and license are unresolved until FND-I01. Package metadata contains `start=node server.js`; it must not run in installation. | Node compatible. JavaScript package; declared script requires lifecycle-policy inspection. No telemetry is admitted. | Canonical React release/security route recheck; OSV direct query: 0. | Exact production pin, immutable npm lock, explicit lifecycle-script audit. Remove with React replacement. Include direct and scheduler notices. | Approved for M1, conditional on FND-I01 script review. |
| [typescript 7.0.2](https://www.npmjs.com/package/typescript/v/7.0.2) | Required strict frontend/generated-client types. JavaScript-only build was rejected. | Apache-2.0; preserve license, copyright, and any NOTICE obligations. | Platform-specific TypeScript compiler packages at exact 7.0.2 are optional dependencies and must be enumerated by platform. | Requires Node >=16.20. Native platform package archives are selected by OS; no lifecycle script. No telemetry admitted. | Canonical TypeScript release/security route recheck; OSV direct query: 0. | Exact development pin and immutable lock; FND-I01 records Linux/macOS package choice and provenance. Remove only with type-system replacement. SBOM/notices include selected compiler archive. | Approved for M1. |
| [vite 8.3.0](https://www.npmjs.com/package/vite/v/8.3.0) | Required production build/dev server. A hand-rolled bundler was rejected. | MIT; retain license/copyright and bundled notices. | `postcss`, `rolldown`, `picomatch`, `tinyglobby`, `lightningcss`; optional `fsevents`. | Engine `^20.19.0 || >=22.12.0`, satisfied by Node 22.23.2. Native/binary risk via Rolldown/Lightning CSS; package's own scripts are publishing/development scripts and must be blocked from arbitrary lifecycle execution. No telemetry admitted. | Canonical Vite release/security route recheck; OSV direct query: 0. | Exact development pin, npm integrity lock, inspect all binaries/scripts. Remove only through replacement build decision. SBOM/notices cover bundled output/tool graph. | Approved for M1, conditional on FND-I01 binary/script review. |
| [@vitejs/plugin-react 6.1.1](https://www.npmjs.com/package/@vitejs/plugin-react/v/6.1.1) | Official React transform integration for Vite. Hand-maintained transform configuration was rejected. | MIT; retain license/copyright notice. | `@rolldown/pluginutils ^1.0.1`. | Same Node engine range as Vite; JavaScript build plugin. Published development/prepublish scripts are not an installation approval. No telemetry admitted. | Canonical Vite plugin release/security route recheck; OSV direct query: 0. | Exact development pin and lock; FND-I01 inspects resolved plugin/scripts. Removal requires a Vite transform replacement. Include locked notices. | Approved for M1, conditional on FND-I01 script review. |
| [@playwright/test 1.63.0](https://www.npmjs.com/package/@playwright/test/v/1.63.0) plus [Playwright Chromium revision 1243 / 153.0.8010.12](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright-core/browsers.json) | Required real built-browser T4 execution. DOM simulators and alternate browser drivers were rejected by testing policy. | Apache-2.0 for Playwright package; retain license/NOTICE obligations. Chromium's separate license/notices must be enumerated from the official acquired artifact before release. | Exact `playwright 1.63.0`; it in turn controls browser archive acquisition. | Node >=20, satisfied by Node 22. Chromium is an OS-specific binary download with substantial supply-chain and license impact. Browser download is network I/O; browser network traffic must be constrained to the real loopback application during tests. No analytics/crash reporting is admitted. | Canonical Microsoft Playwright release/security route recheck; OSV direct query: 0. Chromium archive security and license review is required after official artifact resolution. | Exact dev pin; browser revision/version fixed above. FND-I01 must record archive URL, hash/signature where provided, platform package, install behavior, cache location, license and notices before acquisition. Removal means no T4 browser evidence and needs replacement approval. SBOM/notices must include package and browser binary. | Approved for M1 direct selection only; browser acquisition is blocked pending FND-I01 review. |

## Cross-cutting supply-chain controls

1. FND-I01 must create exactly one Python lock workflow through uv and one npm
   lock workflow through npm. It must compare each resolved package, version,
   source, integrity hash, platform marker, direct/transitive license, native
   artifact, optional dependency, and lifecycle/install script against this
   admission.
2. FND-I01 must stop (not warn) on any unexpected package, license class,
   package source, Git/path dependency, binary, install script, telemetry or
   outbound behavior, unsupported runtime/platform, advisory, missing
   provenance/integrity data, or browser artifact. Copyleft, unclear, dual, or
   conflicting licenses require explicit owner review under the dependency
   policy; a permissive registry headline is insufficient.
3. At lock resolution, run an authenticated-source-independent OSV/advisory
   review of every resolved package/version, inspect the package tarball/wheel
   metadata and license file, and record the query date/result. Direct query
   result above does not make this check optional.
4. Generate SPDX or CycloneDX SBOMs and third-party notices from the final
   backend, frontend, resolver/tool, native-wheel, and Playwright/Chromium
   inventories. Preserve Apache-2.0 NOTICE obligations and bundled Vite/browser
   notices. Review any manual license classification before release.
5. Frozen installs must use canonical PyPI/npm sources over TLS, retain
   resolver-supported integrity hashes, reject manifest/lock drift, and run
   without developer caches as the reproducibility evidence. No analytics,
   crash-reporting, CDN runtime imports, cloud scan upload, or package lifecycle
   script is allowed unless separately recorded and approved.
6. Dependency updates are reviewed changes: re-run this admission evidence,
   resolve cleanly, diff the complete graph/SBOM/notices, rerun advisories, and
   retain FND-I01 real-environment evidence. Remove unused dependencies promptly
   with the same lock/SBOM/notices diff. There are no accepted vulnerability
   exceptions in this record.

## Explicit exclusions and residual uncertainty

- No `httpx`, `requests`, `axios`, fetch wrapper, or external OpenAPI/client
  generator is admitted for M1. Python standard library and the repository-owned
  deterministic generator are the only approved choices for those roles.
- No provider SDK, database driver, async SQLite package, test mock plugin,
  UI router/query/chart/component package, CSS framework, scanner, CI package,
  or telemetry/crash-reporting package is admitted by this record.
- Full transitive package names, exact versions, SPDX expressions, license-file
  evidence, integrity values, platform selection, source/wheel provenance,
  package-install scripts, and actual resolver/browser network behavior are
  **Not Run** because FND-I01 is intentionally not authorized here. They are not
  claimed as passed and block FND-I01 if incompatible with this record.

## Compatibility, security, and documentation impact

This document changes no API, event, provider, database, configuration, or
module contract. It creates no migration or rollback obligation. It mitigates
`R-018` only at direct-selection scope; the resolved graph and browser binary
remain open supply-chain risks until FND-I01. It contains no secret, provider
state, prompt/response, source-content, environment value, or telemetry data.

The next authorized step is FND-I01 only: create the manifests/locks through the
selected resolvers, perform the fail-closed graph comparison above, and then
record real clean-resolution evidence. This admission by itself does not
authorize package installation, browser download, application code, tests, CI,
external resources, or release claims.
