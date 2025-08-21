MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

VENV := .venv
INSTALL_SENTINEL := $(VENV)/.install.success
VERSION := $(shell poetry version -s)
PYTHON := $(VENV)/bin/python

CI ?=

RUN := poetry run

### Help ###
.PHONY: help
help::
	@echo "╭─────────────────────────────────────────────────────────────╮"
	@echo "│ Makefile for dm-bip                                         │"
	@echo "│ ────────────────────────                                    │"
	@echo "│ Usage:                                                      │"
	@echo "│     make <target>                                           │"
	@echo "│                                                             │"
	@echo "│ Pipeline targets:                                           │"
	@echo "│     pipeline            Run the pipeline for a set of files |"
	@echo "|     pipeline-debug      Print pipeline configuration        |"
	@echo "│                                                             │"
	@echo "│ Schema targets:                                             │"
	@echo "│     schema-create       Create a schema from a set of files │"
	@echo "│     schema-lint         Lint a schema from a set of files   │"
	@echo "│     schema-clean        Remove all generated schema files   │"
	@echo "│                                                             │"
	@echo "│ Validation targets:                                         │"
	@echo "│     validate-schema     Validate generated schema           │"
	@echo "│     validate-data       Validate data to generated schema   │"
	@echo "│     validate-clean      Remove validation reports           │"
	@echo "│                                                             │"
	@echo "│ Project targets:                                            │"
	@echo "│     help                Print this help message             │"
	@echo "│     all                 Install everything                  │"
	@echo "│     fresh               Clean and install everything        │"
	@echo "│     clean               Clean up build artifacts            │"
	@echo "│     clobber             Clean up generated files            │"
	@echo "│                                                             │"
	@echo "│     install             Set up the virtual environment      |"
	@echo "│     git-hooks-install   Install git pre-commit hooks        |"
	@echo "│     docs                Generate documentation              │"
	@echo "│     test                Run tests                           │"
	@echo "│                                                             │"
	@echo "│     lint                Lint all code                       │"
	@echo "│     format              Format all code                     │"
	@echo "│     coverage            Measure and report test coverage    │"
	@echo "│                                                             │"
	@echo "│     jupyter-notebook    Start a Jupyter server and notebook │"
	@echo "╰─────────────────────────────────────────────────────────────╯"
	@echo


### Installation and Setup ###

.PHONY: all
all: install

.PHONY: fresh
fresh: clean clobber all


$(INSTALL_SENTINEL): poetry.lock
	poetry install --with dev --with docs $(if $(CI),--no-interaction,)
	touch $@

$(PYTHON): $(INSTALL_SENTINEL)

.PHONY: install
install: $(INSTALL_SENTINEL)

git-hooks-install: .git/hooks/pre-commit

.git/hooks/pre-commit: scripts/git-hooks/pre-commit
	cp $< $@
	chmod +x $@


### Documentation ###

.PHONY: docs
docs: $(INSTALL_SENTINEL)
	$(RUN) sphinx-apidoc -o docs src/dm_bip/ --ext-autodoc -f
	$(RUN) sphinx-build -b html docs docs/_build


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
	rm -rf docs/_build
	rm -rf $(VENV)

.PHONY: clobber
clobber:


.PHONY: lint
lint: $(PYTHON)
	$(RUN) ruff check $(if $(CI),--output-format=github,)
	$(RUN) ruff format --check
	$(MAKE) lint-notebooks


.PHONY: format
format: $(PYTHON)
	-$(RUN) ruff check --fix
	-$(RUN) ruff format

.PHONY: coverage
coverage: $(PYTHON)
	$(RUN) coverage run -m pytest tests
	$(RUN) coverage report -m

include pipeline.Makefile
include notebook.Makefile
