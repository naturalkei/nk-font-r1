# nk-nerd-font developer shortcuts. Run `make setup` once, then `make all`.
PY ?= .venv/bin/python
NK ?= .venv/bin/nkfont
FAMILY ?= sans

.PHONY: setup fetch build patch check proof tune test lint qa qa-ci all clean

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -e ".[dev]"

fetch:
	$(NK) fetch

build: fetch
	$(NK) build $(FAMILY)

patch:
	$(NK) patch

check:
	$(NK) check build/master/*.ttf $(wildcard dist/*.ttf) --base sources/JetBrainsMono-Regular.ttf

proof:
	$(NK) proof build/master/*.ttf -o proofs/proof.png

tune:
	$(NK) tune $(FAMILY) --scale 0.92:1.04:0.04 -o proofs/tune.png

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

qa:
	$(NK) qa

qa-ci:
	$(NK) qa --profile ci

all: build check patch check

clean:
	rm -rf build dist proofs reports
