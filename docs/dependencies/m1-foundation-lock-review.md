# M1 foundation lock review

- Record: `FND-I01-LOCK-001`, reviewed 2026-09-19.
- Owner/module: Foundation; `PLAN-FND` increment `FND-I01`.
- Requirements/scenarios: `NFR-LIC-001`, `FND-VER-001`, `FND-ENV-001`,
  dependency portions of `FND-DEP-001..004`; macOS `FND-ENV-002` remains Blocked.
- Admission: [FND-I00-DEP-001](m1-foundation-admission.md).
- Contracts: no published product contract changed. No product implementation.

## Scope ruling

On 2026-09-19 the owner directed development to proceed with the current exact
pins, recording remediation for later where a development candidate remains
usable. The reviewed findings below are deferred, not cleared or approved for
redistribution. SBOM/notices generation and full supply-chain blocking remain
FND-I09/M1 Task 5 and pre-public-release work. This record replaces the pending
amendment packet. No browser was acquired or run: Chromium is test
infrastructure, not an AgentMonitor delivery artifact.

The controller subsequently directed use of complete system CPython 3.12.3
for this local M1 development milestone only, stopping the custom 3.12.14
rebuild. The development policy is `>=3.12.3,<3.13`, exact reference 3.12.3;
release/deployment must upgrade to 3.12.14 or later in the 3.12 series and
reverify. This exception does not claim later security fixes are present.
Real sqlite3, ctypes, bz2 and lzma imports are required setup checks, not
product/database acceptance. The signed 3.12.14 source build was setup-only
and not selected because optional modules were missing.

## Exact graph and install policy

The authoritative complete inventories, causal edges, platform markers,
canonical URLs and artifact hashes are [backend/uv.lock](../../backend/uv.lock)
and [frontend/package-lock.json](../../frontend/package-lock.json).
Runtime and development groups remain separate; direct equality pins are
unchanged. Packaging is disabled until a backend package exists. npm is
private/unpublished, lockfile version 3. No Git/path dependency is admitted.

Candidate archive review covered all 30 Python package tuples (one applicable
Linux/universal wheel each) and all 68 npm package tuples, including all 47
optional platform packages. Every reviewed archive digest matched its registry
metadata/candidate lock. All 68 npm registry signatures verified; three older
packages use the old registry key whose expiry follows their publication.
This verifies registry provenance, not publisher identity or complete native
source-to-binary reproducibility. Alternative Python platform wheels are
locked, not claimed executed or individually archive-inspected.

No explicit npm preinstall/install/postinstall was present in the reviewed
archives. Registry metadata synthesizes `node-gyp rebuild` for fsevents 2.3.3,
and its lock has `hasInstallScript`; the integrity-matched published archive
has neither that script nor `binding.gyp`. It is optional, Darwin-only, skipped
on Linux before extraction; `--ignore-scripts` independently disables hooks.
Lightning CSS's `prepare=patch-package` is a publisher workflow, not an
authorized install hook. Python uses wheels only (`--no-build`). Native
components include Pydantic core, greenlet, SQLAlchemy, mypy/librt/ast-serialize,
Ruff, TypeScript platform binaries, Rolldown and Lightning CSS.

Static review found no analytics dependency or automatic outbound telemetry
declaration. It is not a runtime network-isolation certification. Install
traffic is limited by explicit canonical registry options and clean caches;
package lifecycle scripts and automatic browser download are disabled.

## Deferred risks — not release clearance

| Component / causal parent | Finding and required Task 5 / release reassessment |
| --- | --- |
| greenlet 3.5.6 / SQLAlchemy; typing-extensions 4.16.0 / shared Python graph | MIT AND PSF-2.0; PSF-2.0 respectively. Preserve actual licenses and assess redistribution obligations. |
| packaging 26.3 / pytest; pathspec 1.1.1 / mypy | Apache-2.0 OR BSD-2-Clause needs branch selection; MPL-2.0 needs file-level notice/source-obligation review. |
| mypy 2.3.1 and librt 0.15.0 | Actual archives also contain historical Python/PSF, BSD-2-Clause base64 and Apache/MIT typeshed notices. Inventory bundled material. |
| lightningcss 1.33.0 and eleven platform archives / Vite | MPL-2.0, native `.node`, no install hooks. Review file-level copyleft and native provenance. |
| TypeScript 7.0.2 and twenty optional native archives | Unicode, W3C Software/Document and Community Final Specification Agreement notices; Go BSD-3-Clause plus Google patent grant. Go x/text 0.38.0 has GO-2026-5970 / CVE-2026-56852 (fixed 0.39.0). |
| Vite 8.3.0 bundled string-hash 1.1.3 | CC0-1.0; retain exact bundled provenance and license decision. |
| Playwright 1.63.0 bundled minimatch 10.2.5; caniuse-lite 1.0.30001799 | BlueOak-1.0.0 and CC-BY-4.0; attribution/notice review remains. |
| Playwright core WebP WASM | libwebp commit `3757b8afeb54e305eaef18502812a9a88b7ed662`, BSD-3-Clause plus WebM patent grant; Emscripten MIT/NCSA. Build uses `emsdk latest`; exact shipped compiler provenance unresolved. |
| Rolldown 1.2.9, fifteen native archives / Vite | Platform archives omit license copies; same-release upstream MIT and third-party notices located. Preserve those in later notice generation. |
| Playwright bundled @hono/node-server 1.19.14 | GHSA-frvp-7c67-39w9, Moderate Windows traversal, fixed 1.19.15; not a Linux exposure claim. |
| Playwright bundled baseline-browser-mapping 2.10.40 | GHSA-w5vr-8v7q-w6rv, Moderate, fixed 2.11.0. |
| Playwright bundled brace-expansion 5.0.7; browserslist 4.28.4 | High: GHSA-mh99-v99m-4gvg / GHSA-rgw5-rvv9-x895 (fixed 5.0.9); GHSA-73wf-gq98-2v4g / GHSA-c83g-rgw3-j3cx (fixed 4.28.7). |
| Playwright bundled fast-uri 3.1.3 | Six High advisories: GHSA-5jgf-p345-68v8, GHSA-7p8r-x3mc-p8w7, GHSA-f65p-4m7j-42xc, GHSA-fph4-wmhf-6fwf, GHSA-jqff-g426-hqxp, GHSA-v2hh-gcrm-f6hx; fixed 3.1.6. |
| Playwright bundled ip-address 10.2.0 | GHSA-22jq-vg5j-6vgg / GHSA-4xrf-jv44-h6hh (Moderate), GHSA-mwp4-54f8-5fhr (High); fixed 10.3.1. |
| Playwright's unused Chromium r1243 / 153.0.8010.12 | Critical CVE-2026-87464 affects versions below 153.0.8010.36. No browser acquisition/execution in FND-I01. Task 5 may assess an existing local real Chrome/Chromium, recording its exact version and issues. |

OSV exact queries returned HTTP 200 with no advisories for the 98 declared
tuples at review time. Supplemental review of 173 bundled tuples found the
16 advisory records above across seven components. This is point-in-time
evidence, not absence of vulnerabilities. Sanitized investigation evidence and
the detailed execution handoff are retained in the ignored task workspace;
raw advisory response bodies were not retained. Recheck canonical
[OSV](https://osv.dev/) records and actual bundled notices at Task 5.

## Verification and repeatable development commands

Linux verification on 2026-09-19 passed with CPython 3.12.3, Node 22.23.2,
npm 10.9.8 and uv 0.11.16: fresh-cache frozen installs (29 Python / 26 npm
packages), 21 checker tests after meaningful Red and refactor, Ruff formatting
and lint, strict mypy, strict TypeScript, temporary Vite smoke build and the
documentation gate with installed dependencies present. Independent lock
generation from manifests only produced byte-identical locks. Both managers
rejected deliberately mismatched isolated manifest/lock copies. These results
cover FND-I01 development tooling only, not clearance of deferred release risks.

Execution results and exact local provisioning paths are recorded in the
FND-I01 handoff. Run from the repository root using the selected executables.
`PYTHON`, `NODE`, `NPM`, `UV` below denote explicit executable paths, not
environment discovery. Start with an empty project-local environment/cache;
do not overwrite another developer's environment. No `.env` is loaded.

```sh
"$PYTHON" tooling/foundation/check_toolchain.py --root . --node "$NODE" --npm "$NPM" --uv "$UV"
"$UV" lock --project backend --check --python "$PYTHON" --no-python-downloads --no-config --default-index https://pypi.org/simple
"$UV" sync --project backend --frozen --no-build --python "$PYTHON" --no-python-downloads --no-config --default-index https://pypi.org/simple
cd frontend
"$NPM" ci --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org
"$NPM" run typecheck --ignore-scripts
```

`uv lock --check` is mandatory before `uv sync --frozen`: frozen alone skips
freshness validation. npm `ci` rejects manifest/lock mismatch. Verification
commands use an empty inherited environment and explicit caches/config paths.
The Node configuration is checked now; app typechecking requires real future
`src` input and is not claimed here. `skipLibCheck` excludes third-party
declarations only; project source remains strict with unchecked index access
and no emit. Vite disables `.env` discovery (`envDir: false`). A temporary
empty input proves the compiler/bundler executes, not a product build.

Real macOS is Blocked (no host). Product UI/browser, SQLite, HTTP, provider,
hosted CI and live verification are Not Run. Git preflight is separately
Blocked without a configured remote/upstream. No secrets, provider profiles,
database migrations, public contracts or remote state are changed. Rollback
is a normal revert of this increment; ignored local caches/runtimes are not
release artifacts. FND-I09 must produce and gate actual SBOM/notices before
any release claim.
