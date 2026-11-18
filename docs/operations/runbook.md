# Operating AgentMonitor

This guide covers an installed AgentMonitor service. The repository is a source
distribution; it does not provide a general-purpose packaged installer.

## Open the dashboard

The usual local address is <http://127.0.0.1:43110/>. Use the address selected
by your operator if it differs. A trusted-LAN deployment has a separate
dashboard sign-in on its LAN address. Keep an HTTP-only deployment on a trusted
network; it is not an Internet-facing hosting configuration.

Closing the browser leaves the service and scheduled collection running.
For an installation using the supplied user-service name, check its state with:

```bash
systemctl --user is-active agentmonitor-dashboard.service
```

The Overview shows subscription capacity and API usage/spend separately.
Organization and provider filters help separate unrelated accounts. Open an
account row for its reporting period, history, connection and activity details.
Names and dashboard organizations are managed through the admin forms; they do
not by themselves verify a provider identity or billing organization.

## Connect Claude or Codex subscriptions

1. Open **Accounts**, create the account record and assign its organization.
2. Open the record, confirm the intended account email and choose
   **Connect Claude** or **Connect Codex**.
3. Complete the official provider sign-in in the browser window that opens.
4. Return to the account page and check the connection result. A verified
   connection enables monitoring; quotas appear after successful collection.

Use **Cancel connection** to cancel an active attempt. A wrong-account result
requires choosing the correct account and starting a deliberate new attempt.
Do not rename a record to conceal an identity mismatch.

AgentMonitor uses separate managed profiles for these connections. It does not
log out or rewrite your default provider profile. CLI adapters admit specific
versions and schemas; a version mismatch is explicit and is not treated as a
compatible reading.

## Connect Anthropic or OpenAI API billing

API billing is separate from a Claude or ChatGPT subscription. It requires
administrative access to the provider organization whose reports you want.

1. Open an existing account's **API billing connection**, or choose
   **Add API billing account** in Accounts for a billing-only account.
2. Choose **Add API billing connection**. Leave the optional **Provider billing
   scope** blank if unknown; a dashboard label is not proof of provider scope.
3. Select the intended organization at the provider's administrative key page:
   [Anthropic Admin keys](https://platform.claude.com/settings/admin-keys) or
   [OpenAI Admin keys](https://platform.openai.com/settings/organization/admin-keys).
   Create or use a key authorized for that organization's reports.
4. In AgentMonitor, expand **Set up or replace local key** and choose
   **Copy setup command**. Run that exact command on the displayed AgentMonitor
   host, as the user running its service. Paste the key only at the hidden
   terminal prompt. The command already selects the connection.
5. Choose **Refresh billing status**, then **Check connection**. Wait for the
   result. If an outcome is uncertain, use **Refresh check status** or
   **Resolve check outcome** as offered.
6. After verification, choose **Enable API monitoring**. Check the source scope,
   reporting period and observation time when the first report arrives.

A key stored locally is not yet verified provider access. A successful empty
report is not proof that you selected the intended billing organization.

For rotation, repeat **Set up or replace local key**, check the new connection,
then revoke the retired key at the provider when appropriate. AgentMonitor does
not revoke provider keys. Keys stay in the protected AgentMonitor `.env`; never
put them in browser fields, command arguments, screenshots or issue reports.

## Connect Ollama cloud

Create the Ollama account and organization in Accounts, then open the account.
Expand **Set up or replace the local key** and copy its setup command. Run it on
the AgentMonitor host, select the displayed account and **connect/rotate (1)**,
then enter the key at the hidden prompt. Return to **Check connection** and
enable monitoring after successful verification.

Existing working cloud connections are reused for their supported balance and
usage reports. They do not need duplicate account records. **Usage scope**
selects Self or Team; team access depends on provider permissions. A missing
team report never reuses self usage.

## Read money and history correctly

- **Reported spend** retains its currency, source scope and covered period.
  It is not an invoice. Usage counts are not converted into money locally.
- Missing funds or limits are shown as unavailable, not zero or unlimited.
- Anthropic and OpenAI use supported 7/30 completed UTC-day reports. Ollama
  retains the coverage its source actually reports.
- Compatible totals count known shared billing pools once. Incompatible
  currencies, periods or cost bases are not silently combined.
- History and charts belong to a selected report. An observed daily rate needs
  qualifying monetary history. An exhaustion estimate additionally needs
  compatible funds; otherwise the missing input is explained.
- **Refresh view** rereads stored data. **Collect now** or **Collect usage**
  requests a new reading when eligible. Repeated clicks do not bypass cooldowns.

## Disconnect, archive and recover

For API billing, expand **Disconnect or clean up local credentials** and run
the displayed command on the service host. Disconnect retires local access and
stops API monitoring while retaining history. **Cleanup required** remains
visible until retired local entries are removed. Neither action revokes a
provider key or changes a subscription profile.

To restore an archived API account, use **Edit account → Restore account**, then
**Reconnect API billing**. Set up its local key, check access and enable
monitoring. Retained history is not an active credential.

## Investigate stale or unavailable data

Check the account's connection outcome, last successful observation, selected
period and next retry time. **Monitoring on** describes configuration; it does
not prove a fresh reading. Collection/History lists collection outcomes, while
Operations provides service diagnostics. Unknown process-account links remain
unknown until supported evidence identifies them.

Use only the installed, revision-compatible backup, migration and recovery
procedures. Do not overwrite a live database with an older copy, delete recovery
journals, or edit provider profiles to clear a displayed error. Deployment
helpers that select a fixed workstation are not portable installation commands.

Report problems with the revision, provider/version, time, displayed error code
and sanitized reproduction. Keep keys, passwords, provider files, raw responses
and complete databases out of reports; see [Security](../../SECURITY.md).
