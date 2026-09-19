# M1 foundation admission amendment candidate

- Record ID: `FND-I01-A`
- Version: 0.1.0
- Status: **Pending owner/security decision**
- Evidence date: 2026-09-19
- Owner: Pavlo Sidelov; technical review: Foundation dependency/security steward
- Plan/increment: `PLAN-FND` 0.2.0-draft / FND-I01 admission prerequisites
- Requirements: `NFR-LIC-001`, `NFR-SEC-001`, `NFR-PRIV-001/002`,
  `NFR-TEST-001/002`, `NFR-PLAT-001`, `NFR-DOC-001`
- Supporting acceptance: `AC-V1-005/007`, `AC-TEST-001/002/006`
- Scenarios: `FND-DEP-001..004`, `FND-VER-001`, `FND-ENV-001/002`,
  `FND-DOC-001`; none gains an implementation pass from this packet.
- Contract impact: None. Proposed `foundation.contracts.v1` and
  `CTR-FND-001..008` 1.0.0 are unchanged.

## Decision boundary

The current candidate graph is not admitted or executable. Reject the selected
browser r1243 / Chrome for Testing (CfT) 153.0.8010.12 for Critical
CVE-2026-87464. Propose a different exact browser for quarantine review and two
temporary security containments; no decision below is approved. The
[FND-I00 record](m1-foundation-admission.md) remains the historical direct-selection
record, not current graph or browser clearance. This pending packet changes no pin,
manifest, lock, executable, or product contract.

The [dependency policy](../engineering/dependency-and-license-policy.md) and
[ADR 0011](../decisions/0011-copyright-and-dependency-licenses.md) govern every
decision. Approval would apply only to the versions, branches, obligations,
scope, and expiry specified here. It would not waive future packages/versions,
provenance gaps, notices, or the final graph gate.

Exact canonical PyPI release metadata and npm `latest` tags rechecked on
2026-09-19 still identify FastAPI 0.141.1, Uvicorn 0.53.0, Pydantic 2.13.5,
SQLAlchemy 2.0.54, Alembic 1.20.0, pytest 9.1.1, Ruff 0.16.8, mypy 2.3.1,
React/React DOM 19.3.0, TypeScript 7.0.2, Vite 8.3.0,
@vitejs/plugin-react 6.1.1, and @playwright/test 1.63.0 as current stable
direct packages. Their exact registry links are in the FND-I00 record;
latest checks used `https://pypi.org/pypi/<name>/json` and
`https://registry.npmjs.org/<name>`. No newer stable direct package carrier was
available in those sources. That is point-in-time evidence, not a reason to
approve the vulnerable graph or select a prerelease.

## Browser rejection and exact candidate

The [Playwright 1.63.0 browser manifest](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright-core/browsers.json)
selects Chromium revision 1243, titled Chrome for Testing, version
153.0.8010.12. The [Chrome CNA record](https://cveawg.mitre.org/api/cve/CVE-2026-87464)
identifies versions before 153.0.8010.36 as affected by a WebGL use-after-free;
the [2026-09-08 Chrome release](https://chromereleases.googleblog.com/2026/09/stable-channel-update-for-desktop_0808145027.html)
rates it Critical and publishes that fixed Linux version. Therefore r1243's
153.0.8010.12 is rejected. This finding does not itself reject the stable
Playwright 1.63.0 package: its bundled advisories and provenance remain separate
unresolved gates below. Locally installed Google Chrome 152.0.7977.75-1 is not
proposed as a safe substitute.

Propose **official CfT 153.0.8010.52, linux64 (Linux x64), full Chrome archive**
as the least-change browser candidate, retaining Playwright 1.63.0 and later
launching through an explicit executable path. Same-major patch proximity is
the rationale, not proof of compatibility. Playwright's
[executablePath documentation](https://playwright.dev/docs/api/class-browsertype#browser-type-launch-option-executable-path)
warns that compatibility with a different browser executable is not guaranteed.
Real launch, protocol, and built-UI evidence remain Not Run.

| Evidence | Exact observation / limit |
|---|---|
| Version/download authority | [CfT version JSON](https://googlechromelabs.github.io/chrome-for-testing/153.0.8010.52.json) and [Stable channel JSON](https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json) identify 153.0.8010.52, Chromium source revision `1681091`, and the linux64 URL below. |
| Vendor security release | [2026-09-17 desktop release](https://chromereleases.googleblog.com/2026/09/stable-channel-update-for-desktop_0194356994.html) publishes Linux 153.0.8010.52 with 16 security fixes, including Critical CVE-2026-93374 and CVE-2026-93372. It is beyond the CVE-2026-87464 fix; this is not a complete binary vulnerability clearance. |
| Exact archive | [chrome-linux64.zip](https://storage.googleapis.com/chrome-for-testing-public/153.0.8010.52/linux64/chrome-linux64.zip), HTTPS HEAD 200; no archive body acquired. |
| Object metadata | 195,708,470 bytes; `application/zip`; stored encoding `identity`; Last-Modified `Thu, 17 Sep 2026 05:37:52 GMT`; generation `1789623472726407`; metageneration `1`; ETag `04f593dceea417bb9b03a5613ca380b6`. |
| Published integrity | GCS `crc32c=cS+Qeg==`, `md5=BPWT3O6kF7ubA6VhPKOAtg==`. These and the ETag are transport/object checks, not authenticated strong binary provenance. |
| Strong digest/signature | Version JSON has no digest/signature field; HEAD of this exact archive plus `.sha256`, `.sha256sum`, and `.sig` returned 404. No independently authenticated SHA-256/signature was found in these inspected sources. A locally calculated SHA-256 would identify acquired bytes, not authenticate the upstream build. Strong provenance remains Blocked. |
| License/notices | Exact binary inventory, complete license texts, notices, embedded/native components, and distribution obligations are uninspected. Chromium source licensing alone cannot certify the CfT binary. No artifact-specific external notice inventory was established in the inspected metadata. |

### Proposed quarantine-only ordering

This is a requested amendment to the earlier pre-acquisition ordering, not an
authority inferred from license approval. The inspected official metadata does
not expose the archive's complete embedded notices; inspecting those exact
members before acquiring any archive bytes is therefore impossible with the
available evidence.

1. After explicit approval of decision Q01, acquire only the exact archive above
   into a new ignored, isolated AgentMonitor project-local quarantine directory
   as inert data. Do not execute browser/package code, use a system install,
   invoke a broad Playwright installer, or change any existing/default profile.
2. Verify TLS origin and final URL, version/platform, object generation, length,
   CRC32C and MD5; reject changed/missing metadata or mismatches. Record a local
   SHA-256 separately and search for authenticated upstream strong provenance.
   Neither MD5 nor the new local hash clears that unresolved requirement.
3. Inspect archive structure, safe member paths, licenses/notices, embedded
   components and native inventory without execution. Reject traversal,
   escaping links, unexpected binaries, missing terms, or unreviewed obligations.
   Inventory evidence is not an SBOM/notices generation pass.
4. Security/dependency review must either admit the exact inspected object after
   all required provenance/license/advisory gates pass, or reject/delete that
   exact isolated candidate. If strong provenance remains unresolved, admission
   and execution stay Blocked; quarantine approval cannot waive it.
5. Only subsequent execution clearance permits an explicit path to this admitted
   project's `chrome-linux64/chrome`, isolated project-local test profile and
   loopback-only application testing. Compatibility failure stops the workflow;
   do not fall back to the rejected/default/system browser.

No FFmpeg, headless-shell, ChromeDriver, OS package installation, `install-deps`,
service change, default provider/browser profile access, or browser execution
is included in Q01. The [tagged Playwright registry](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright-core/src/server/registry/index.ts)
can select additional browser/FFmpeg artifacts through a broad installer.
Any eventual browser cache must be explicitly ignored and project-local
(including an explicit `PLAYWRIGHT_BROWSERS_PATH` if Playwright manages it).

Recheck current vendor advisories before quarantine review and before later
execution. Version/object changes require a new exact record; never silently
advance a URL. A fixed stable Playwright carrier should replace these temporary
arrangements only through new admission and compatibility evidence. On rejection
or replacement, remove only the exact AgentMonitor-owned candidate/cache after
retaining sanitized review evidence; no system browser is modified.

## Security dispositions and proposed containments

The prior candidate review's zero results for 98 locked package tuples did not
cover all bundled code. Its bundle inventory found these exact components;
the [Playwright 1.63.0 source lock](https://github.com/microsoft/playwright/blob/v1.63.0/package-lock.json)
independently fixes their versions. Canonical advisory records were rechecked
on 2026-09-19. A scoped disposition below does not claim a package, advisory,
or vulnerable bundled implementation is absent. Runtime containment enforcement
has not been implemented or tested.

| Decision | Exact affected code / fixed version / evidence | Proposed fail-closed treatment |
|---|---|---|
| S01 — Pending owner/security decision | `golang.org/x/text v0.38.0`, a linked TypeScript 7.0.2 compiler dependency: the native release [go.mod](https://github.com/microsoft/typescript-go/blob/typescript/v7.0.2/go.mod) pins it and compiler [locale code](https://github.com/microsoft/typescript-go/blob/typescript/v7.0.2/internal/locale/locale.go) imports its language package. [GO-2026-5970](https://pkg.go.dev/vuln/GO-2026-5970) / CVE-2026-56852 concerns an infinite loop in `unicode/norm` on invalid UTF-8; fixed v0.39.0. No severity field is published in that Go record. Linking is not proof that every affected norm call is reached, nor evidence of immunity. | Permit only repository/generated compiler inputs with strict UTF-8 validation of **every compiler input before any tsc invocation**: source/declaration files, compiler libraries and resolved dependency declarations, configurations, response files and input paths must be explicitly enumerated inside reviewed project roots. No arbitrary external path, symlink escape, unvalidated incremental/watch input, external project reference, or validation-to-use content change. If exhaustive validation cannot be demonstrated, tsc remains Blocked. Containment removes the advisory's invalid-byte condition; it does not fix x/text. |
| S02 — Pending owner/security decision | `brace-expansion 5.0.7` is executable through minimatch in Playwright 1.63.0 / playwright-core 1.63.0 bundles. The source lock fixes 5.0.7; [file matching](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright/src/util.ts) calls minimatch without disabling brace expansion. High [GHSA-mh99-v99m-4gvg](https://api.osv.dev/v1/vulns/GHSA-mh99-v99m-4gvg) fixes unbounded expansion at 5.0.8; High [GHSA-rgw5-rvv9-x895](https://api.osv.dev/v1/vulns/GHSA-rgw5-rvv9-x895) fixes the intermediate-array bypass at 5.0.9. The combined fix threshold is **5.0.9**. | Permit only reviewed fixed literal repository-owned test, file and ignore patterns, with bounded expansion. Reject operator/external patterns, CLI pattern overrides, externally selected configs, and dynamic glob construction before Playwright starts. Include every minimatch consumer used by the workflow, not just testMatch. No npm override can replace code already inlined into a bundle. If the pattern boundary cannot be enforced, Playwright remains Blocked. |

For **each** S01/S02 proposal, the accountable decision owner is Pavlo Sidelov
with the security reviewer; Foundation owns enforcement and rechecks.
Expiry is **2026-10-03T00:00:00Z or publication of the first stable carrier
with the fixed code, whichever occurs first**: TypeScript carrying x/text
at least v0.39.0 for S01; Playwright carrying brace-expansion at least 5.0.9
in every shipped copy for S02. This is less than 30 days from review.
At expiry, stop affected execution until the fixed carrier is independently
admitted; no automatic extension or assumed upgrade compatibility.

Reassess immediately on any package/bundle/input/path/config/pattern change,
new advisory or affected-range change, new workflow using these functions,
or failed containment check. Approval would accept only this bounded residual
risk and expiry; meaningful fail-closed enforcement and real verification must
precede execution. A development-only label alone is not containment.

### Evidence-bound non-blocking findings for the proposed Linux workflow

These dispositions preserve the narrow reachability conclusions. Each becomes
Blocked for reassessment when its listed premise changes; none clears the whole
carrier, browser, native inventory, or execution gate.

| Embedded component | Advisory / same-line fix | Scoped source evidence and reassessment trigger |
|---|---|---|
| `@hono/node-server 1.19.14` | Moderate [GHSA-frvp-7c67-39w9](https://api.osv.dev/v1/vulns/GHSA-frvp-7c67-39w9); 1.19.15 | Affected `serve-static` functionality is outside the examined import path and the finding is Windows-specific. Playwright's [utilsBundle imports](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright-core/src/utilsBundle.ts) reach SDK [streamableHttp](https://github.com/modelcontextprotocol/typescript-sdk/blob/v1.29.0/src/server/streamableHttp.ts), which imports `getRequestListener`; Hono's exact [root exports](https://github.com/honojs/node-server/blob/v1.19.14/src/index.ts) do not export serve-static. Non-blocking for this Linux scope. Reassess on static serving, additional bundle imports, or platform changes; no general Hono safety claim. |
| `baseline-browser-mapping 2.10.40` | Moderate [GHSA-w5vr-8v7q-w6rv](https://api.osv.dev/v1/vulns/GHSA-w5vr-8v7q-w6rv); 2.11.0 | Invalid-input process termination. The ordinary Playwright transform's [exact Babel options](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright/src/transform/babelBundle.ts) disable browserslist configuration discovery, babelrc and configFile; [transform code](https://github.com/microsoft/playwright/blob/v1.63.0/packages/playwright/src/transform/transform.ts) states it does not use browserslist data. Non-blocking only for that ordinary transform path. Reassess custom transforms/plugins, target queries, browserslist data or external configuration. |
| `browserslist 4.28.4` | High [GHSA-73wf-gq98-2v4g](https://api.osv.dev/v1/vulns/GHSA-73wf-gq98-2v4g) and [GHSA-c83g-rgw3-j3cx](https://api.osv.dev/v1/vulns/GHSA-c83g-rgw3-j3cx); 4.28.7 | Untrusted custom stats can crash/write prototypes; distinct query results can cause unbounded memory. Same disabled ordinary transform configuration path as above. Reassess any custom stats, queries, target configuration or programmatic browserslist use. |
| `fast-uri 3.1.3` | High host-confusion/SSRF: [GHSA-v2hh-gcrm-f6hx](https://api.osv.dev/v1/vulns/GHSA-v2hh-gcrm-f6hx) fixed 3.1.4; [GHSA-7p8r-x3mc-p8w7](https://api.osv.dev/v1/vulns/GHSA-7p8r-x3mc-p8w7) fixed 3.1.5; [GHSA-5jgf-p345-68v8](https://api.osv.dev/v1/vulns/GHSA-5jgf-p345-68v8), [GHSA-f65p-4m7j-42xc](https://api.osv.dev/v1/vulns/GHSA-f65p-4m7j-42xc), [GHSA-fph4-wmhf-6fwf](https://api.osv.dev/v1/vulns/GHSA-fph4-wmhf-6fwf), [GHSA-jqff-g426-hqxp](https://api.osv.dev/v1/vulns/GHSA-jqff-g426-hqxp) fixed 3.1.6 | Carrier source lock traces it through Ajv 8.20.0 / SDK 1.29.0. SDK's [default validator](https://github.com/modelcontextprotocol/typescript-sdk/blob/v1.29.0/src/validation/ajv-provider.ts) uses synchronous compile with no loadSchema/remote-schema loader. No network policy or remote-schema consumer is proposed. Reassess custom Ajv injection, remote schemas, URI-based trust/host policies, or remote MCP workflows. This does not establish that URI parsing itself is absent. |
| `ip-address 10.2.0` | Moderate [GHSA-22jq-vg5j-6vgg](https://api.osv.dev/v1/vulns/GHSA-22jq-vg5j-6vgg) fixed 10.2.1; Moderate [GHSA-4xrf-jv44-h6hh](https://api.osv.dev/v1/vulns/GHSA-4xrf-jv44-h6hh) fixed 10.2.2; High [GHSA-mwp4-54f8-5fhr](https://api.osv.dev/v1/vulns/GHSA-mwp4-54f8-5fhr) fixed 10.3.1 | Carrier source lock reaches socks 2.8.9. Its [exact published-source commit](https://github.com/JoshGlazebrook/socks/blob/c191a5c3b12256404ab798f9e6105e31d94254df/src/client/socksclient.ts) imports Address6 for byte decoding, not affected address trust classification. Those methods are unused in the examined path. Reassess IP-based allow/deny policy, Address4 text interpretation, private/loopback classification, or additional consumers. |

`fsevents 2.3.3` remains a macOS-only optional Vite dependency. Its exact
[archive-matching manifest](https://github.com/fsevents/fsevents/blob/v2.3.3/package.json)
declares Darwin and no install hook; registry `install=node-gyp rebuild` and
the lock's `hasInstallScript` marker do not authorize execution. npm 10.9.8's
[reifier](https://github.com/npm/cli/blob/v10.9.8/workspaces/arborist/lib/arborist/reify.js)
checks optional platform compatibility before extraction; its
[rebuild implementation](https://github.com/npm/cli/blob/v10.9.8/workspaces/arborist/lib/arborist/rebuild.js)
guards lifecycle scripts with ignoreScripts. Keep Linux frozen installs at
`npm ci --ignore-scripts`, with no OS override or rebuild. This source-derived
Linux disposition is not an executed frozen-install pass. macOS is **Blocked**.

## Consolidated exceptional-license decisions

The table records actual prior archive/bundle evidence, not only registry
headlines. The existing ignored candidate review inspected 98 archives and
retained their full license texts; this amendment rechecked those records and
exact canonical source licenses/metadata without acquiring packages. Matching
notice hashes are below. Distribution obligations remain mandatory even for
development dependencies. Check exactly one Approve/Reject choice per row;
all boxes are currently empty.

| ID / decision | Exact component and causal parent | Archive/bundle evidence, proposed branch and obligations |
|---|---|---|
| L01: [ ] Approve [ ] Reject | `greenlet 3.5.6` via SQLAlchemy 2.0.54 | Linux cp312 wheel contains [MIT LICENSE](https://github.com/python-greenlet/greenlet/blob/3.5.6/LICENSE) and [LICENSE.PSF](https://github.com/python-greenlet/greenlet/blob/3.5.6/LICENSE.PSF), with Stackless-derived platform files assigned PSF terms. **MIT AND PSF-2.0**, not an alternative choice: retain both complete licenses/copyrights and PSF change summary when distributing applicable derivatives. |
| L02: [ ] Approve [ ] Reject | `typing-extensions 4.16.0` via FastAPI 0.141.1, Pydantic 2.13.5, SQLAlchemy 2.0.54, Alembic 1.20.0 and mypy 2.3.1 | Universal wheel [LICENSE](https://github.com/python/typing_extensions/blob/4.16.0/LICENSE) includes PSF-2.0 and historical Python material. Retain the complete file, copyrights and applicable derivative-change summaries; no endorsement/trademark right is granted. |
| L03: [ ] Approve [ ] Reject | `packaging 26.3` via pytest 9.1.1 | Universal wheel contains LICENSE, LICENSE.APACHE and LICENSE.BSD. The [umbrella license](https://github.com/pypa/packaging/blob/26.3/LICENSE) offers Apache-2.0 OR BSD-2-Clause; propose **BSD-2-Clause**. Preserve [BSD notice/disclaimer](https://github.com/pypa/packaging/blob/26.3/LICENSE.BSD) in source and binary materials, retain the archive's legal files and bundled MIT license-parser attribution. No Apache branch is selected by this decision. |
| L04: [ ] Approve [ ] Reject | `pathspec 1.1.1` via mypy 2.3.1 | Universal wheel's [LICENSE](https://github.com/cpburnz/python-pathspec/blob/v1.1.1/LICENSE) is MPL-2.0. Preserve notices; if distributing executable covered code, make the corresponding covered source and modifications available under MPL and tell recipients how to obtain it. Respect file-level coverage, patent grant/termination and no restriction of recipients' MPL rights. No claim that AgentMonitor as a whole becomes MPL. |
| L05: [ ] Approve [ ] Reject | `lightningcss 1.33.0` plus the 11 exact 1.33.0 platform packages listed below, via Vite 8.3.0 | Wrapper and all 11 inspected archives contain the same [MPL-2.0 LICENSE](https://github.com/parcel-bundler/lightningcss/blob/v1.33.0/LICENSE); each platform archive contains a native .node member. Same MPL notices, covered-source/modification availability, recipient-information and patent conditions as L04. Approval concerns these terms only; native/embedded component provenance and remaining inventory still require review. |
| L06: [ ] Approve [ ] Reject | Direct `mypy 2.3.1` and `librt 0.15.0` via mypy | Actual universal mypy wheel and Linux cp312 librt wheel [mypy LICENSE](https://github.com/python/mypy/blob/v2.3.1/LICENSE) / [librt LICENSE](https://github.com/mypyc/librt/blob/v0.15.0/LICENSE) include PSF/historical Python terms for pythonsupport.h/getargs.c/getargsfast.c beyond MIT metadata. Retain complete MIT, PSF, BeOpen, CNRI, CWI and applicable other texts; include brief summaries of applicable Python-derived changes when redistributed. Preserve BSD-2 base64 and Apache/MIT typeshed notices where shipped, including source/binary notice conditions. Source-availability requirements from MPL elsewhere remain separate; PSF change-summary terms do not themselves impose a blanket source-release obligation. Uninspected mypy native wheels remain outside this evidence. |
| L07: [ ] Approve [ ] Reject | `string-hash 1.1.3` bundled in Vite 8.3.0 | Vite archive LICENSE.md contains CC0-1.0; exact version is in [Vite's tagged lock](https://github.com/vitejs/vite/blob/v8.3.0/pnpm-lock.yaml). Upstream's [published-source README](https://github.com/darkskyapp/string-hash/blob/5bf7547a91372c399f4052cc1094a93f73e10284/README.md) provides the CC0 dedication. Preserve dedication/disclaimer in the full Vite notice; do not infer patent or trademark grants from CC0. |
| L08: [ ] Approve [ ] Reject | `typescript 7.0.2` and all 20 exact `@typescript/typescript-* 7.0.2` platform packages identified below | Actual NOTICE.txt matches the [native release notice](https://github.com/microsoft/typescript-go/blob/typescript/v7.0.2/NOTICE.txt). Preserve the **entire** notice: Apache-2.0 base, Unicode Data Files and Software, W3C Software and Document, Web Background Synchronization's W3C Community Final Specification Agreement, Go BSD and Google patent grants, and **WHATWG DOM CC-BY-4.0**, omitted from the earlier decision summary. Preserve attribution/license links, indicated changes and applicable modification notices; retain patent grant conditions/termination and covered-contribution scope. CC-BY prohibits additional restrictions on licensed material and requires attribution and change indication when shared. No generic EULA/LGPL boilerplate establishes an actual LGPL component. |
| L09: [ ] Approve [ ] Reject | `minimatch 10.2.5` in Playwright 1.63.0 esmLoader and playwright-core 1.63.0 utilsBundle, via @playwright/test | Actual sidecar LICENSE files carry [BlueOak-1.0.0](https://github.com/isaacs/minimatch/blob/693c82377d0948401be4c6d3220c9a74132ab112/LICENSE.md). Preserve full license/notices and ensure recipients receive the license text or required notice/link; retain its copyright/patent permission and disclaimer conditions. This license choice does not clear bundled brace-expansion advisories. |
| L10: [ ] Approve [ ] Reject | `caniuse-lite 1.0.30001799` in Playwright 1.63.0 babelBundle, via @playwright/test | Actual babelBundle.js.LICENSE includes [CC-BY-4.0](https://github.com/browserslist/caniuse-lite/blob/aef76b667ead9acd16d2d9493b890df4473b3dfc/LICENSE). Preserve creators/copyright, license link/text, disclaimer and source attribution supplied with the material; identify modifications and retain prior change indications when sharing. Do not impose additional restrictions or imply endorsement. |
| L11: [ ] Approve [ ] Reject | WebP codec in `playwright-core 1.63.0`, via playwright / @playwright/test 1.63.0 | Exact [webp_codec.LICENSE](https://github.com/microsoft/playwright/blob/v1.63.0/packages/utils/webp/webp_codec.LICENSE) includes BSD-3-Clause libwebp, WebM patent terms and Emscripten MIT/NCSA alternatives. Propose **MIT for the Emscripten portion**, not NCSA; preserve the full codec notice, BSD source/binary attributions/disclaimer/non-endorsement, MIT notices and WebM patent grant/termination conditions. The [build script](https://github.com/microsoft/playwright/blob/v1.63.0/utils/libwebp-wasm/build.sh) defaults libwebp source to `3757b8afeb54e305eaef18502812a9a88b7ed662`, permits emsdk latest and only says tested emcc 6.0.2. Exact compiler/build provenance for the shipped WASM is **unresolved and cannot be approved away** by this license decision; 6.0.2 is not a verified shipped compiler version. |

L05 exact platform set, each version **1.33.0**, is confirmed by the
[wrapper's optional-dependency pins](https://registry.npmjs.org/lightningcss/1.33.0)
and each exact registry entry: `lightningcss-android-arm64`,
`lightningcss-darwin-arm64`, `lightningcss-darwin-x64`,
`lightningcss-freebsd-x64`, `lightningcss-linux-arm-gnueabihf`,
`lightningcss-linux-arm64-gnu`, `lightningcss-linux-arm64-musl`,
`lightningcss-linux-x64-gnu`, `lightningcss-linux-x64-musl`,
`lightningcss-win32-arm64-msvc`, `lightningcss-win32-x64-msvc`.

L08 exact platform set, each prefixed `@typescript/typescript-` and at **7.0.2**,
is fixed by the [TypeScript release metadata](https://registry.npmjs.org/typescript/7.0.2):
`aix-ppc64`, `darwin-arm64`, `darwin-x64`, `freebsd-arm64`, `freebsd-x64`,
`linux-arm`, `linux-arm64`, `linux-loong64`, `linux-mips64el`, `linux-ppc64`,
`linux-riscv64`, `linux-s390x`, `linux-x64`, `netbsd-arm64`, `netbsd-x64`,
`openbsd-arm64`, `openbsd-x64`, `sunos-x64`, `win32-arm64`, `win32-x64`.
The supplemental Go grants name x/sync v0.21.0, x/sys v0.46.0,
x/term v0.44.0 and x/text v0.38.0. An all-platform license inventory does not
authorize non-Linux execution or assert platform compatibility.

### Notice fingerprints and evidence custody

These SHA-256 values identify actual retained archive legal texts. Upstream
source rechecks matched greenlet, typing-extensions, packaging, pathspec,
Lightning CSS, mypy, librt, TypeScript and WebP hashes. The Vite and Playwright
sidecar values identify the prior archive inspection, not newly acquired files.

| Text | SHA-256 |
|---|---|
| greenlet LICENSE / LICENSE.PSF | `769831d6e5dfaf2c20802faccff1fafb4c2025dd8f6253dfa47fcad59d4d0979` / `e5ff3c23c110e494cd7d736c10fd96d462457bafeca310840db6527298c7d46b` |
| typing-extensions LICENSE | `3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf` |
| packaging LICENSE / LICENSE.BSD | `cad1ef5bd340d73e074ba614d26f7deaca5c7940c3d8c34852e65c4909686c48` / `b70e7e9b742f1cc6f948b34c16aa39ffece94196364bc88ff0d2180f0028fac5` |
| pathspec LICENSE | `fab3dd6bdab226f1c08630b1dd917e11fcb4ec5e1e020e2c16f83a0a13863e85` |
| Lightning CSS wrapper and 11 platform LICENSE files | `5eba353fe5076ac3432177f8ab1cf75e3afcd0584251e37c3bfead5f447d040e` |
| mypy / librt LICENSE | `fdf1cd17f50e1305ed8cfd37467312d27a984648dba622cef70573b5512e4e1b` / `88f9e379c684580053c58e75e296ca2eb243b6edcc6e5357f247310e96eeef8a` |
| Vite LICENSE.md | `387dd7baa307083401a27c58c362c30832f5ba1dba84f10cc22c33401523f45c` |
| TypeScript NOTICE.txt | `f5c708b59114507b8b27b48181b6883d106bbca0c1634bbee45b5e344237b66b` |
| Playwright babelBundle.js.LICENSE / esmLoader.js.LICENSE | `6e396aded640f0bd2671d57442575ce8172aa1371b2dece6c5d4048f2f38f34c` / `3cec0c446526a449e4613b0defee0adb585f88f1d7fdba919421226d69be078e` |
| playwright-core utilsBundle.js.LICENSE / webp_codec.LICENSE | `2495f30be29620d54b58339821eda0ebabdfb6ee9b09455f7285a06fd46fb9f3` / `995c7ee35aceb7666829b7a501ca89c0864e12b493c1174b155774ab1e03d831` |

Inspectable local evidence remains in the ignored
`.superpowers/sdd/2026-09-19-agentmonitor-v1-m1-foundation/task-0b-report.md`
and `candidate-review/archive-review.json`, `supplemental-review.json`,
`bundled-advisory-findings.json`, `bundled-license-metadata.json` in the same
task directory. The complete task-0b amendment supersedes its earlier partial
archive findings. The packet corrects its missing WHATWG decision and refines
its blanket bundled-advisory blocker into the bounded dispositions above.
It does not recast the previous archive inspection as final graph admission.

## Owner decision block

One response may state `L01–L11 approve/reject; Q01 approve/reject;
S01 approve/reject; S02 approve/reject`, naming any exceptions explicitly.
No check is preselected and no previous direct-license approval answers these.

| Decision | Choice and exact scope |
|---|---|
| L01–L11 | Use the per-row Approve/Reject boxes above for the consolidated exact exceptional-license set, including BSD-2-Clause packaging, MIT Emscripten, complete TypeScript WHATWG attribution and all retained obligations. |
| Q01 | [ ] Approve [ ] Reject — CfT 153.0.8010.52 linux64 **quarantine review only**, using the ordering above; no admission, strong-provenance waiver, execution or redistribution authority. |
| S01 | [ ] Approve [ ] Reject — exact TypeScript/x/text input containment, expiry 2026-10-03T00:00:00Z or first fixed stable TypeScript carrier, whichever first; security review and verified enforcement required before use. |
| S02 | [ ] Approve [ ] Reject — exact Playwright/brace-expansion pattern containment, same fixed deadline or first fixed stable Playwright carrier, whichever first; security review and verified enforcement required before use. |

Owner decision/date: **Pending**. Security decision/date: **Pending**.
Approval of this packet's choices would still not constitute an FND-I01 pass.

## Remaining execution gates and impact

| Gate / boundary | Current status |
|---|---|
| Exceptional-license decisions and two security containments | Pending owner/security decision; enforcement implementation and verification Not Run. |
| Rejected r1243 / 153.0.8010.12 browser | Rejected; acquisition and execution prohibited. |
| CfT 153.0.8010.52 quarantine | Pending Q01; acquisition, member/license inventory and inspection Not Run. |
| Authenticated browser strong provenance; complete browser notices | Blocked; HEAD and source licensing are insufficient. |
| Exact Emscripten build provenance; remaining embedded/native inventory | Blocked/unresolved; not cleared by owner license approval. |
| Final Python/npm/tool/runtime graph, exact CPython provisioning and native provenance | Blocked pending all admission gates; no final manifests/locks or clean install pass. |
| SBOM and full notices generation/regeneration | Not Run; final graph and complete inventories required. |
| FND-VER-001, FND-ENV-001, FND-DEP-001..004 implementation completion | Blocked; runtime checks, clean frozen installs, strict typing, builds and behavioral TDD Not Run. |
| Amendment Red/Green/refactor | Not Applicable: documentation-only correction, no changed production behavior or tests. Future enforcement still requires meaningful TDD. |
| Browser compatibility / built UI, SQLite, HTTP, provider/live and hosted CI | Not Run; no product boundary is exercised or cleared by this packet. |
| FND-ENV-002 / real macOS | Blocked; no real macOS execution evidence. |

Only the existing documentation command, diff check and allowed-path scan
verify this documentation packet. They do not validate dependency execution.
No security control is implemented here. Privacy impact is limited to public
dependency metadata and legal evidence: no provider/default profile, credential,
prompt/response, arbitrary environment or application data is inspected or
changed. No new dependency, external resource, migration, API/configuration or
database change occurs. R-018 and Foundation's browser/native risks remain open.
The next step is the finite owner/security decision above, followed only by
the specifically authorized review work and remaining fail-closed gates.
