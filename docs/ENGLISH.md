# Naše energie — English quick start

Read-only outbound solar monitoring for the Naše energie portal. Home Assistant
2026.9+ is required. It never controls inverters, batteries or household devices.
It sends selected measurements every 60 seconds through verified HTTPS; no
Home Assistant access token or inbound port is required.

After the maintainer publishes the repository and a release, add
`https://github.com/kullalukas-png/nase-energie-ha` in **HACS → Custom repositories**,
category **Integration**. Download a released version and restart HA.
For beta releases, enable pre-release versions in HACS.

Create a ten-minute one-use code for your own installation in the portal's
connection settings. Add **Naše energie** under **Settings → Devices & services**.
Confirm sensors, grid/battery polarity and consent. GoodWe sensors are suggested
from the registry; other manufacturers require selecting the available sensors.
Never sum duplicate household/grid measurements or both a PV total and its parts.

PV strings are optional separate channels, not additional generation. The portal
must support their storage (1.3.0+ with its optional string table enabled).
Missing readings are null, not fictitious zero. Internet outages retry with
bounded backoff and a 120-sample in-memory queue, cleared on restart/reload.

For updates, back up HA, install through HACS and restart. **Do not remove or
re-pair the integration.** Existing selections, keys, string IDs and sending
preferences remain in HA's config entries, outside the integration code folder.
New fields are not automatically opted into.

Revoked keys trigger HA's reauthentication flow. Use a fresh code for the same
installation; only the key is replaced. A different installation is rejected;
revoke the unused key created for that other installation in the portal.

This is a beta until the live HA/portal verification checklist is completed.
MIT license. See [security guidance](../SECURITY.md) and [release notes](../CHANGELOG.md).
