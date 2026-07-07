# 📰 What's New

## 🚀 0.31.0

- Add green stacks entity picture.

## 🚀 0.30.0

- Add highest character level entity picture.

## 🚀 0.29.0

- Add character count entity picture.

## 🚀 0.28.0

- Add shrine levels entity picture.

## 🚀 0.27.0

- Add companion pets entity picture.

## 🚀 0.26.0

- Treat Jade as a numeric sensor.

## 🚀 0.25.0

- Add Tome points account sensor.

## 🚀 0.24.0

- Fix Jade and pet crystal parsing.

## 🚀 0.23.5

- Add gem sensor entity picture.

## 🚀 0.23.4

- Add stat sensor entity pictures.

## 🚀 0.23.3

- Add class sensor entity pictures.

## 🚀 0.23.2

- Nest pouch assets by type.

## 🚀 0.23.1

- Reorganize bundled Idleon assets.

## 🚀 0.23.0

- Add character storage capacity sensors.

## 🚀 0.22.4

- Add transparent padding around bundled money coin icons so they render cleanly in Home Assistant entity rows.
- Cover the expected padded coin asset dimensions in metadata tests.

## 🚀 0.22.3

- Bundle Idleon coin tier PNGs with the integration and serve them from a local static path.
- Set account and character money entity pictures to the current coin tier image.

## 🚀 0.22.2

- Use Idleon large-number suffix formatting as the visible state for account and character money sensors.
- Preserve coin-tier money formatting as attributes for dashboards and inspection.

## 🚀 0.22.1

- Add generic Idleon suffix formatting attributes to formatted money sensors.
- Cover account and character money abbreviation attributes in entity tests.

## 🚀 0.22.0

- Add shared Idleon number and coin-tier money formatters that preserve exact raw values.
- Expose account and character money as formatted display sensors plus raw copper-string sensors.
- Keep large money parsing integer-safe and cover tier boundaries in tests.

## 🚀 0.21.0

- Add account sensors for requested World 4, World 5, World 6, and World 7 systems.
- Parse compact later-world summaries from known raw Idleon fields and clean-data aliases.
- Cover the new later-world entities and parser details in tests and documentation.

## 🚀 0.20.0

- Add account sensors for World 3 printer, refinery, atom collider, equinox, buildings, death note, worship, prayers, traps, salt lick, construction, armor smithy, and hat rack.
- Parse compact World 3 summaries from known raw Idleon fields and clean-data aliases.
- Cover the new World 3 entities and parser details in tests and documentation.

## 🚀 0.19.1

- Rename Killroy to World 2 Killroy and use rooms available as the sensor value.
- Fold achievement world details into Achievements completed instead of exposing a duplicate sensor.
- Enable Raw money and harden account money parsing for flexible exports.
- Compact whole-number float attributes before exposing them to Home Assistant.

## 🚀 0.19.0

- Add World 2 account sensors for cauldron, vials, bubbles, sigils, vote ballots, and Killroy.
- Parse raw alchemy and ballot fields into structured account attributes.
- Mark numeric sensors with measurement state class so Home Assistant can graph them.
- Keep Last Updated as a disabled diagnostic sensor.

## 🚀 0.18.0

- Add account sensors for World 1 anvil, bribes, stamps, and broader world summaries.
- Parse forge slots, bribe purchase status, and stamp level details from raw Idleon fields.
- Keep world-specific account details in structured attributes to avoid mass entity creation.

## 🚀 0.17.0

- Add grouped account sensors for pets, achievements by world, task levels, taskboard merits, and taskboard unlocks.
- Parse raw achievement/task fields with websiteData labels and progress percentages where available.
- Keep detailed account-wide data in attributes to avoid creating hundreds of entities.

## 🚀 0.16.0

- Add grouped account sensors for currencies, shrine levels, statue levels, colosseum scores, minigame scores, and progress totals.
- Parse known Idleon raw fields for account currencies, scores, shrines, statues, stamps, bubbles, refinery salts, printer totals, and storage candies.
- Keep detailed values as attributes to avoid creating dozens of noisy default entities.

## 🚀 0.15.0

- Add Total money to the account device.
- Add Money to each character device from parsed character details.
- Keep Raw money as a disabled compatibility sensor for new installs.

## 🚀 0.14.0

- Add an explicit account last_updated timestamp to diagnostics.
- Disable the Last updated account sensor by default.

## 🚀 0.13.0

- Add a top-level quick start and screenshots for HACS users.
- Replace stale data-source setup copy with provider-neutral login guidance.

## 🚀 0.12.6

- Treat indexed PTimeAway values as seconds so long AFK durations do not collapse to 0.5h.

## 🚀 0.12.5

- Parse compact account-wide summary details from Idleon data.
- Add account sensors for skill, money, slab, green stack, and achievement summaries.
- Add character total skill sensors and disabled-by-default primary stat sensors.

## 🚀 0.12.4

- Add stage-specific Steam and Apple login logging.
- Document debug logger configuration for experimental provider testing.
- Keep provider logs free of tokens and raw account data.

## 🚀 0.12.3

- Label Steam and Apple as experimental in the setup flow.
- Update README and auth docs to distinguish primary and experimental providers.

## 🚀 0.12.2

- Start Idleon Apple auth sessions from the config flow.
- Open Apple Sign In with Idleon handoff details and poll completion.
- Store Firebase refresh credentials after successful Apple authorization.

## 🚀 0.12.1

- Align Steam OpenID parameters with the IdleonToolbox login flow.
- Log Steam authorization failure details before returning auth_failed.

## 🚀 0.12.0

- Replace the Steam paste-back URL field with a Home Assistant external config-flow step.
- Add a Steam callback endpoint that resumes the config flow automatically.
- Exchange Steam OpenID data through Idleon custom-token auth before storing Firebase refresh credentials.

## 🚀 0.11.0

- Use the Idleon Firebase auth handler for Steam OpenID redirects.
- Update Steam setup instructions to copy the final returned browser URL.

## 🚀 0.10.1

- Run the release workflow when code is pushed to main.
- Create the v<version> tag before publishing the GitHub release.

## 🚀 0.10.0

- Add Steam OpenID callback exchange for Idleon cloud setup.
- Store only Firebase refresh credentials after Steam validation.

## 🚀 0.9.3

- Add packaged fallback labels for core item and inventory bag IDs used by tests.
- Cover parser behavior when ignored websiteData files are unavailable.

## 🚀 0.9.2

- Generate WHATSNEW entries from commit subjects or body bullets.
- Install the version bump hook at commit-msg time.

## 🚀 0.9.1

- Renamed the Home Assistant and HACS display name to `Legends of Idleon`.
- Kept the integration domain unchanged as `idleon`, so existing config entries
  and entities continue to use the same technical integration ID.

## 🚀 0.9.0

- Added character summary sensors for inventory slots used, inventory slots
  free, highest skill, and equipped item count.
- Added compact character attributes for primary stats, skill levels, highest
  skill, equipped items, equipped tools, equipped food, and attack loadout.
- Expanded parser coverage for indexed Idleon exports so entities can consume
  normalized model details instead of raw JSON paths.

## 🚀 0.8.2

- Added a GitHub release workflow that builds and publishes a HACS-compatible
  release zip.
- Added release archive validation to ensure the zip contains the
  `custom_components/idleon` layout, HACS metadata, README, LICENSE, and brand
  icon assets.
- Added a Release status badge to the README.

## 🚀 0.8.1

- Switched the Home Assistant/HACS source icon to the compact official Idleon
  vial icon asset.
- Updated metadata tests to track the current official source icon.

## 🚀 0.8.0

- Changed the default refresh interval to five minutes.
- Kept the refresh cadence aligned with Home Assistant's minimum polling
  interval while avoiding excessive cloud polling.

## 🚀 0.7.0

- Simplified config-entry options so existing services only expose the refresh
  interval.
- Moved data-source selection out of options, matching the intended direction
  toward authenticated Idleon cloud sources.

## 🚀 0.6.4

- Replaced the Home Assistant brand assets with the official Idleon source icon.
- Kept the documentation project icon separate from the Home Assistant-served
  icon assets.

## 🚀 0.6.3

- Updated brand assets to use transparent-background images.
- Preserved Home Assistant and HACS icon/logo paths for local and custom
  repository installs.

## 🚀 0.6.2

- Added integration-local brand assets under `custom_components/idleon/brand`.
- Ensured the HACS release archive includes the integration brand icon.

## 🚀 0.6.1

- Added 2x icon and logo assets for Home Assistant and HACS.
- Expanded metadata checks around served brand image files.

## 🚀 0.6.0

- Flattened setup so users choose directly between `google`, `apple`, `email`,
  `steam`, and `local_file`.
- Removed the intermediate `idleon_cloud` source label from the user-facing
  setup path.

## 🚀 0.5.0

- Split cloud login provider selection onto its own setup page.
- Improved Google authorization instructions with a clearer login link and a
  prominent device code.
- Added support for Google verification URLs that can prefill the device code
  when Google supports it.

## 🚀 0.4.0

- Added Google device-code authorization for Idleon cloud data.
- Allowed Google-based Idleon accounts to be linked without pasting private
  session tokens.

## 🚀 0.3.0

- Fixed indexed character device names so `Character 1 - Manix84` displays as
  `Idleon Character 1 - Manix84` instead of repeating the character prefix.

## 🚀 0.2.0

- Added the local Git hook installer and smart version-bump workflow fixes.
- Promoted the integration version for the first authenticated cloud-source
  setup flow.

## 🚀 0.1.18

- Added the first authenticated Idleon cloud data source using Idleon
  email/password sign-in, stored refresh-token polling, and Firebase cloud-save
  reads.
- Documented the authenticated Idleon cloud data source and clarified that
  local/remote JSON sources are transitional development paths.
- Changed the account last-updated sensor to prefer the parsed source/export
  timestamp when available.
- Added duplicate-source protection when changing data sources through options.
- Added the parsed source/export timestamp to diagnostics.
- Added newly discovered character entities after successful data refreshes.
- Cleaned inventory carry capacity attributes by hiding filler categories
  and showing material capacity with a readable label.
- Improved HA share deployment tooling for local Home Assistant testing.

## 🚀 0.1.17

- Normalized class labels in the clean reference/debug output so known class IDs
  render as names instead of raw numbers.

## 🚀 0.1.16

- Made the debug parser output visibly refresh when parser code or example data
  changes.
- Added a debug renderer version marker so stale HTML output is obvious.

## 🚀 0.1.15

- Added an IdleonToolbox-derived parser registry for parser metadata.
- Captured parser IDs, referenced raw fields, websiteData dependencies, and
  exported function names for future mapping work.

## 🚀 0.1.14

- Connected split websiteData reference files to parser label lookups.
- Used websiteData-backed labels for classes, maps, monsters, inventory bags,
  and item samples where available.

## 🚀 0.1.13

- Simplified repeated websiteData type declarations so generated type files are
  easier to read and maintain.

## 🚀 0.1.12

- Improved generated Python type stubs for split websiteData files.
- Made the reference data more useful from Python tooling and parser scripts.

## 🚀 0.1.11

- Generated Python `.pyi` type stubs for websiteData reference files.
- Added Python-friendly type mapping alongside the split TypeScript reference
  data.

## 🚀 0.1.10

- Connected split websiteData files back to their TypeScript definition files.
- Preserved the relationship between each top-level websiteData part and its
  generated type metadata.

## 🚀 0.1.9

- Split the large websiteData reference file into one JSON file per top-level
  element.
- Added a manifest for the split reference data.

## 🚀 0.1.8

- Added a watchable debug HTML task for parsed Idleon data.
- Made parser/debug iteration quicker while working from real account captures.

## 🚀 0.1.7

- Added VS Code tasks backed by `just` recipes for common development commands.
- Added reusable commands for running Home Assistant, validation, tests, lint,
  formatting, type checks, builds, and releases.

## 🚀 0.1.6

- Added Makefile task shortcuts for common local development commands.
- Improved command discoverability before the `justfile` workflow was added.

## 🚀 0.1.5

- Added debug comparison between raw parsed output and the clean reference data.
- Made it easier to spot parser gaps against real Idleon captures.

## 🚀 0.1.4

- Added a parsed-data debug HTML renderer.
- Included parsed account, character, and reference sections without exposing
  huge raw JSON blobs in Home Assistant entities.

## 🚀 0.1.3

- Added readable Idleon map and AFK activity labels.
- Improved parser output for indexed exports by mapping known map/activity IDs
  to display text.

## 🚀 0.1.2

- Added support for wrapped Idleon export data from the local downloader flow.
- Parsed `saveData`, `charNameData`, and source update timestamps from wrapped
  exports.

## 🚀 0.1.1

- Added the smart version bump hook.
- Wired version updates across `pyproject.toml`, `manifest.json`, and
  integration constants.

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
- Added CI, metadata checks, community health files, documentation, and project
  icon assets.

🔒 v1 does not ask for Idleon credentials and does not implement login, Steam
login, browser scraping, session/token scraping, write actions, or services.
