# git-wtf release tooling
# ─────────────────────────────────────────────────────────────────────────────
# Usage:
#   make dev          install in editable mode for local development
#   make build        build wheel + sdist
#   make publish      publish to PyPI (requires PYPI_API_TOKEN or trusted pub)
#   make release v=1.2.3  bump version, tag, push — triggers CI publish
#   make brew-resources   regenerate homebrew resource blocks (requires poet)
#   make clean        remove build artifacts

VERSION_FILE := git_wtf/__init__.py
CURRENT_VERSION := $(shell grep '__version__' $(VERSION_FILE) | cut -d'"' -f2)

.PHONY: dev build publish release brew-resources clean check

# ── development ───────────────────────────────────────────────────────────────

dev:
	pip install -e ".[dev]" 2>/dev/null || pip install -e .

check:
	python -c "from git_wtf.cli import main; print('imports ok')"
	git-wtf --version

# ── build ─────────────────────────────────────────────────────────────────────

build: clean
	pip install build --quiet
	python -m build
	@echo ""
	@echo "built:"
	@ls -lh dist/

# ── publish ───────────────────────────────────────────────────────────────────

publish: build
	pip install twine --quiet
	twine upload dist/*

# ── release (bump + tag + push → triggers CI) ────────────────────────────────

release:
ifndef v
	$(error usage: make release v=1.2.3)
endif
	@echo "releasing v$(v) (current: $(CURRENT_VERSION))"
	# Bump version in __init__.py and pyproject.toml
	sed -i 's/__version__ = "$(CURRENT_VERSION)"/__version__ = "$(v)"/' $(VERSION_FILE)
	sed -i 's/^version = "$(CURRENT_VERSION)"/version = "$(v)"/' pyproject.toml
	# Update formula version reference (the sha256 will be updated by CI after publish)
	sed -i 's/git_wtf-$(CURRENT_VERSION)/git_wtf-$(v)/g' Formula/git-wtf.rb
	git add $(VERSION_FILE) pyproject.toml Formula/git-wtf.rb
	git commit -m "release: v$(v)"
	git tag "v$(v)"
	git push && git push --tags
	@echo ""
	@echo "tag v$(v) pushed — GitHub Actions will publish to PyPI and update the brew tap."

# ── homebrew resource blocks ──────────────────────────────────────────────────
# Requires: pip install homebrew-pypi-poet

brew-resources:
	pip install homebrew-pypi-poet --quiet
	@echo ""
	@echo "# paste these resource blocks into Formula/git-wtf.rb:"
	@echo ""
	poet git-wtf

# ── clean ─────────────────────────────────────────────────────────────────────

clean:
	rm -rf dist/ build/ *.egg-info
