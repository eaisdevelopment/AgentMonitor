# M2 local ReDoc asset admission

- Record: `P01-ST-API-001-DEP-002`; reviewed 2026-09-20.
- Status: **Owner approved for Story 4 on 2026-09-21; implemented locally with a narrow offline footer-logo exception.**
- Scope: authenticated local `/redoc` in `ST-API-001`, `CTR-API-003` V1; no resource-route or public DTO change.

## Necessity and exact artifact

The approved P01 M2 plan requires `/redoc` to work with local assets, not FastAPI's CDN default. The upstream [ReDoc documentation](https://www.npmjs.com/package/redoc) supports a locally served standalone browser bundle. Candidate: the exact `redoc@2.5.4` npm tarball, integrity `sha512-M6jWhG1qoBnH6TFmzJnstyCZ87HmOY/UzDm78mHiYihEdlV/YcS9ogOo1NlElnJMeLsyxHFe2yFc4sNjHTrABQ==`, SHA-256 `44922df4d0eb45c1b066c09ec251e6bd9bd7ded16bc69e87613337b9d911a56e`. Admit only `bundles/redoc.standalone.js` (SHA-256 `dcaf76612bc4a3fbcc923a8966dee2f6146a5f32e5ce1b6f02dd60cbbf89500b`), top-level `LICENSE`, and `bundles/redoc.standalone.js.LICENSE.txt`, copied byte-for-byte by a reproducible, hash-checking build/vendor operation. No ReDoc npm package, its 114-package resolved runtime graph, or install/prepare scripts would be installed in the project. The reviewed tarball was fetched with `npm pack redoc@2.5.4 --ignore-scripts` in an isolated temporary directory; its declared `prepare` hook was not run.

## License, maintenance, security, and remaining gates

The exact npm metadata and tarball declare MIT for ReDoc, with its license file included. The standalone bundle's notice lists bundled MIT components and DOMPurify under the Apache-2.0/MPL-2.0 choice; preserve that notice alongside the asset. The upstream [repository](https://github.com/Redocly/redoc) has maintained 2.5.x releases. An exact-version OSV query for `redoc@2.5.4` returned no listed advisory on 2026-09-20. A separately resolved temporary 114-package lock returned zero npm-audit findings, but that graph was **not installed** and neither lookup guarantees safety. Later asset-hash/notice, CSP, real-browser, and zero-external-attempt results are recorded below.

The exact tarball and original standalone bundle are verified before a single deterministic substitution: upstream's unconditional `https://cdn.redoc.ly/redoc/logo-mini.svg` footer reference (required to occur exactly once) becomes `/docs-assets/redoc/redoc-mark.svg`. The locally copied upstream SVG is pinned at SHA-256 `1dab4315f8de2177b2b2726b29e84a26314c69cd27d692228947c0058793d5a7`; the derived JS is pinned at `f6f01d44331204dfd1e0aef8c0caee9fe59d3edc7669447ec5d89bffd8f82110`. Original LICENSE and bundle notice are preserved and hash-checked. The write routine fetches only at vendoring time; `--check` and runtime are network-free. Real Chrome ReDoc rendering passed with zero attempted external requests. The root approved this narrow derived-bundle exception; no full ReDoc npm graph was installed. Hosted release publication remains Not Run.
