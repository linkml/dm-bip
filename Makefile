MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

VENV := .venv
INSTALL_SENTINEL := $(VENV)/.install.success
VERSION := $(shell poetry version -s)
PYTHON := $(VENV)/bin/python

LINT_EXCLUDES := tests/input tests/output

RUN := poetry run

### Help ###
.PHONY: help
help:
	@echo "╭───────────────────────────────────────────────────────────╮"
	@echo "│ Makefile for dm-bip                                       │"
	@echo "│ ────────────────────────                                  │"
	@echo "│ Usage:                                                    │"
	@echo "│     make <target>                                         │"
	@echo "│                                                           │"
	@echo "│ Targets:                                                  │"
	@echo "│     help                Print this help message           │"
	@echo "│     all                 Install everything                │"
	@echo "│     fresh               Clean and install everything      │"
	@echo "│     clean               Clean up build artifacts          │"
	@echo "│     clobber             Clean up generated files          │"
	@echo "│                                                           │"
	@echo "│     install             Set up the virtual environment    |"
	@echo "│     docs                Generate documentation            │"
	@echo "│     test                Run tests                         │"
	@echo "│     lint                Lint all code                     │"
	@echo "│     format              Format all code                   │"
	@echo "│     coverage            Measure and report test coverage  │"
	@echo "╰───────────────────────────────────────────────────────────╯"


### Installation and Setup ###

.PHONY: all
all: install

.PHONY: fresh
fresh: clean clobber all


$(INSTALL_SENTINEL): poetry.lock
	poetry install --with dev --with docs
	touch $@

$(PYTHON): $(INSTALL_SENTINEL)

.PHONY: install
install: $(INSTALL_SENTINEL)


### Documentation ###

.PHONY: docs
docs: $(INSTALL_SENTINEL)
	$(RUN) mkdocs build


### Testing ###

.PHONY: test
test: $(PYTHON)
	$(RUN) pytest tests


### Linting, Formatting, and Cleaning ###

.PHONY: clean
clean:
	rm -f `find . -type f -name '*.py[co]'`
	rm -rf `find . -name __pycache__`
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf $(VENV)

.PHONY: clobber
clobber:


.PHONY: lint
lint: $(PYTHON)
	-$(RUN) ruff check --diff src/ tests/ --exclude $(LINT_EXCLUDES)
	-$(RUN) ruff format --check --diff --exclude $(LINT_EXCLUDES)


.PHONY: format
format: $(PYTHON)
	-$(RUN) ruff check --fix src/ tests/ --exclude $(LINT_EXCLUDES)
	-$(RUN) ruff format src/ tests/ --exclude $(LINT_EXCLUDES)

.PHONY: coverage
coverage: $(PYTHON)
	$(RUN) coverage run -m pytest tests
	$(RUN) coverage report -m
