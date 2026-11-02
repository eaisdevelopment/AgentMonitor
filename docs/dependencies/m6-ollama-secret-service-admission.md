# M6 Ollama Secret Service system-dependency admission

**Historical; superseded:** the owner selected the protected managed `.env`
instead of Secret Service on 2 November 2026. This dependency is not required
for the current M6 cloud credential architecture.

- Record: `M6-KEYRING-DEP-001`, reviewed 2 November 2026.
- Status: **admitted for Ubuntu 24.04 amd64 local implementation only**.
  This does not admit bundled binaries, another distribution, macOS, public
  redistribution, or completed runtime behavior.
- Authority: the owner-approved
  [M6 Ollama cloud plan](../plans/integration/m6-ollama-cloud-implementation-change.md)
  and root `AGENTS.md` exception explicitly approve the named Secret
  Service/libsecret/`secret-tool` architecture and its GPL/LGPL nature. No
  repeat license-family approval is required.
- Traceability: `M6-T016`, `M6-A09`, `NFR-LIC-001`, `NFR-SEC-001`,
  `FR-SAFE-001/002`, `FR-COL-007`.
- Owner: M03 Ollama adapter, with Security and M6 integration review.
- Contract/schema impact: none. This record admits an external system
  prerequisite; it does not implement a credential contract or access a key.

## Decision and necessity

AgentMonitor may invoke the fixed Ubuntu path `/usr/bin/secret-tool` as a
separate process to store, look up, rotate and clear one owner-managed Ollama
API-key item per connection. GNOME Keyring supplies the user-session Secret
Service. No Python or frontend package is added, and AgentMonitor neither
links to nor copies libsecret or GNOME Keyring.

This satisfies the approved requirement for persistent per-account local
secret storage without sending keys through the LAN dashboard, command
arguments, `.env`, SQLite, logs or provider profiles. Standard-library code
cannot implement Secret Service safely, and an in-house key store is rejected.
The exact subprocess and lifecycle controls remain implementation work under
the approved cloud plan.

## Installed origin and runtime graph

Read-only inspection was performed on Ubuntu 24.04.5 LTS (`amd64`). No package
was installed or changed. The installed and current APT candidate versions are:

| Ubuntu package | Version | Repository | Role |
|---|---:|---|---|
| `libsecret-tools` | `0.21.4-1build3` | Noble `universe` | owns `/usr/bin/secret-tool` |
| `libsecret-1-0` | `0.21.4-1build3` | Noble `main` | Secret Service client library |
| `libsecret-common` | `0.21.4-1build3` | Noble `main` | libsecret data files |
| `gnome-keyring` | `46.1-2ubuntu0.2` | Noble Updates `main` | owns the daemon, D-Bus activation and user unit |

The package maintainer is Ubuntu Developers; the source packages are Ubuntu
builds of GNOME `libsecret` and `gnome-keyring`. The installed payloads match
their local `dpkg` MD5 manifests. That is a local drift check, not modern
cryptographic proof of the originally downloaded `.deb`. APT repository
metadata reports the origins above. Canonical package references are
[`libsecret-tools`](https://packages.ubuntu.com/noble/libsecret-tools) and
[`gnome-keyring`](https://packages.ubuntu.com/noble-updates/gnome-keyring).

`ldd` resolution of the two installed ELF executables produced this installed
library-package union: `libblkid1`, `libc6`, `libcap2`, `libffi8`,
`libgck-1-0`, `libgcr-base-3-1`, `libgcrypt20`, `libglib2.0-0t64`,
`libgpg-error0`, `liblz4-1`, `liblzma5`, `libmount1`, `libp11-kit0`,
`libpcre2-8-0`, `libsecret-1-0`, `libselinux1`, `libsystemd0`, `libzstd1`
and `zlib1g`. `libsecret-common` is a non-ELF package dependency. This is the
resolved ELF closure on this machine, not a runtime trace: `dlopen`, D-Bus,
PKCS#11 and unlock/prompt helpers can add processes or libraries.

The broader recursive APT candidate inventory contains 150 installed packages
because GNOME Keyring depends on D-Bus, GCR, p11-kit and `pinentry-gnome3`,
which pull GTK, fonts and icon data. It can overcount alternatives and code not
loaded on an unlocked lookup. It remains the conservative package-level review
surface in
[`m6-keyring-system-dependency-inventory.json`](../evidence/m6-keyring-system-dependency-inventory.json).

## License review

The exact upstream source headers identify
[`secret-tool`](https://gitlab.gnome.org/GNOME/libsecret/-/blob/0.21.4/tool/secret-tool.c)
as `LGPL-2.1-or-later` and
[`gnome-keyring-daemon`](https://gitlab.gnome.org/GNOME/gnome-keyring/-/blob/46.1/daemon/gkd-main.c)
as `GPL-2.0-or-later`.
Installed Ubuntu copyright manifests also contain LGPL, GPL, MPL, Apache,
BSD/MIT/X11 and other file-specific notices across the source-package closure.
Those manifests are a conservative source-package superset, not proof that
every listed term applies to every installed binary.

Forty-one packages in the broad inventory have legacy copyright files without
machine-readable `License:` labels. All 41 were manually reviewed and grouped
into 27 source-package manifests in the inventory, with the exact installed
copyright-file SHA-256 and a conservative license-family summary. The gap was
missing machine-readable structure, not missing copyright text. The manual
summary is not a per-file SPDX conclusion; GCC, glibc, Kerberos and X.Org in
particular contain numerous file-specific terms.

Engineering disposition: local execution of OS-supplied GPL/LGPL programs and
libraries is within the explicitly owner-approved architecture. AgentMonitor
will not bundle, modify, statically link, or redistribute these binaries. A
future package that includes them requires a new distribution-specific legal,
source-offer, notice and SBOM review. This is engineering review, not legal
advice.

## Security and maintenance

- `secret-tool` and GNOME Keyring are local D-Bus components; this dependency
  adds no AgentMonitor analytics or hosted service. No packet-capture claim was
  made. The separately planned Ollama HTTPS request is outside this dependency.
- Secret Service is a same-user boundary, not per-application isolation. Other
  processes running as the service user may access an unlocked collection.
  Item attributes are not secret, so bindings must remain random and contain
  no email, account label or key-derived value.
- `secret-tool lookup` returns the secret on stdout and may unlock an item. The
  runtime therefore necessarily holds key bytes in a bounded pipe and process
  memory; reliable Python zeroization is not promised. No shell, environment
  value, argument, log, traceback or diagnostic may contain the key.
- The installed manual has no noninteractive lookup flag. A locked collection
  may prompt or block. The scheduler must use a deadline, never provide prompt
  input, and fail closed as unavailable until real service-context behavior is
  verified.
- `secret-tool clear` removes all unlocked matches. All four approved random
  attributes must be supplied, uniqueness must be enforced before use, and
  failed cleanup must remain visible.
- The fixed executable path, regular-file ownership/mode and package version
  must be checked before use. OS package updates are preferred over vendoring;
  version/license/behavior changes trigger re-review.
- Upstream is active: official tags observed on the review date include
  libsecret `0.21.8.2` and GNOME Keyring `51.1`, both from September 2026.
  Ubuntu intentionally carries older LTS versions and patched GNOME Keyring in
  Noble Updates.
- Neither reviewed upstream tag contains a repository-root `SECURITY.md`;
  vulnerability handling therefore relies on GNOME's reporting channel and
  Ubuntu CVE/USN maintenance rather than a component-specific support promise.
- `pro security-status --format json` at `2026-11-02T14:37:45Z` reported no
  pending update intersecting the 150-package inventory. This is a point-in-time
  package-status result, not proof of no vulnerability. `libsecret-tools` is in
  Universe and this host is not attached to Ubuntu Pro, so its long-term
  security coverage is weaker than Main and must be reviewed continuously.

## Alternatives and removal

- Plaintext files, `.env`, SQLite, browser entry and command arguments violate
  the approved secret boundary.
- The default Ollama profile is protected and is not a credential store for
  this integration.
- `systemd-creds` complicates per-account CRUD and rotation and normally binds
  credentials to unit configuration/restart.
- A Python keyring wrapper adds packages and backend ambiguity; direct D-Bus or
  a custom encrypted store increases security-critical code; an external
  broker adds a service and data-flow boundary. None improves this bounded
  Ubuntu-local scope enough to replace the approved OS tool.

Removal disables the Ollama cloud binding and leaves provider-side revocation
to the owner. Managed items require the approved cleanup flow; removing an OS
package is never an AgentMonitor runtime action.

## Remaining gates

The dependency review is sufficient to begin Ubuntu-local implementation, but
the capability is not operationally admitted. The following remain **Not Run**
or **Blocked**:

- owner-controlled enrollment and unattended lookup against a dedicated real
  item, including locked/unlocked outcomes;
- user-service behavior after logout and reboot;
- dynamic prompt/PKCS#11 closure and resource measurement;
- secret-leak scanning of the implemented subprocess, errors and diagnostics;
- an executable OS-prerequisite/version check and external-system SBOM entry;
- public redistribution/notices/source obligations, other Linux releases and
  macOS.

No keyring item, provider key, provider profile, running dashboard service or
provider endpoint was accessed during this review.
