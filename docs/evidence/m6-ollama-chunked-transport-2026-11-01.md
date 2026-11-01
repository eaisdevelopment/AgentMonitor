# M6 local Ollama chunked transport — candidate evidence

Requirements: M6-T004, M6-A08/A09; approved local Ollama implementation plan.
Owner: M03 Ollama adapter; existing local-catalog v1 contract unchanged.

The previous HTTP reader rejected chunked transfer encoding, which can occur
when a provider response grows. The candidate decodes bounded chunked bodies,
retaining the deadline and response size limits and rejecting ambiguous
framing. No provider profile, model, dependency, migration, or secret changes.

Red: the real-provider transport test failed with ImportError for the missing
decoder before implementation. Green: 23 Ollama adapter tests passed,
including a chunked HTTP response from the real Ollama documentation server.
`AUTO-M6-LOCAL-ADMIT` passed with source/test digest
`6fe6fd232181d2ff6cbbd2d368fa649c6b41aec31e6ab125b8744cdb9efce89f`;
its real local API and built-browser checks include automatic refresh.

The documentation response verifies HTTP framing, not a populated Ollama
catalog JSON response. Model-present and natural source failure/recovery tests
remain unexecuted. This is a candidate, not the currently running dashboard or
full M6 completion. See the earlier local preview evidence for rollout and
security boundaries. No new dependency or license impact was identified.
