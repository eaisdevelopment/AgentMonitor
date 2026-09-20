# V1-M1 hosted CI execution environment review

- Scope: development/test-only GitLab.com hosted Linux jobs for `FND-CI-001/002` and `AC-TEST-001/002/004/006`.
- Decision date: 2026-09-20. Owner instruction: finish the approved M1 milestone using the supplied private GitLab project and development token.
- No application runtime dependency, package manifest, product artifact, provider credential, or distribution license is changed by this runner selection.

## Exact inputs and necessity

| Input | Exact identity | Reason and verified boundary |
|---|---|---|
| Playwright test image | `mcr.microsoft.com/playwright@sha256:eff16c30e6f3f4af0a03fa4b706120d5e9b0891c344a27d64559aff5900a4a27` (`v1.63.0-noble`, Linux/amd64) | Official Playwright image supplies the real matching Chromium engine and browser OS libraries. Local Docker inspection found Python 3.12.3 and the `pwuser` account; Node/uv are installed separately. [Official image guidance](https://playwright.dev/docs/docker). |
| Node.js | `22.23.2` Linux x64 tarball; SHA-256 `d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307` | Matches `.node-version`; bundled npm is 10.9.8. Digest was checked against [official release checksums](https://nodejs.org/dist/v22.23.2/SHASUMS256.txt) and a downloaded archive. Node is MIT with bundled notices; already used in the admitted local M1 toolchain. |
| uv | `0.11.16` Linux x86-64 GNU tarball; SHA-256 `74947fe2c03315cf07e82ab3acc703eddef01aba4d5232a98e4c6825ec116131` | Matches the admitted local resolver version. Digest was checked against the [upstream release asset](https://github.com/astral-sh/uv/releases/tag/0.11.16) and a downloaded archive. uv is MIT/Apache-2.0. |
| Python/npm/Playwright package | Python 3.12.3 from pinned image; npm 10.9.8 from Node archive; `@playwright/test==1.63.0` from committed npm lock | The package/license graph is the already reviewed M1 graph, installed from committed locks without lifecycle scripts. No second browser-driver package is added. |

The image is CI infrastructure, not shipped with AgentMonitor. Its Ubuntu/browser native components have mixed upstream notices; full binary SBOM/notices review remains a release-only Not Run item. The known Playwright-bundled Chromium vulnerability is confined to the isolated, development-only browser job that visits the loopback service; it is not a product binary or a provider-data browser. The owner explicitly allowed a test-browser candidate with a documented follow-up rather than blocking M1 on that browser's vulnerability.

## Containment and alternatives

- Run as image user `pwuser` (`1001:1001`), without privileged mode, Docker-in-Docker, caches, or uploaded artifacts. Jobs receive no `.env`, provider profile, owner evidence, or personal access token. The project remains private and `main` protected.
- Download exact Node/uv archives over HTTPS, verify pinned SHA-256 before extraction, then run `uv lock --check`, frozen no-build `uv sync`, and `npm ci --ignore-scripts`. `tools/ci/bootstrap.py` fails closed on wrong platform/version, existing `.env`, digest/layout mismatch, or installation failure.
- Use the matching real Playwright Chromium from the image in hosted CI; keep real installed Chrome for local workstation testing. Evidence records the browser actually executed.
- The default GitLab runner image lacks the approved toolchain; a mutable `latest` tag, unverified install-pipe script, silently changed local version policy, and fake/browserless tests were rejected.
- Maintenance: revisit the pinned image/digests and browser advisories before public release or an M1 CI image upgrade. A new digest requires a fresh clean-container and hosted run.
