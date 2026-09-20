# M2 local Swagger UI asset admission

- Record: `P01-ST-API-001-DEP-001`; reviewed 2026-09-20.
- Status: **Pending owner approval**. No package has been installed or added to a manifest or lock by this record.
- Scope: `ST-API-001`, `FR-IAM-006`, `CTR-API-003` V1. No public API contract change.

## Need and exact candidate

The M2 authenticated `/docs` must load without a CDN and must support bearer Try-it-out. FastAPI's default Swagger page uses external assets; the current project lock contains no local Swagger distribution. The upstream [installation guide](https://github.com/swagger-api/swagger-ui/blob/main/docs/usage/installation.md) describes `swagger-ui-dist` as the server-side static-asset distribution. The proposed exact frontend build dependency is `swagger-ui-dist@5.33.0` (Apache-2.0), with its sole declared dependency `@scarf/scarf@1.4.0` (Apache-2.0). Registry metadata reports 11,920,429 unpacked bytes and SHA-512 integrity `sha512-wpdK+m6BU5yj6pmUdMskZVTSWYG4DLglAx3sIhylloY37i8O37IrH+YEpqdXNfpaTGxILRBFzUqLF2jKqbfI7A==` for the direct package. The released tarball inventory includes `LICENSE`, `NOTICE`, and bundled JavaScript `.LICENSE.txt` files; the build must preserve applicable notices with shipped assets.

`@scarf/scarf` has a `postinstall` analytics script. The [package's registry instructions](https://www.npmjs.com/package/swagger-ui-dist) say to disable it with `scarfSettings.enabled=false` in `package.json` or `SCARF_ANALYTICS=false`. Admission is conditional on codifying that opt-out before install and verifying the resolved lock/installation; no analytics transmission is authorized. Only the required version-pinned CSS, bundle, preset, and notices should be copied into the built local shell. No remote CDN or runtime npm resolver is permitted.

## License, maintenance, security, and verification

Both declared packages identify as Apache-2.0 in exact-version npm metadata. `swagger-ui-dist` is maintained in the [upstream Swagger UI repository](https://github.com/swagger-api/swagger-ui); its [security policy](https://github.com/swagger-api/swagger-ui/security) supports 5.x. The exact tarball was inspected with `npm pack swagger-ui-dist@5.33.0 --dry-run --json --ignore-scripts`: 32 files, including the top-level license/notice and bundled notices. This is a package inventory, not a release-artifact verification. The OSV exact-version API queries for both npm packages returned no listed advisories on 2026-09-20; this does not prove absence of vulnerabilities. The installed lock, transitive graph, copied-file hashes/notices, disabled analytics, and real browser behavior remain **Not Run**.

If the owner approves the exact two-package graph, the P01 writer may pin and lock it, disable Scarf analytics, build only local assets, regenerate license notices/SBOM, run the dependency/security and production-build gates, and verify `/docs` plus bearer Try-it-out in a real browser. Any extra dependency, changed version/license/advisory, install hook, or external request returns to review. No package is admitted merely by this pending record.
