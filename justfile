set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

# Run a local Home Assistant dev instance.
run:
    scripts/run-home-assistant

# Restart Home Assistant through the REST API. Requires HA_TOKEN.
restart:
    scripts/restart-home-assistant

# Validate the integration with lint, format, type, test, and release checks.
validate:
    scripts/check

# Run the test suite. Pass args with: just test tests/test_parser.py
test *args:
    scripts/test {{args}}

# Lint Python files.
lint:
    scripts/lint

# Format Python files.
format:
    scripts/format

# Check Python formatting.
format-check:
    scripts/format-check

# Run static type/compile checks.
typecheck:
    scripts/type-check

# Build a release zip in dist/.
build:
    scripts/build-release

# Check release metadata.
release-check:
    scripts/release-check

# Create a GitHub release when gh is installed, otherwise print the gh command.
release:
    scripts/create-release

# Render local parser debug output.
debug *args:
    scripts/render-debug-parsed-data {{args}}

# Inspect one Idleon export. Override with: just inspect path/to/export.json
inspect file="examples/rawData.json":
    scripts/inspect-idleon-export {{file}}
