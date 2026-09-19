# M1 foundation dependency admission

- Record ID: `FND-I00-DEP-001`
- Status: **Blocked — owner decisions required before any M1 direct admission.**
  The technical selections are documented, but CPython's PSF-2.0, npm's
  Artistic-2.0, and uv's selectable dual license are outside ADR-0011's normal
  admission classes. FND-I01 must not begin while this status is Blocked.
- Research date: 2026-09-19
- Plan/increment: `PLAN-FND` 0.2.0-draft, `FND-I00`
- Requirements/scenarios: `NFR-LIC-001`, `FND-DEP-001..004`, `FND-VER-001`, `FND-ENV-001`, `UI-DEP-001`, `DB-DEP-001..002`
- Affected published contracts: None. No manifest, lockfile, package, browser,
  application, test, CI, or generated artifact is created or changed by this record.
- Reviewer/date: M1 dependency steward (Codex), 2026-09-19. This is a research
  and review record, not an owner license decision or approval of a future
  resolved graph or installation.

## Decision and scope

This record identifies the exact technical selections proposed for FND-I01. The
package pins were the current stable registry releases researched on the record
date and are compatible with the observed local executables: CPython 3.12.3,
Node.js 22.23.2, npm 10.9.8, and uv 0.11.16. It is not an admission while the
status above is Blocked.

CPython 3.12.3 is an observed local executable, not an approved supported
baseline: it is superseded by the proposed current 3.12 security-maintenance
candidate, **CPython 3.12.14**. The official source provenance proposed for a
later approved FND-I01 is the Python 3.12.14 source distribution with its
published `.asc` and Sigstore verification artifacts. Before FND-I01, the owner
must approve PSF-2.0 and the dependency steward must approve/provision that
exact candidate through an authorized path. FND-I01 must fail rather than
resolve against 3.12.3 merely because it is locally installed.

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
- The [OSV API](https://osv.dev/) direct query evidence is retained in the
  sanitized, tuple-by-tuple table below. No advisory response bodies were saved.

Registry and upstream release metadata are rechecked on every direct-pin or
lockfile change. The evidence register intentionally distinguishes an upstream
security route from a published fixed support horizon: where no time-bounded
support commitment was found in an authoritative source, it says so rather than
inventing one. FND-I01 must record exact release dates, provenance
hashes/signatures available from the selected resolver, and any security-policy
exception from then-current upstream evidence.

## Runtime and resolver baseline

| Direct item and exact selection | Purpose / necessity and alternative considered | License and notice obligation | Platform, binary/install/network/telemetry assessment | Pin, update, removal, SBOM decision | Decision |
|---|---|---|---|---|---|
| CPython 3.12.14 proposed candidate; 3.12.3 observed locally and rejected as superseded | Backend runtime. Python is required by the approved backend architecture; no alternative runtime is in M1 scope. | PSF-2.0; retain its license/copyright material in release notices if redistributed. | Linux-first and macOS-compatible source/runtime. No AgentMonitor telemetry; obtaining runtime distributions is a network operation outside this increment. | FND-I01 records the exact 3.12.14 distribution provenance and resolver compatibility. Upgrade only through a new admission and clean locked verification; removal means replacing the backend architecture. Include runtime in SBOM/release inventory. | **Blocked:** owner must explicitly approve PSF-2.0; 3.12.3 cannot be selected as the baseline. |
| Node.js 22.23.2 | Frontend build/browser-test runtime. Node 20/24 were considered; Node 22 is the required baseline and satisfies the selected package engine ranges. | MIT; preserve attribution in redistributed runtime material. npm bundled material needs its own notice inventory. | Linux/macOS official binaries; native runtime. No AgentMonitor telemetry. Registry access during install is network I/O. | FND-I01 pins node/npm provenance and fails unsupported engines. Upgrade/remove only by new admission; include runtime in SBOM/release inventory. | Approved for M1 direct selection; overall admission remains Blocked. |
| npm 10.9.8 | The one selected JavaScript package-manager and lock workflow. pnpm/yarn were rejected to avoid competing locks. | Artistic-2.0 for npm CLI; preserve required notices when redistributed. | Cross-platform Node CLI; package lifecycle scripts are an explicit lock-time gate. npm registry access is network I/O; no project analytics/crash service is permitted. | Commit one `package-lock.json` only after FND-I01 review. Frozen install and lock mismatch must fail. Upgrade/remove only with new admission and lock diff; inventory npm/tool components in SBOM/notices. | **Blocked:** owner must explicitly approve Artistic-2.0 under ADR-0011. |
| uv 0.11.16 | The one Python resolver/environment/lock workflow. pip/Poetry were rejected to prevent competing resolution state and weaker one-tool governance. | Upstream offers selectable MIT **or** Apache-2.0 license branches; retain the eventually selected text and attribution. This record does not select either branch. | Native Rust binary for Linux/macOS; resolver downloads are network I/O. No AgentMonitor telemetry may be enabled or introduced. | FND-I01 must pin the uv binary provenance, generate the single Python lock, and inspect all resolver/download behavior. Update/remove only with new admission and clean resolve. Include uv in tooling SBOM/notices. | **Blocked:** owner must select and approve an upstream license branch; no selection is inferred. |

## Direct-admission evidence register

Each row is the evidence reviewed before a direct package was marked approved,
conditional, or blocked. `Security route` is an inspectable canonical upstream
location for disclosure policy/status at update time; it is not a claim that the
project publishes a time-bounded support commitment. `No published horizon
located` means precisely that, not that support is indefinite. Archive values are
registry metadata on the research date; they are size impact, not a performance
benchmark. Performance remains Not Run until FND-I01's clean real resolution.

| Evidence | Exact release and tagged license evidence | Ownership, maintenance/security route, release/support horizon | Size/performance impact before lock |
|---|---|---|---|
| E-RT-01 CPython 3.12.14 proposed candidate; 3.12.3 observed only | [official 3.12.14 release](https://www.python.org/downloads/release/python-31214/); [tagged PSF license](https://github.com/python/cpython/blob/v3.12.14/LICENSE); [official source directory](https://www.python.org/ftp/python/3.12.14/) | [python/cpython](https://github.com/python/cpython); [official version-status policy](https://devguide.python.org/versions/). Python 3.12 is in security maintenance through 2028-10. Candidate released 2026-08-12; 3.12.3 is superseded and rejected. | Official source provenance proposed: `Python-3.12.14.tar.xz` (20,820,300 bytes) plus published `.asc` and `.sigstore` files; no download/install performed. Startup performance **Not Run**. |
| E-RT-02 Node.js 22.23.2 | [official distribution directory](https://nodejs.org/dist/v22.23.2/); [tagged MIT license](https://github.com/nodejs/node/blob/v22.23.2/LICENSE) | [nodejs/node](https://github.com/nodejs/node); [security route](https://github.com/nodejs/node/security/policy); [official release schedule](https://github.com/nodejs/Release#release-schedule) gives the Node 22 line's planned 2027-04 end. | Official Linux x64 archive is 31 MB; official `SHASUMS256.txt` and signature are published in the same directory. No download/install or runtime benchmark was performed. |
| E-RT-03 npm 10.9.8 | [npm registry release metadata](https://registry.npmjs.org/npm/10.9.8); [tagged Artistic-2.0 license](https://github.com/npm/cli/blob/v10.9.8/LICENSE) | [npm/cli](https://github.com/npm/cli); [security route](https://github.com/npm/cli/security/policy). No separate time-bounded npm 10 support horizon located in canonical source; recheck against Node 22 support. | Registry reports `dist.unpackedSize` 11,682,638 bytes / 2,009 files and SHA-512 integrity metadata for the official tarball. No download/install or benchmark was performed. Lifecycle scripts remain a FND-I01 stop condition. |
| E-RT-04 uv 0.11.16 | [official release](https://github.com/astral-sh/uv/releases/tag/0.11.16); [MIT branch](https://github.com/astral-sh/uv/blob/0.11.16/LICENSE-MIT); [Apache-2.0 branch](https://github.com/astral-sh/uv/blob/0.11.16/LICENSE-APACHE) | [astral-sh/uv](https://github.com/astral-sh/uv); [security route](https://github.com/astral-sh/uv/security/policy). No published time-bounded support horizon located. | Official release assets: Linux x86_64 GNU tarball 24,014,155 bytes; macOS x86_64 tarball 22,381,489 bytes. No download/install or resolver benchmark was performed. |
| E-PY-01 FastAPI 0.141.1 | [PyPI release](https://pypi.org/project/fastapi/0.141.1/); [tagged MIT license](https://github.com/fastapi/fastapi/blob/0.141.1/LICENSE) | [fastapi/fastapi](https://github.com/fastapi/fastapi); [security route](https://github.com/fastapi/fastapi/security/policy). Current registry release on research date; no published time-bounded support horizon located. | PyPI files: 131,954–425,799 bytes; pure Python. Runtime performance not measured. |
| E-PY-02 Uvicorn 0.53.0 | [PyPI release](https://pypi.org/project/uvicorn/0.53.0/); [tagged BSD-3-Clause license](https://github.com/Kludex/uvicorn/blob/0.53.0/LICENSE.md) | [Kludex/uvicorn](https://github.com/Kludex/uvicorn); [security route](https://github.com/Kludex/uvicorn/security/policy). Current registry release; no published time-bounded support horizon located. | PyPI files: 87,081–110,881 bytes; pure Python baseline. Runtime performance not measured. |
| E-PY-03 Pydantic 2.13.5 | [PyPI release](https://pypi.org/project/pydantic/2.13.5/); [tagged MIT license](https://github.com/pydantic/pydantic/blob/v2.13.5/LICENSE) | [pydantic/pydantic](https://github.com/pydantic/pydantic); [security route](https://github.com/pydantic/pydantic/security/policy). Current registry release; no published time-bounded support horizon located. | PyPI files: 472,589–845,750 bytes; `pydantic-core` native artifact adds platform impact. Runtime performance not measured. |
| E-PY-04 SQLAlchemy 2.0.54 | [PyPI release](https://pypi.org/project/SQLAlchemy/2.0.54/); [tagged MIT license](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_54/LICENSE) | [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy); [security route](https://github.com/sqlalchemy/sqlalchemy/security/policy). Current registry release; no published time-bounded support horizon located. | PyPI files: 1,958,015–9,969,559 bytes; `greenlet` may be native. Query/startup performance not measured. |
| E-PY-05 Alembic 1.20.0 | [PyPI release](https://pypi.org/project/alembic/1.20.0/); [tagged MIT license](https://github.com/sqlalchemy/alembic/blob/rel_1_20_0/LICENSE) | [sqlalchemy/alembic](https://github.com/sqlalchemy/alembic); [security route](https://github.com/sqlalchemy/alembic/security/policy). Current registry release; no published time-bounded support horizon located. | PyPI files: 268,719–2,093,272 bytes; pure Python. Migration performance not measured. |
| E-PY-06 pytest 9.1.1 | [PyPI release](https://pypi.org/project/pytest/9.1.1/); [tagged MIT license](https://github.com/pytest-dev/pytest/blob/9.1.1/LICENSE) | [pytest-dev/pytest](https://github.com/pytest-dev/pytest); [security route](https://github.com/pytest-dev/pytest/security/policy). Current registry release; no published time-bounded support horizon located. | PyPI files: 386,536–1,636,369 bytes; pure Python. Test execution overhead not measured. |
| E-PY-07 Ruff 0.16.8 | [PyPI release](https://pypi.org/project/ruff/0.16.8/); [tagged MIT license](https://github.com/astral-sh/ruff/blob/0.16.8/LICENSE) | [astral-sh/ruff](https://github.com/astral-sh/ruff); [security route](https://github.com/astral-sh/ruff/security/policy). Current registry release; no published time-bounded support horizon located. | PyPI files: 4,938,814–11,336,694 bytes; native Rust binary. Formatting/lint performance not measured. |
| E-PY-08 mypy 2.3.1 | [PyPI release](https://pypi.org/project/mypy/2.3.1/); [tagged MIT license](https://github.com/python/mypy/blob/v2.3.1/LICENSE) | [python/mypy](https://github.com/python/mypy); [security route](https://github.com/python/mypy/security/policy). Current registry release; no published time-bounded support horizon located. | PyPI files: 2,754,338–17,073,258 bytes; compiled-wheel possibility. Type-check performance not measured. |
| E-JS-01 React 19.3.0 | [npm release](https://www.npmjs.com/package/react/v/19.3.0); [tagged MIT license](https://github.com/facebook/react/blob/v19.3.0/LICENSE) | [facebook/react](https://github.com/facebook/react); [security route](https://github.com/facebook/react/security/policy). Current registry release; no published time-bounded support horizon located. | npm unpacked size: 178,663 bytes / 27 files. Bundle impact not measured. |
| E-JS-02 React DOM 19.3.0 | [npm release](https://www.npmjs.com/package/react-dom/v/19.3.0); [tagged MIT license](https://github.com/facebook/react/blob/v19.3.0/LICENSE) | [facebook/react](https://github.com/facebook/react); [security route](https://github.com/facebook/react/security/policy). Current registry release; no published time-bounded support horizon located. | npm unpacked size: 8,063,782 bytes / 43 files. Bundle impact not measured. |
| E-JS-03 TypeScript 7.0.2 | [npm release](https://www.npmjs.com/package/typescript/v/7.0.2); [tagged Apache-2.0 license](https://github.com/microsoft/TypeScript/blob/v7.0.2/LICENSE.txt) | [microsoft/TypeScript](https://github.com/microsoft/TypeScript); [security route](https://github.com/microsoft/TypeScript/security/policy). Current registry release; no published time-bounded support horizon located. | npm unpacked size: 2,497,498 bytes / 416 files; platform compiler archives add OS impact. Compile performance not measured. |
| E-JS-04 Vite 8.3.0 | [npm release](https://www.npmjs.com/package/vite/v/8.3.0); [tagged MIT license](https://github.com/vitejs/vite/blob/v8.3.0/LICENSE) | [vitejs/vite](https://github.com/vitejs/vite); [security route](https://github.com/vitejs/vite/security/policy). Current registry release; no published time-bounded support horizon located. | npm unpacked size: 2,361,169 bytes / 37 files; Rolldown/Lightning CSS add native impact. Build performance not measured. |
| E-JS-05 @vitejs/plugin-react 6.1.1 | [npm release](https://www.npmjs.com/package/@vitejs/plugin-react/v/6.1.1); [tagged MIT license](https://github.com/vitejs/vite-plugin-react/blob/plugin-react@6.1.1/LICENSE) | [vitejs/vite-plugin-react](https://github.com/vitejs/vite-plugin-react); [security route](https://github.com/vitejs/vite-plugin-react/security/policy). Current registry release; no published time-bounded support horizon located. | npm unpacked size: 44,804 bytes / 8 files. Transform/build performance not measured. |
| E-JS-06 @playwright/test 1.63.0 | [npm release](https://www.npmjs.com/package/@playwright/test/v/1.63.0); [tagged Apache-2.0 license](https://github.com/microsoft/playwright/blob/v1.63.0/LICENSE) | [microsoft/playwright](https://github.com/microsoft/playwright); [security route](https://github.com/microsoft/playwright/security/policy). Current registry release; no published time-bounded support horizon located. | npm unpacked size: 28,544 bytes / 11 files; the `playwright` package and browser archive are separate. Browser execution performance not measured. |
| E-BR-01 Chromium r1243 / 153.0.8010.12 | [tagged browser manifest](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright-core/browsers.json); Chromium license/notices source is not available until the official platform artifact is resolved. | Microsoft Playwright controls revision selection; security/support status of the not-yet-acquired browser artifact is unresolved. | Browser archive size, hash, platform selection, install behavior, and performance are **Not Run**. This blocks browser acquisition. |

## Sanitized upstream runtime/tool advisory evidence

Supplemental method actually executed: `GET` each selected upstream repository's public
GitHub advisory endpoint
`https://api.github.com/repos/<owner>/<repo>/security-advisories?state=published&per_page=100`
at **2026-09-19T14:47:26Z**. No response bodies were retained. `Published
record count` is the returned array length. A zero record count is not evidence
that the product has no vulnerabilities: it means only that the queried upstream
repository endpoint returned no published GHSA records. Where that leaves
version-specific advisory coverage ambiguous, it is not used as the sole
assessment source.

| Evidence | Exact item | Upstream endpoint HTTP/result | Exact version assessment |
|---|---|---|---|
| GHSA-RT-01 | CPython 3.12.14 candidate | `python/cpython`: HTTP 200; published record count 0. | Supplemental only. Exact release/index assessment is recorded in RT-REL-01; no universal-absence conclusion is drawn from this endpoint. |
| GHSA-RT-02 | Node.js 22.23.2 | `nodejs/node`: HTTP 200; published record count 0. | Supplemental only. Exact release/index assessment is recorded in RT-REL-02; no universal-absence conclusion is drawn from this endpoint. |
| GHSA-RT-03 | npm 10.9.8 | `npm/cli`: HTTP 200; published record count 5. Declared npm ranges: `>=7.9.0,<8.11.0`, `<6.14.6`, `<6.13.4`, `<6.13.3`, `<6.13.3`. | 10.9.8 is outside all five returned declared ranges. This is a point-in-time upstream endpoint result only; FND-I01 still rechecks full tool/distribution provenance. |
| GHSA-RT-04 | uv 0.11.16 | `astral-sh/uv`: HTTP 200; published record count 6. Declared `uv` ranges: `<0.11.15`, `<=0.11.5`, `<=0.9.5`, `<=0.9.4`, `<=0.8.21`, `<0.8.5`. | 0.11.16 is outside all six returned declared ranges. This is a point-in-time upstream endpoint result only; owner license-branch decision remains Blocked. |

### Exact CPython and Node release/index assessment

This direct assessment was executed at **2026-09-19T14:54:32Z** using the
official release pages and current canonical publication indexes. It assesses
what the selected release includes and whether the reviewed current index shows
a subsequent security-release publication. It makes no universal claim that no
other vulnerability, disclosure, operating-system library issue, or future
advisory exists.

| Evidence | Exact candidate and official source | Dated result and applicability | Boundary |
|---|---|---|---|
| RT-REL-01 | [CPython 3.12.14 official release](https://www.python.org/downloads/release/python-31214/) and [official Python source-release index](https://www.python.org/ftp/python/) | The release page identifies 3.12.14 as a security release and lists fixes including CVE-2021-4189, CVE-2025-4330, CVE-2026-2297, CVE-2026-3644, and CVE-2026-4224. Those listed fixes are included in the exact 3.12.14 candidate. At review time, 3.12.14 was the highest published `3.12.*` entry in the official index; no subsequent 3.12 security-release artifact was listed. | Direct candidate advisory assessment recorded. This is not a complete distribution/native-library scan and does not prove universal absence. Those remain FND-I01 work. |
| RT-REL-02 | [Node.js 22.23.2 official release](https://nodejs.org/en/blog/release/v22.23.2) and [current official Node security-release feed](https://nodejs.org/en/feed/blog.xml) | The exact release page lists CVE-2026-56846, CVE-2026-56847, CVE-2026-56848, CVE-2026-56850, CVE-2026-58039, CVE-2026-58040, CVE-2026-58042, CVE-2026-58043, CVE-2026-58044, and CVE-2026-58045; the release includes the corresponding fixes. At review time, the feed's newest `Security Releases` entry was 2026-07-29 and linked the exact 22.23.2 release event; no later security-release feed entry was present. | Direct candidate advisory assessment recorded. This is not a complete distribution/OpenSSL/native-library scan and does not prove universal absence. Those remain FND-I01 work. |

## Python direct packages

The `Known direct impact` column is the exact-version distribution metadata
known before resolution, not a transitive inventory. Optional/extras paths are
not selected unless explicitly named. Every named package and all descendants
remain subject to FND-I01's license, provenance, script, telemetry, and OSV
review.

| Exact canonical package | Purpose / necessity; alternative | License / attribution | Known direct impact before lock | Support, binary/scripts, network/telemetry | Maintenance/security and advisory method | Exact pin, update/removal, SBOM/notices | Decision |
|---|---|---|---|---|---|---|---|
| [FastAPI 0.141.1](https://pypi.org/project/fastapi/0.141.1/) | Required versioned ASGI/OpenAPI boundary. A hand-built HTTP framework was rejected; no `standard`/`all` extra is selected. | MIT; retain license/copyright notice; E-PY-01. | `starlette`, `pydantic`, `typing-extensions`, `typing-inspection`, `annotated-doc`; selected Pydantic is also listed directly below for explicit control. | Python >=3.10, compatible with selected 3.12 policy. Pure Python package; no published lifecycle script. Runtime makes no telemetry/network calls by itself. | E-PY-01; OSV-E01. | Manifest equality pin only; lock every dependency and hashes in FND-I01. Remove by replacing API boundary. Add direct/transitive licenses to SBOM/notices. | Approved for M1 direct selection; overall admission remains Blocked. |
| [Uvicorn 0.53.0](https://pypi.org/project/uvicorn/0.53.0/) | Required real ASGI server. Hypercorn was considered and rejected to keep one server. No `standard` extra, reload, or worker convenience dependency is selected. | BSD-3-Clause; retain copyright and disclaimer; E-PY-02. | `click`, `h11`; typing extensions is conditional only below Python 3.11 and does not apply to selected 3.12 policy. | Python >=3.10. Pure Python baseline; no lifecycle script. Network listener is product-controlled later, not telemetry; no outbound behavior is admitted. | E-PY-02; OSV-E02. | Exact pin/lock; update requires lifecycle/shutdown and security review. Remove by replacing approved ASGI server. SBOM/notices include all locked packages. | Approved for M1 direct selection; overall admission remains Blocked. |
| [Pydantic 2.13.5](https://pypi.org/project/pydantic/2.13.5/) | Transport/configuration validation required through FastAPI. Dataclasses alone were rejected for the approved schema boundary. No email/timezone extra is selected. | MIT; retain license/copyright notice; E-PY-03. | `annotated-types`, exact `pydantic-core 2.46.5`, `typing-extensions`, `typing-inspection`. | Python >=3.9. `pydantic-core` has platform native wheels/source-build implications; no package lifecycle script known before lock. No runtime telemetry/network behavior admitted. | E-PY-03; OSV-E03. | Exact pin; FND-I01 verifies the chosen wheel/source hash and native provenance on Linux/macOS. Remove only with transport model replacement. SBOM/notices include core and its native artifacts. | Approved for M1 direct selection; overall admission remains Blocked. |
| [SQLAlchemy 2.0.54](https://pypi.org/project/SQLAlchemy/2.0.54/) | Required synchronous persistence/UoW and PostgreSQL seam. `sqlite3` alone was rejected except its approved standard-library adapter use. No driver/async extras are selected. | MIT; retain license/copyright notice; E-PY-04. | `greenlet` for common selected architectures and `typing-extensions >=4.6.0`; optional driver and async extras excluded. | Python >=3.7. `greenlet` can be native; SQLAlchemy has no network/telemetry role. No lifecycle script known before lock. | E-PY-04; OSV-E04. | Exact pin; lock and inspect greenlet wheel/source provenance. Removal requires a persistence-architecture decision. SBOM/notices cover ORM and resolved native artifacts. | Approved for M1 direct selection; overall admission remains Blocked. |
| [Alembic 1.20.0](https://pypi.org/project/alembic/1.20.0/) | Required explicit immutable migration chain. Hand-rolled migration history was rejected. | MIT; retain license/copyright notice; E-PY-05. | `SQLAlchemy >=2.0`, `Mako`, `typing-extensions`; `tomli` is conditional below Python 3.11 and does not apply. | Python >=3.10. Pure Python; no package lifecycle script. No outbound/telemetry behavior admitted. | E-PY-05; OSV-E05. | Exact pin; locked graph must prove Mako and shared SQLAlchemy compatibility. Removal requires an approved migration replacement. SBOM/notices include all locked packages. | Approved for M1 direct selection; overall admission remains Blocked. |
| [pytest 9.1.1](https://pypi.org/project/pytest/9.1.1/) | Required Python test runner. `unittest` alone was considered but does not provide the planned test workflow; no mock/plugin extras are selected. | MIT; retain license/copyright notice; E-PY-06. | `iniconfig`, `packaging`, `pluggy`, `pygments`; conditional Python <3.11 requirements do not apply. | Python >=3.10. Pure Python; no lifecycle script. No telemetry/network behavior admitted. | E-PY-06; OSV-E06. | Exact development-group pin; lock minimal plugins only. Remove only by replacing the approved test workflow. SBOM/notices include dev graph. | Approved for M1 direct selection; overall admission remains Blocked. |
| [Ruff 0.16.8](https://pypi.org/project/ruff/0.16.8/) | Required one coherent formatter/linter. Black/Flake8/isort combination was rejected to minimize tools. | MIT; retain license/copyright notice; E-PY-07. | No declared Python-package requirements. | Python >=3.7; native Rust executable wheels/source-build implications; no package lifecycle script. No telemetry/network behavior admitted. | E-PY-07; OSV-E07. | Exact development-group pin; FND-I01 records wheel/source hash per platform. Remove only by selecting a replacement toolchain. Include binary in SBOM/notices. | Approved for M1 direct selection; overall admission remains Blocked. |
| [mypy 2.3.1](https://pypi.org/project/mypy/2.3.1/) | Required strict Python type gate. Pyright was considered and rejected to keep the Python toolchain minimal. No optional report/cache extras are selected. | MIT; retain license/copyright notice; E-PY-08. | `typing_extensions >=4.6.0` for Python <3.15 (`>=4.14.0` for >=3.15), `mypy-extensions >=1.0.0`, `pathspec >=1.0.0`, `ast-serialize >=0.6.0,<1.0.0`, `librt >=0.13.0` on non-PyPy; `tomli >=1.1.0` only below Python 3.11. | Python >=3.10. May use compiled wheels; no lifecycle script. No telemetry/network behavior admitted. | E-PY-08; OSV-E08. | Exact development-group pin; lock platform conditionals. Remove only with a replacement strict type-gate decision. SBOM/notices include dev graph. | Approved for M1 direct selection; overall admission remains Blocked. |

## JavaScript direct packages and browser binary

| Exact canonical package/project | Purpose / necessity; alternative | License / attribution | Known direct impact before lock | Support, binary/scripts, network/telemetry | Maintenance/security and advisory method | Exact pin, update/removal, SBOM/notices | Decision |
|---|---|---|---|---|---|---|---|
| [react 19.3.0](https://www.npmjs.com/package/react/v/19.3.0) | Required UI runtime; no substitute is planned by P02. | MIT; retain license/copyright notice; E-JS-01. | No declared runtime dependency. | Node engine metadata allows the selected Node 22. Pure JavaScript; no package lifecycle script. No external analytics/crash dependency is admitted. | E-JS-01; OSV-E09. | Exact production pin and npm integrity lock. Removal requires a UI architecture decision. SBOM/notices include React. | Approved for M1 direct selection; overall admission remains Blocked. |
| [react-dom 19.3.0](https://www.npmjs.com/package/react-dom/v/19.3.0) | Required DOM renderer for React. Direct DOM-only UI was rejected as incompatible with the approved architecture. | MIT; retain license/copyright notice; E-JS-02. | `scheduler ^0.28.0`; its version and license are unresolved until FND-I01. Package metadata contains `start=node server.js`; it must not run in installation. | Node compatible. JavaScript package; declared script requires lifecycle-policy inspection. No telemetry is admitted. | E-JS-02; OSV-E10. | Exact production pin, immutable npm lock, explicit lifecycle-script audit. Remove with React replacement. Include direct and scheduler notices. | Conditional; FND-I01 script review and whole admission Blocked. |
| [typescript 7.0.2](https://www.npmjs.com/package/typescript/v/7.0.2) | Required strict frontend/generated-client types. JavaScript-only build was rejected. | Apache-2.0; preserve license, copyright, and any NOTICE obligations; E-JS-03. | Platform-specific TypeScript compiler packages at exact 7.0.2 are optional dependencies and must be enumerated by platform. | Requires Node >=16.20. Native platform package archives are selected by OS; no lifecycle script. No telemetry admitted. | E-JS-03; OSV-E11. | Exact development pin and immutable lock; FND-I01 records Linux/macOS package choice and provenance. Remove only with type-system replacement. SBOM/notices include selected compiler archive. | Approved for M1 direct selection; overall admission remains Blocked. |
| [vite 8.3.0](https://www.npmjs.com/package/vite/v/8.3.0) | Required production build/dev server. A hand-rolled bundler was rejected. | MIT; retain license/copyright and bundled notices; E-JS-04. | `postcss`, `rolldown`, `picomatch`, `tinyglobby`, `lightningcss`; optional `fsevents`. | Engine `^20.19.0 || >=22.12.0`, satisfied by Node 22.23.2. Native/binary risk via Rolldown/Lightning CSS; package's own scripts are publishing/development scripts and must be blocked from arbitrary lifecycle execution. No telemetry admitted. | E-JS-04; OSV-E12. | Exact development pin, npm integrity lock, inspect all binaries/scripts. Remove only through replacement build decision. SBOM/notices cover bundled output/tool graph. | Conditional; FND-I01 binary/script review and whole admission Blocked. |
| [@vitejs/plugin-react 6.1.1](https://www.npmjs.com/package/@vitejs/plugin-react/v/6.1.1) | Official React transform integration for Vite. Hand-maintained transform configuration was rejected. | MIT; retain license/copyright notice; E-JS-05. | `@rolldown/pluginutils ^1.0.1`. | Same Node engine range as Vite; JavaScript build plugin. Published development/prepublish scripts are not an installation approval. No telemetry admitted. | E-JS-05; OSV-E13. | Exact development pin and lock; FND-I01 inspects resolved plugin/scripts. Removal requires a Vite transform replacement. Include locked notices. | Conditional; FND-I01 script review and whole admission Blocked. |
| [@playwright/test 1.63.0](https://www.npmjs.com/package/@playwright/test/v/1.63.0) plus [Playwright Chromium revision 1243 / 153.0.8010.12](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright-core/browsers.json) | Required real built-browser T4 execution. DOM simulators and alternate browser drivers were rejected by testing policy. | Apache-2.0 for Playwright package; retain license/NOTICE obligations; E-JS-06/E-BR-01. Chromium's separate license/notices must be enumerated from the official acquired artifact before release. | Exact `playwright 1.63.0`; it in turn controls browser archive acquisition. | Node >=20, satisfied by Node 22. Chromium is an OS-specific binary download with substantial supply-chain and license impact. Browser download is network I/O; browser network traffic must be constrained to the real loopback application during tests. No analytics/crash reporting is admitted. | E-JS-06; OSV-E14. Chromium is **Not Run** until its official artifact resolves. | Exact dev pin; browser revision/version fixed above. FND-I01 must record archive URL, hash/signature where provided, platform package, install behavior, cache location, license and notices before acquisition. Removal means no T4 browser evidence and needs replacement approval. SBOM/notices must include package and browser binary. | Conditional; browser acquisition and whole admission Blocked. |

## Sanitized direct-advisory evidence

Method actually executed: one `POST` to
`https://api.osv.dev/v1/querybatch` at **2026-09-19T14:35:36Z**, with the 14
exact ecosystem/name/version tuples below. HTTP status was **200**. The response
was counted in memory and discarded; no response body, advisory text, account
data, or token was retained. `0` means the returned `vulns` array for that exact
direct tuple had zero entries at that time. It does not assess transitive
packages, browser archives, runtimes, future advisories, or package provenance.

| Evidence | OSV ecosystem | Exact name | Exact version | HTTP/result |
|---|---|---|---|---|
| OSV-E01 | PyPI | `fastapi` | `0.141.1` | 200 / advisory count 0 |
| OSV-E02 | PyPI | `uvicorn` | `0.53.0` | 200 / advisory count 0 |
| OSV-E03 | PyPI | `pydantic` | `2.13.5` | 200 / advisory count 0 |
| OSV-E04 | PyPI | `SQLAlchemy` | `2.0.54` | 200 / advisory count 0 |
| OSV-E05 | PyPI | `alembic` | `1.20.0` | 200 / advisory count 0 |
| OSV-E06 | PyPI | `pytest` | `9.1.1` | 200 / advisory count 0 |
| OSV-E07 | PyPI | `ruff` | `0.16.8` | 200 / advisory count 0 |
| OSV-E08 | PyPI | `mypy` | `2.3.1` | 200 / advisory count 0 |
| OSV-E09 | npm | `react` | `19.3.0` | 200 / advisory count 0 |
| OSV-E10 | npm | `react-dom` | `19.3.0` | 200 / advisory count 0 |
| OSV-E11 | npm | `typescript` | `7.0.2` | 200 / advisory count 0 |
| OSV-E12 | npm | `vite` | `8.3.0` | 200 / advisory count 0 |
| OSV-E13 | npm | `@vitejs/plugin-react` | `6.1.1` | 200 / advisory count 0 |
| OSV-E14 | npm | `@playwright/test` | `1.63.0` | 200 / advisory count 0 |

CPython, Node.js, npm CLI, uv, and Chromium were **not queried through OSV**
because this executed query had no canonical package tuple for their selected
distribution/artifact. That OSV-query fact is distinct from advisory assessment:
CPython and Node have the direct upstream assessments in `RT-REL-01/02`, and
npm/uv have upstream GHSA assessments in `GHSA-RT-03/04`. Chromium's advisory
assessment remains **Not Run**. Full distribution/native-library and resolved
graph assessment remains FND-I01 work for every item.

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

## Owner decision required before FND-I01

ADR-0011 normally admits verified MIT/BSD/ISC/Apache-2.0 only. The owner must
record all of the following, with reviewer/date, before a manifest, lock, or
download is authorized:

1. Approve or reject **PSF-2.0** for proposed **CPython 3.12.14**. If approved,
   the dependency steward may provision that exact official source distribution
   with its published verification artifacts; observed 3.12.3 remains rejected.
   If rejected, choose a compliant runtime architecture.
2. Approve or reject **Artistic-2.0** for npm 10.9.8. If rejected, select and
   fully admit a replacement single Node package-manager/lock workflow.
3. For uv 0.11.16, select either upstream **MIT** or **Apache-2.0** and approve
   that selected branch. This record intentionally makes no choice between them.

Until those three owner decisions exist, the
whole `FND-I00-DEP-001` admission is **Blocked**. FND-I01, package installation,
browser download, manifest creation, and lockfile creation are prohibited.

The prior direct CPython/Node advisory-evidence blocker is closed by the dated
official release/index assessments in `RT-REL-01/02`. Their narrow scope does
not approve an artifact, native library, resolved graph, or future advisory;
those checks remain mandatory and fail-closed at FND-I01.

## Compatibility, security, and documentation impact

This document changes no API, event, provider, database, configuration, or
module contract. It creates no migration or rollback obligation. It mitigates
`R-018` only at direct-selection scope; the resolved graph and browser binary
remain open supply-chain risks until FND-I01. It contains no secret, provider
state, prompt/response, source-content, environment value, or telemetry data.

The next required action is the owner decision above. Only after it resolves the
Blocked status may FND-I01 be separately authorized to create manifests/locks,
perform the fail-closed graph comparison, and record real clean-resolution
evidence. This record authorizes no package installation, browser download,
application code, tests, CI, external resources, or release claim.
