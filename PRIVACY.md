# 🔐 Privacy

🔒 HA Idleon is a read-only Home Assistant custom integration.

The `idleon_cloud` data source asks for Idleon email/password credentials or
uses Google device authorization during setup, exchanges the login result for
Firebase tokens, and does not store the password or Google ID token after a
successful token exchange. Users should not paste private session tokens into
this integration.

Home Assistant stores the provider type, account identifier, and refresh token
required to fetch read-only cloud save data.

## 📥 Data Processed

The integration reads data from the configured source:

- Idleon Cloud through Firebase-backed Idleon services.
- A local file path.
- A remote URL.

The authenticated source fetches the user's cloud save data from Idleon's
backing services after the user signs in through a supported provider.

Raw Idleon account data may contain sensitive game/account details, including
character names, progress, inventory-derived state, account-level totals, and
other exported fields. Keep source JSON files private.

## 💾 Data Stored

Home Assistant stores the integration configuration in its config entry store.
Depending on the selected source, this can include:

- The local file path.
- The remote URL.
- The scan interval.
- The authenticated-source provider.
- Redacted account identity metadata.
- A Firebase refresh token for continued polling.

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

For `idleon_cloud`, Home Assistant contacts Firebase identity and Idleon
Firebase data endpoints at setup and refresh time.
