# 🕹️ HA Idleon

<p align="center">
  <img src="assets/project-icon-transparent.png" alt="HA Idleon project icon" width="160">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Home%20Assistant-2026.6.4-41BDF5" alt="Home Assistant 2026.6.4">
  <img src="https://img.shields.io/badge/HACS-custom-orange" alt="HACS custom repository">
  <img src="https://img.shields.io/badge/version-0.1.13-blue" alt="Version 0.1.13">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license">
  <br />
  <a href="https://github.com/manix84/ha-idleon/actions/workflows/lint.yml"><img src="https://github.com/manix84/ha-idleon/actions/workflows/lint.yml/badge.svg" alt="Lint status"></a>
  <a href="https://github.com/manix84/ha-idleon/actions/workflows/type-check.yml"><img src="https://github.com/manix84/ha-idleon/actions/workflows/type-check.yml/badge.svg" alt="Type Check status"></a>
  <a href="https://github.com/manix84/ha-idleon/actions/workflows/test.yml"><img src="https://github.com/manix84/ha-idleon/actions/workflows/test.yml/badge.svg" alt="Test status"></a>
  <a href="https://github.com/manix84/ha-idleon/actions/workflows/release-check.yml"><img src="https://github.com/manix84/ha-idleon/actions/workflows/release-check.yml/badge.svg" alt="Release Check status"></a>
</p>

Home Assistant integration for Legends of Idleon account and character stats.

This custom integration is experimental. It is not official to Legends of Idleon,
Lavaflame2, or any Idleon service provider.

The project icon is generated from Idleon artwork for recognizability, but this
project remains unofficial and community-maintained.

## ✨ What It Does

HA Idleon reads a JSON representation of your Idleon account data and creates
Home Assistant devices and entities for basic account and character status.

🔒 The integration is read-only. v1 does not ask for Idleon credentials. Users
should not paste private session tokens. Raw Idleon account data may contain
sensitive game/account details.

## 📦 Installation

### 🧩 HACS Custom Repository

1. Open HACS in Home Assistant.
2. Go to the custom repositories menu.
3. Add this repository URL as an `Integration` repository.
4. Install `HA Idleon`.
5. Restart Home Assistant.
6. Add the integration from Settings -> Devices & services.

### 🛠️ Manual Installation

1. Copy `custom_components/idleon` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from Settings -> Devices & services.

## ⚙️ Configuration

The integration is configured through the Home Assistant UI. YAML-only setup is
not supported.

Fields:

- `data_source_type`: `local_file` or `remote_url`
- `local_file_path`: required when using `local_file`
- `remote_url`: required when using `remote_url`
- `scan_interval`: defaults to `3600` seconds, minimum `300` seconds

The integration validates the source before creating the config entry.

## 📡 Data Sources

### 📄 Local File

Use `local_file` when Home Assistant can read a JSON file from disk. The path
must be readable by the Home Assistant process.

### 🌐 Remote URL

Use `remote_url` when Home Assistant can fetch a JSON document over HTTP or
HTTPS. Do not use URLs containing private session tokens or account secrets.

v1 intentionally does not implement Idleon login, Steam login, browser scraping,
session scraping, or token scraping.

## 🧭 Entities

One account device is created:

- `Legends of Idleon Account`

One device is created per character:

- `Idleon Character - <character name>`

Account sensors:

- Total level
- Character count
- Gems
- Last updated

Character sensors:

- Level
- Class
- Current map
- Current activity
- AFK hours

Character binary sensors:

- Inventory full
- Needs attention

The integration avoids raw JSON attributes and does not create hundreds of
default entities.

## 🔐 Privacy And Security

HA Idleon stores the configured data source in the Home Assistant config entry.
Diagnostics redact local file paths and remote URL query strings because these
may expose usernames, tokens, or private infrastructure.

Raw Idleon account JSON may contain sensitive game/account details. Keep source
files private and do not publish diagnostics that include unreviewed data from
future versions.

Third-party data notices are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## 🚧 Known Limitations

- The parser is flexible but based on early fixture-style JSON.
- Real Idleon export schemas may require parser updates.
- No write actions, services, automations, cloud storage, or auth flows are
  included.
- New characters require reloading the integration before entities are created.

## 🗺️ Roadmap

- Confirm the real Idleon data schema.
- Expand typed models without creating noisy default entities.
- Add more account and character metrics disabled by default where appropriate.
- Improve repair messages for invalid or stale data sources.

## 🧪 Development

Install test dependencies in a Python 3.14 environment, then run:

```sh
python -m pip install -r requirements_test.txt
pre-commit install
scripts/check
```

Convenience targets are also available through `make`:

```sh
make check
make test
make debug
```

The primary task runner is [`just`](https://github.com/casey/just), which is
also used by the VS Code tasks in `.vscode/tasks.json`:

```sh
just --list
just validate
just test
just lint
just format
just typecheck
just debug
just debug-watch
just website-data-split
just build
```

VS Code users can run the same commands from **Tasks: Run Task**. The tasks are
also compatible with the Task Explorer extension.

Targets can pass common arguments through variables:

```sh
make test PYTEST_ARGS=tests/test_parser.py
make inspect INSPECT_FILE=examples/rawData.json
make debug DEBUG_ARGS="--output-dir /tmp/idleon-debug"
```

Equivalent `just` examples:

```sh
just test tests/test_parser.py
just inspect examples/rawData.json
just debug --output-dir /tmp/idleon-debug
just debug-watch
just website-data-split
```

`just debug` builds `debug/parsed-data.html` once. `just debug-watch` keeps
running and regenerates `debug/parsed-data.html` when parser code, fixtures, or
local example data changes. In watch mode the generated HTML includes a short
browser refresh interval, so an open `debug/parsed-data.html` tab updates as you
work.

If you have a local `examples/websiteData.json` capture, `just
website-data-split` writes one file per top-level key into
`examples/websiteData/`. When `examples/websiteData.d.json.ts` is present, the
splitter also writes adjacent `.d.ts` and `.pyi` type files, plus a
`_manifest.json` connecting each JSON part to its TypeScript and Python type
references. Python code can read a split part with `load_website_data_part()`
from `custom_components.idleon.idleon_data`.

The source file and generated directory are ignored because the data is large
and only used as a local mapping reference.

Individual checks are available as:

```sh
scripts/lint
scripts/format
scripts/format-check
scripts/type-check
scripts/test
scripts/release-check
```

To inspect how the current parser sees local example data, generate ignored
debug files:

```sh
scripts/render-debug-parsed-data
open debug/parsed-data.html
```

By default this reads `examples/rawData.json` and `examples/real_data*.json`
when present. If `examples/cleanData.json` exists, the HTML report includes it
as a clean parsed reference. The generated `debug/` directory is ignored because
parsed output from real exports can still contain private account details.

The local pre-commit hook bumps versions automatically for release-affecting
changes:

- docs-only changes do not bump the version.
- internal code changes bump the patch version.
- entity, config flow, model, manifest, strings, and translation changes bump
  the minor version.

Override the hook when needed:

```sh
HA_IDLEON_VERSION_BUMP=minor git commit
HA_IDLEON_VERSION_BUMP=patch git commit
HA_IDLEON_VERSION_BUMP=skip git commit
```

For testing in a real Home Assistant instance, see
[Manual Testing](docs/manual-testing.md).
