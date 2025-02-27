MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

VENV := .venv
INSTALL_SENTINEL := $(VENV)/.install.success
VERSION := $(shell poetry version -s)
PYTHON := $(VENV)/bin/python

LINT_EXCLUDES := tests/input tests/output

RUN := poetry run


### Installation and Setup ###

.PHONY: all
all: $(INSTALL_SENTINEL) docs

.PHONY: fresh
fresh: clean clobber all


$(INSTALL_SENTINEL): poetry.lock
	poetry install --with dev --with docs
	touch $@

$(PYTHON): $(INSTALL_SENTINEL)


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
