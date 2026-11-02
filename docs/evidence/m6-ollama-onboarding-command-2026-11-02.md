# Ollama local setup command candidate

The deployed Ollama account panel told the owner to use a local setup command
without providing it. It also did not refresh a `not_configured` status after
local enrollment. The candidate displays a copyable, non-secret command that
selects the active systemd service's executable and release directory, and
refreshes status when the user returns and periodically while setup is pending.
The API key is entered only in the existing local operator's hidden terminal
prompt; it is never entered into the browser.

On the real deployed service, the exact command extracted from the candidate UI
was invoked with `--help`; it reached the installed operator and exited 0
without prompting for a key. The operator also resolved the service-selected
`.env` path and its non-secret metadata as ready. Frontend typecheck and
production build passed. No credentials were read and no provider or live
account data were created or changed.

The real signed-in account/browser red-green test, interactive enrollment,
first authenticated balance probe and scheduled polling remain Not Run. No
constructed UI or API account data was used. This is a candidate change,
not a claim of verified onboarding or full M6 acceptance. It affects M6-A01,
M6-A03 and the P02 account presentation; no API, schema, provider contract,
dependency or migration changes are introduced.

Follow-up: The command now uses the fixed systemctl and sed executables, and the exact displayed command reached the deployed operator's help successfully without accessing credentials. Account status is bound to the selected account, and obsolete refreshes are aborted and fenced. Frontend typecheck and build passed. A real signed-in account navigation and red/green browser check remain Not Run; no account or provider data was fabricated.
