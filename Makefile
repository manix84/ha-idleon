.PHONY: check debug format format-check inspect lint release-check test type-check

DEBUG_ARGS ?=
INSPECT_FILE ?= examples/rawData.json
PYTEST_ARGS ?=

check:
	scripts/check

debug:
	scripts/render-debug-parsed-data $(DEBUG_ARGS)

format:
	scripts/format

format-check:
	scripts/format-check

inspect:
	scripts/inspect-idleon-export $(INSPECT_FILE)

lint:
	scripts/lint

release-check:
	scripts/release-check

test:
	scripts/test $(PYTEST_ARGS)

type-check:
	scripts/type-check
