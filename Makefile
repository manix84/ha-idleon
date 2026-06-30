.PHONY: build check debug debug-watch format format-check inspect lint release release-check restart run test type-check validate website-data-split

DEBUG_ARGS ?=
INSPECT_FILE ?= examples/rawData.json
PYTEST_ARGS ?=

build:
	just build

check:
	just validate

debug:
	just debug $(DEBUG_ARGS)

debug-watch:
	just debug-watch $(DEBUG_ARGS)

format:
	just format

format-check:
	just format-check

inspect:
	just inspect $(INSPECT_FILE)

lint:
	just lint

release:
	just release

release-check:
	just release-check

restart:
	just restart

test:
	just test $(PYTEST_ARGS)

type-check:
	just typecheck

run:
	just run

validate:
	just validate

website-data-split:
	just website-data-split
