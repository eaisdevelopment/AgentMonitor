# M2 local ReDoc asset admission

- Record: `P01-ST-API-001-DEP-002`; reviewed 2026-09-20.
- Status: **Pending owner approval**. No ReDoc asset has been added to this repository or runtime.
- Scope: authenticated local `/redoc` in `ST-API-001`, `CTR-API-003` V1; no resource-route or public DTO change.

## Necessity and exact artifact

The approved P01 M2 plan requires `/redoc` to work with local assets, not FastAPI's CDN default. The upstream [ReDoc documentation](https://www.npmjs.com/package/redoc) supports a locally served standalone browser bundle. Candidate: the exact `redoc@2.5.4` npm tarball, integrity `sha512-M6jWhG1qoBnH6TFmzJnstyCZ87HmOY/UzDm78mHiYihEdlV/YcS9ogOo1NlElnJMeLsyxHFe2yFc4sNjHTrABQ==`, SHA-256 `44922df4d0eb45c1b066c09ec251e6bd9bd7ded16bc69e87613337b9d911a56e`. Admit only `bundles/redoc.standalone.js` (SHA-256 `dcaf76612bc4a3fbcc923a8966dee2f6146a5f32e5ce1b6f02dd60cbbf89500b`), top-level `LICENSE`, and `bundles/redoc.standalone.js.LICENSE.txt`, copied byte-for-byte by a reproducible, hash-checking build/vendor operation. No ReDoc npm package, its 114-package resolved runtime graph, or install/prepare scripts would be installed in the project. The reviewed tarball was fetched with `npm pack redoc@2.5.4 --ignore-scripts` in an isolated temporary directory; its declared `prepare` hook was not run.

## License, maintenance, security, and remaining gates

The exact npm metadata and tarball declare MIT for ReDoc, with its license file included. The standalone bundle's notice lists bundled MIT components and DOMPurify under the Apache-2.0/MPL-2.0 choice; preserve that notice alongside the asset. The upstream [repository](https://github.com/Redocly/redoc) has maintained 2.5.x releases. An exact-version OSV query for `redoc@2.5.4` returned no listed advisory on 2026-09-20. A separately resolved temporary 114-package lock returned zero npm-audit findings, but that graph is **not proposed for installation** and neither lookup guarantees safety. The actual vendored-file hashes, complete distribution notice, CSP, authenticated real-browser rendering, and network-no-external-request test remain **Not Run**.

If approved, the P01 writer may add only the pinned, hash-checked standalone asset and required notices through a codified routine, then test `/redoc` over real loopback HTTP and a real browser. No CDN, remote font/analytics request, npm install, changed artifact version, or extra license is authorized. Any such change returns to dependency review. This pending review alone does not approve an asset or pass Story 4.
