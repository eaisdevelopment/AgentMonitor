# M1 React declaration admission

- Record: `FND-I09-TYPES-001`, 2026-09-20.
- Scope: local V1-M1 development/typecheck only; no application runtime package.
- Owner approval: Pavlo Sidelov, 2026-09-20, explicitly approved the exact two direct packages below and their identified transitive package.
- Requirements: `NFR-API-002`, `NFR-TEST-002`, `NFR-LIC-001`; scenarios `FND-UI-001`, `FND-DEP-001..004`.
- Contract impact: none; `CTR-UI-001`, `CTR-FND-005/008` V1 semantics unchanged.

## Necessity and graph

The real strict `tsconfig.app.json` check failed with TS7016/TS7026 for React and React-DOM JSX declarations. Vite's transpilation and the previous `typecheck` command omitted that application project. Handwritten broad declarations would hide type errors; these upstream React-major-matched type packages are necessary to enforce the existing strict TypeScript requirement.

| Package | Exact selection | Scope and graph | License / source |
|---|---|---|---|
| `@types/react` | `19.3.0` | Direct dev-only; depends on `csstype ^3.2.2` | MIT; [npm registry package](https://www.npmjs.com/package/%40types/react), [DefinitelyTyped source](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/react) |
| `@types/react-dom` | `19.3.0` | Direct dev-only; peer `@types/react ^19.3.0`; no further declared dependency | MIT; [npm registry package](https://www.npmjs.com/package/%40types/react-dom), [DefinitelyTyped source](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/react-dom) |
| `csstype` | `3.2.3` | Transitive dev-only; no declared dependency | MIT; [npm registry package](https://www.npmjs.com/package/csstype), [upstream source](https://github.com/frenic/csstype) |

Registry metadata was checked for the exact versions, licenses, graph, integrity values, and published package sizes on 2026-09-20. OSV's package/version query returned no advisories for these three tuples at review time; that is not proof of future safety. The two direct packages are actively published by DefinitelyTyped; `csstype` is maintained separately. These are declaration/build inputs only, with no browser/runtime import or product telemetry path. Their published dependency graph adds no native binary. `csstype` lists repository publish/build/test scripts, but no preinstall/install/postinstall script in the reviewed registry metadata; installation uses `--ignore-scripts` regardless. The locked integrity hashes and actual installed license files must be checked after resolution.

Post-install check on 2026-09-20: exact manifest/lock/installed graph passed `AUTO-QUALITY` and `AUTO-BUILD`; all three installed `LICENSE` files were present and contained the MIT permission grant. `npm audit --prefix frontend --audit-level=low` exited 0 with `found 0 vulnerabilities`. This is a point-in-time npm registry check, not a full release vulnerability/provenance gate. No install scripts were run during admission.

Alternatives: removing strict app checking is rejected because it caused this defect; local handwritten declaration stubs are rejected because they would fake TypeScript coverage. Update policy: exact pins only, lockfile review on every update, no silent latest-tag change. Removal means replacing React or obtaining equivalent reviewed declarations. Release SBOM/notices and full vulnerability/provenance refresh remain Not Run for M1 and required before redistribution; existing lock-review findings are not cleared by this admission.
