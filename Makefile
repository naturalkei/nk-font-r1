# nk-nerd-font developer shortcuts. Run `make setup` once, then `make all`.
PY ?= .venv/bin/python
NK ?= .venv/bin/nkfont
FAMILY ?= mono

.PHONY: setup app app-install fetch build patch check audit proof tune test lint qa qa-ci qa-release release-pages all clean

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -e ".[dev]"

# NK Studio desktop window (pywebview). `make app-install` also adds ~/Applications/NK Studio.app.
app:
	$(PY) -m pip install -q -e ".[dev,app]"
	$(NK) app

app-install:
	$(PY) -m pip install -q -e ".[dev,app]"
	$(NK) app --install-mac-app

fetch:
	$(NK) fetch

build: fetch
	$(NK) build $(FAMILY)

patch:
	$(NK) patch

check:
	$(NK) check build/master/NKMono-*.ttf $(wildcard dist/NKMono*.ttf) --base sources/JetBrainsMono-Regular.ttf

# fontbakery (config/audit.toml); installs the optional [audit] extra on first use.
audit:
	$(PY) -m pip install -q -e ".[dev,audit]"
	$(NK) audit

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

qa-release:
	$(PY) -m pip install -q -e ".[dev,audit]"
	$(NK) qa --profile release --family $(FAMILY)

# Publish the site: fast-forward the `release` branch to main; .github/workflows/pages.yml deploys it.
release-pages:
	git fetch origin main
	git push origin origin/main:refs/heads/release

all: build check patch check

clean:
	rm -rf build dist proofs reports
