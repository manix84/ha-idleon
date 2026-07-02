# 📰 What's New

## 🚀 0.8.0

- Minor release placeholder. Update before release.

## 🚀 0.7.0

- Minor release placeholder. Update before release.

## 🚀 0.6.4

- Patch release placeholder. Update before release.

## 🚀 0.6.3

- Patch release placeholder. Update before release.

## 🚀 0.6.2

- Patch release placeholder. Update before release.

## 🚀 0.6.1

- Patch release placeholder. Update before release.

## 🚀 0.6.0

- Minor release placeholder. Update before release.

## 🚀 0.5.0

- Split `idleon_cloud` login provider selection onto its own setup page.
- Improved Google authorization instructions with a clearer login link and
  prominent device code.

## 🚀 0.4.0

- Added Google device-code authorization for `idleon_cloud`, so Google-based
  Idleon accounts can be linked without pasting session tokens.

## 🚀 0.3.0

- Fixed indexed character device names so `Character 1 - Manix84` is displayed
  as `Idleon Character 1 - Manix84` instead of repeating the character prefix.

## 🚀 0.2.0

- Promoted the integration version for the first authenticated cloud-source
  setup flow.
- Added a helper script for installing local Git hooks so automatic version
  bumps are not silently skipped.

## 🚀 0.1.18

- Added the first authenticated `idleon_cloud` data source using Idleon
  email/password sign-in, stored refresh-token polling, and Firebase cloud-save
  reads.
- Documented the authenticated Idleon cloud data source and clarified that
  local/remote JSON sources are transitional development paths.
- Changed the account last-updated sensor to prefer the parsed source/export
  timestamp when available.
- Added duplicate-source protection when changing data sources through options.
- Added the parsed source/export timestamp to diagnostics.
- Added newly discovered character entities after successful data refreshes.
- Cleaned inventory carry capacity attributes by hiding placeholder categories
  and showing material capacity with a readable label.
- Improved HA share deployment tooling for local Home Assistant testing.

## 🚀 0.1.17

- Patch release placeholder. Update before release.

## 🚀 0.1.16

- Patch release placeholder. Update before release.

## 🚀 0.1.15

- Patch release placeholder. Update before release.

## 🚀 0.1.14

- Patch release placeholder. Update before release.

## 🚀 0.1.13

- Patch release placeholder. Update before release.

## 🚀 0.1.12

- Patch release placeholder. Update before release.

## 🚀 0.1.11

- Patch release placeholder. Update before release.

## 🚀 0.1.10

- Patch release placeholder. Update before release.

## 🚀 0.1.9

- Patch release placeholder. Update before release.

## 🚀 0.1.8

- Patch release placeholder. Update before release.

## 🚀 0.1.7

- Patch release placeholder. Update before release.

## 🚀 0.1.6

- Patch release placeholder. Update before release.

## 🚀 0.1.5

- Patch release placeholder. Update before release.

## 🚀 0.1.4

- Patch release placeholder. Update before release.

## 🚀 0.1.3

- Patch release placeholder. Update before release.

## 🚀 0.1.2

- Patch release placeholder. Update before release.

## 🚀 0.1.1

- Patch release placeholder. Update before release.

## 🚀 0.1.0

Initial experimental MVP.

- Added UI config flow for `local_file` and `remote_url` JSON sources.
- Added read-only account and character parsing.
- Added one account device and one device per character.
- Added account sensors for total level, character count, gems, and last
  updated time.
- Added character sensors for level, class, current map, current activity, and
  AFK hours.
- Added character binary sensors for inventory full and needs attention.
- Added diagnostics with source redaction.
- Added HACS custom repository metadata.

🔒 v1 does not ask for Idleon credentials and does not implement login, Steam
login, browser scraping, session/token scraping, write actions, or services.
