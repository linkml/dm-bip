RUN := poetry run


# Configurable parameters via environment variables
DM_INPUT_DIR ?=
DM_INPUT_FILES ?=
DM_SCHEMA_NAME ?= Schema
DM_OUTPUT_DIR ?= output/$(DM_SCHEMA_NAME)
VALIDATOR_OUTPUT_DIR ?= $(DM_OUTPUT_DIR)/schema-validator-data

# Derived output files
SCHEMA_FILE := $(DM_OUTPUT_DIR)/schema-automator-data/$(DM_SCHEMA_NAME).yaml
SCHEMA_LINT_LOG := $(VALIDATOR_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-schema-lint.log
SCHEMA_VALIDATE_LOG := $(VALIDATOR_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-schema-validate.log
DATA_VALIDATE_LOG := $(VALIDATOR_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-data-validate.log

ifdef DM_INPUT_FILES
	INPUT_FILES := $(DM_INPUT_FILES)
else ifdef DM_INPUT_DIR
	INPUT_FILES := $(shell find $(DM_INPUT_DIR) -type f -regex '.*\.[ct]sv' 2> /dev/null)
else
	INPUT_FILES :=
endif

# The names of the files used as inputs, with the base input directory stripped.
# (Not currently not used).
INPUT_FILENAMES := $(INPUT_FILES:$(DM_INPUT_DIR)/%=%)


define DEBUG

Configurable variables:
  DM_SCHEMA_NAME = $(DM_SCHEMA_NAME)
  DM_INPUT_DIR = $(DM_INPUT_DIR)
  DM_INPUT_FILES = $(DM_INPUT_FILES)
  DM_OUTPUT_DIR = $(DM_OUTPUT_DIR)

Generated variables
  input files: $(if $(INPUT_FILES),$(INPUT_FILES),(none))
  schema output: $(SCHEMA_FILE)

endef

define HELP
To specify which files to generate a schema from, set the DM_INPUT_DIR or DM_INPUT_FILES environment variables.

By default, the value of DM_INPUT_DIR is `input`. and the value of `DM_INPUT_FILES` is empty. If `DM_INPUT_FILES`, `DM_INPUT_DIR` will be ignored.

To specify the name of the schema, set the DM_SCHEMA_NAME environment variable. The default is `Schema`.

All of the schema targets use these variables. You may want to set them ahead of time, for example in Bash: `export DM_INPUT_DIR=my/input/directory`

Examples
========

Create a schema for all CSV/TSV files in the toy data directory in a schema at `output/ToySchema/schema-automator-data/ToySchema.yaml`

    DM_SCHEMA_NAME="ToySchema" DM_INPUT_DIR=toy_data/initial make create_schema

Create a schema from a single file at `output/schema-automator-data/Schema.yaml`

    DM_INPUT_FILES=toy_data/initial/demographics.tsv make schema-create
endef

check_input_files = \
	$(if $(INPUT_FILES),,\
	$(info No input files detected. Debug information:)\
	$(info $(DEBUG))\
	$(error no input files detected))



# VALIDATE_TARGETS := $(addprefix validate-,$(basename $(notdir $(INPUT_FILENAMES))))

.PHONY: schema-all
schema-all: $(SCHEMA_FILE) schema-lint

.PHONY: schema-clean
schema-clean:
	rm -rf $(DM_OUTPUT_DIR)

$(SCHEMA_FILE): $(INPUT_FILES)
	@:$(call check_input_files)
	mkdir -p $(@D)
	$(RUN) schemauto generalize-tsvs -n $(DM_SCHEMA_NAME) $^ -o $@
	@echo
	@echo "  Created schema at $@"
	@echo

.PHONY: schema-debug
schema-debug:
	@:$(info $(DEBUG))

.PHONY: schema-ensure-input
schema-ensure-input:
	@:$(call check_input_files)

.PHONY: schema-create
schema-create: $(SCHEMA_FILE)

.PHONY: schema-lint
schema-lint: $(SCHEMA_FILE)
	@mkdir -p $(VALIDATOR_OUTPUT_DIR)
	@echo "Linting schema $(SCHEMA_FILE)..."
	@if $(RUN) linkml-lint $< > $(SCHEMA_LINT_LOG) 2>&1; then \
			echo "Schema linting passed." >> $(SCHEMA_LINT_LOG); \
		else \
			echo "Schema linting failed. See log for details." >> $(SCHEMA_LINT_LOG); \
		fi;
	@echo "Schema linting log written to $(SCHEMA_LINT_LOG)"


COND_START_COL ?= 6

.PHONY: extract-conditions
extract-conditions:
	./src/dm_bip/cleaners/extract_conditions.sh $(input_file) $(COND_START_COL)


.PHONY: annotate
annotate:
	@echo "** Annotate data file with ontology terms using config and input_file: $(input_file)"
	@cmd="python harmonica/harmonize.py annotate \
		--config config/config.yml \
		--input_file $(input_file)"; \
	if [ -n "$(output_dir)" ]; then cmd="$$cmd --output_dir $(output_dir)"; fi; \
	if [ -n "$(refresh)" ]; then cmd="$$cmd --refresh"; fi; \
	echo $$cmd; \
	eval $$cmd

.PHONY: help
.PHONY: schema-help
help::
schema-help:
	@:$(info $(HELP))
	@:$(info )
	@:$(info Defined variables)
	@:$(info =================)
	@:$(info $(DEBUG))

.PHONY: validate-schema
validate-schema: $(SCHEMA_FILE)
	@mkdir -p $(VALIDATOR_OUTPUT_DIR)
	@echo "Validating schema $(SCHEMA_FILE)..."
	@if $(RUN) linkml validate --schema $< > $(SCHEMA_VALIDATE_LOG) 2>&1; then \
			echo "  ✓ $$f passed." | tee -a $(SCHEMA_VALIDATE_LOG); \
		else \
			echo "  ✗ $$f failed. See $$out" | tee -a $(SCHEMA_VALIDATE_LOG); \
		fi;
	@echo "Schema validation written to $(SCHEMA_VALIDATE_LOG)"


.PHONY: validate-data
validate-data: $(SCHEMA_FILE)
	@:$(call check_input_files)
	@mkdir -p $(VALIDATOR_OUTPUT_DIR)
	@rm -f $(DATA_VALIDATE_LOG)
	@for f in $(INPUT_FILES); do \
		class=$$(basename $$f | sed -E 's/\.[ct]sv$$//' | tr '-' '_' | tr '[:upper:]' '[:lower:]'); \
		out="$(VALIDATOR_OUTPUT_DIR)/$$(basename $$f).validate.log"; \
		echo "Validating $$f as class '$$class'..." | tee -a $(DATA_VALIDATE_LOG); \
		if $(RUN) linkml validate --schema $(SCHEMA_FILE) --target-class $$class $$f 2>&1; then \
			echo "  ✓ $$f passed." | tee -a $(DATA_VALIDATE_LOG); \
		else \
			echo "  ✗ $$f failed. See $$out" | tee -a $(DATA_VALIDATE_LOG); \
		fi; \
	done
	@echo "Data validation summary written to $(DATA_VALIDATE_LOG)"

.PHONY: validate-debug
validate-debug:
	@:$(info $(DEBUG))
	