# 🔐 Privacy

🔒 HA Idleon is a read-only Home Assistant custom integration.

The current MVP does not ask for Idleon credentials, Steam credentials, browser
cookies, session tokens, or private API tokens. Users should not paste private
session tokens into this integration.

The intended future data source is authenticated Idleon cloud access. When that
is implemented, Home Assistant will need to store the provider type, account
identifier, and refresh token or equivalent auth material required to fetch
read-only cloud save data.

## 📥 Data Processed

The current MVP reads JSON from the configured source:

- A local file path, or
- A remote URL.

The planned authenticated source will fetch the user's cloud save data from
Idleon's backing services after the user signs in through a supported provider.

Raw Idleon account data may contain sensitive game/account details, including
character names, progress, inventory-derived state, account-level totals, and
other exported fields. Keep source JSON files private.

## 💾 Data Stored

Home Assistant stores the integration configuration in its config entry store.
Depending on the selected source, this can include:

- The local file path.
- The remote URL.
- The scan interval.
- Future authenticated-source provider and token metadata.

The integration does not intentionally store raw account JSON.

## 🩺 Diagnostics

Diagnostics redact:

- Local file paths.
- Remote URL query strings and fragments.
- Raw account JSON.
- Auth/session-like fields.

Review diagnostics before sharing them publicly.

## 🌐 Network Access

For `remote_url`, Home Assistant fetches the configured URL at the configured
scan interval. For `local_file`, no network request is made by this integration.

For the planned authenticated source, Home Assistant will contact identity
provider and Idleon/Firebase endpoints at setup and refresh time.
