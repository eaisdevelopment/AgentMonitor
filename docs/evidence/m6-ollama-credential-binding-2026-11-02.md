# M6 Ollama credential-binding domain evidence

Scope: M6-T004/T005/T010, M6-A01/A03/A09 and FR-ACC-001/003/004/006;
M02 additive internal `CTR-REG-011` v1.0.0. Existing account view
`CTR-REG-002` is unchanged. The pure policy models owner-asserted pending,
active and cleanup states, versioned rotation, disconnect and generation
fences. Binding identifiers have a closed random-handle format; application
code must generate them and persistence must enforce global uniqueness.

Red: the domain contract was initially absent. Review then found missing
pending-only disconnect, replay cleanup and identifier validation; their tests
failed before correction. Green: 30 focused pure binding, cloud timing and
balance tests passed on the integration branch. Ruff and documentation checks
passed in the implementation worktree. Constructed values were confined to
pure no-I/O tests; no real or fake provider credentials, profiles or accounts
were read or created by this domain work.

Not implemented: persistence and atomic constraints; serialized enrollment
and cleanup; the atomic observation-commit generation fence; owner keyring
entry; API/UI projection; actual Ollama authentication and provider comparison.
No migration, runtime dependency, existing API change or live deployment is
introduced by this domain contribution. Cleanup means the local item was
cleared, not that the provider key was revoked.
