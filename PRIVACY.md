# Privacy

HA Idleon is a read-only Home Assistant custom integration.

v1 does not ask for Idleon credentials, Steam credentials, browser cookies,
session tokens, or private API tokens. Users should not paste private session
tokens into this integration.

## Data Processed

The integration reads JSON from the configured source:

- A local file path, or
- A remote URL.

Raw Idleon account data may contain sensitive game/account details, including
character names, progress, inventory-derived state, account-level totals, and
other exported fields. Keep source JSON files private.

## Data Stored

Home Assistant stores the integration configuration in its config entry store.
Depending on the selected source, this can include:

- The local file path.
- The remote URL.
- The scan interval.

The integration does not intentionally store raw account JSON.

## Diagnostics

Diagnostics redact:

- Local file paths.
- Remote URL query strings and fragments.
- Raw account JSON.
- Future auth/session-like fields.

Review diagnostics before sharing them publicly.

## Network Access

For `remote_url`, Home Assistant fetches the configured URL at the configured
scan interval. For `local_file`, no network request is made by this integration.

