# 🧪 Manual Testing

Use this guide to test HA Idleon in a real Home Assistant instance before real
Idleon export data is available.

## ✅ Prerequisites

- Home Assistant 2026.6.4 or newer.
- File access to your Home Assistant config directory.
- This repository checked out locally.

## 📦 Install The Integration

### HACS Custom Repository

1. Open HACS.
2. Open the custom repositories menu.
3. Add this repository URL as an `Integration` repository.
4. Install `HA Idleon`.
5. Restart Home Assistant.

### Manual Install

Copy the integration directory into Home Assistant:

```sh
cp -R custom_components/idleon /path/to/homeassistant/config/custom_components/
```

Then restart Home Assistant.

## 📄 Test With The Sample Local File

Copy the sample JSON into your Home Assistant config directory:

```sh
cp examples/sample_idleon_data.json /path/to/homeassistant/config/idleon_sample.json
```

If you run Home Assistant OS, Supervised, or Container, the path inside Home
Assistant is usually:

```txt
/config/idleon_sample.json
```

## 🌐 Test With A Remote URL

Serve the sample file from a machine that Home Assistant can reach:

```sh
python -m http.server 8124 --directory examples
```

Then configure HA Idleon with `remote_url` and a URL like:

```txt
http://<your-lan-ip>:8124/sample_idleon_data.json
```

If Home Assistant runs in a container, avoid `localhost` unless the HTTP server
is running inside the same container. Use a LAN IP or hostname that resolves
from the Home Assistant instance.

## ⚙️ Add The Integration

1. Go to Settings -> Devices & services.
2. Select Add integration.
3. Search for `HA Idleon`.
4. Choose `local_file`.
5. Enter the local file path, for example `/config/idleon_sample.json`.
6. Keep the default scan interval or set a value of at least `300` seconds.

## 🔎 Expected Result

Home Assistant should create:

- One account device: `Legends of Idleon Account`.
- Two character devices: `Idleon Character - Bubo Main` and
  `Idleon Character - Miner Alt`.
- Account sensors for total level, character count, gems, and last updated.
- Character sensors for level, class, current map, current activity, and AFK
  hours.
- Character binary sensors for inventory full and needs attention.

The sample data should show:

- Account total level: `365`.
- Character count: `2`.
- Gems: `1234`.
- `Bubo Main` inventory full: `on`.
- `Bubo Main` needs attention: `on`.
- `Miner Alt` inventory full: `off`.
- `Miner Alt` needs attention: `off`.

## 🔁 Change Settings

Use Configure from the integration entry to change:

- Data source type.
- Local file path or remote URL.
- Scan interval.

Changing options reloads the integration entry.

## 🩺 Diagnostics

Download diagnostics from the integration entry to confirm:

- Integration version.
- Data source type.
- Character count.
- Last successful update.
- Last error details.

Diagnostics should redact local file paths, remote URL query strings, and raw
account JSON.
