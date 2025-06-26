RUN := poetry run


# Configurable parameters via environment variables
DM_INPUT_DIR ?=
DM_INPUT_FILES ?=
DM_SCHEMA_NAME ?= Schema
DM_OUTPUT_DIR ?= output/$(DM_SCHEMA_NAME)
VALIDATOR_OUTPUT_DIR ?= $(DM_OUTPUT_DIR)/schema-validator-logs

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
INPUT_FILENAMES := $(INPUT_FILES:$(if $(DM_INPUT_DIR),$(DM_INPUT_DIR)/,)%=%)


NOW := $(shell date +%s)

# Derive validate data log target names from INPUT_FILENAMES
INPUT_FILE_KEYS := $(subst /,__,$(INPUT_FILENAMES))
VALIDATE_LOGS := $(INPUT_FILE_KEYS:%=$(VALIDATOR_OUTPUT_DIR)/validation/%/success.log)


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


# Given the name of an output log, determine the file that produced it.
input_file_from_validation_log = $(if $(DM_INPUT_DIR),$(DM_INPUT_DIR)/,)$(subst __,/,$(1))

# Given an input file, determine the class name that schema automator assigned it.
class_name_from_input = $(shell echo $(notdir $(basename $(1))) | tr '-' '_' | tr '[:upper:]' '[:lower:]')

# Pattern rule to handle validation per file
#
# Here are the variables in the following recipe, assuming an input file named "data/chairs.tsv" and
# the default values for $(DM_OUTPUT_DIR) and $(VALIDATOR_OUTPUT_DIR):
#
# Make variables:
#     % and $*: data__chairs.tsv
#     $<: data/chairs.tsv
#
# Shell variables
#     LOG_DIR:             output/schema-validator-logs/validation/data__chairs.tsv/
#     FAILURE_DIR_SYMLINK: output/schema-validator-logs/errors/data__chairs.tsv/
#     LOG_FILENAME:        $LOG_DIR/data__chairs.tsv.92475972.log
#     SUCCESS_SYMLINK:     $LOG_DIR/success.log <-- the same as $@ (the target of this recipe)
#     FAILURE_SYMLINK:     $LOG_DIR/latest-error.log
#
# If validation hasn't run yet, here is the idea:
#   * Run `linkml validate` for the target class in schema $(SCHEMA_FILE) against $< (the input file)
#   * No matter what, send the output of that command to $$LOG_FILENAME, a timestamped log of the validation
#     command
#   * If validation was successful, link that log to $$SUCCESS_SYMLINK, aka $@, the target of this
#     recipe.
#   * If validation was not successful, link that log to $$FAILURE_SYMLINK, and link the log directory for
#     this file ($$LOG_DIR) to $$FAILURE_DIR_SYMLINK. This will allow someone to quickly check out the
#     `output/schema-validator/errors/` directory to see what files did not validate
#
# If validation *has* run, then the only files that will be validated are ones that do not have the
# $$SUCCESS_SYMLINK symlink created. Before validation is run again, the failure symlinks are removed.
$(VALIDATOR_OUTPUT_DIR)/validation/%/success.log: $(call input_file_from_validation_log,%) $(SCHEMA_FILE)
	@:$(call check_input_files)
	@mkdir -p $(VALIDATOR_OUTPUT_DIR)/validation $(VALIDATOR_OUTPUT_DIR)/errors
	@echo "Validating $< as class '$(call class_name_from_input,$<)'..." | tee -a $(DATA_VALIDATE_LOG)
	@LOG_DIR=$(VALIDATOR_OUTPUT_DIR)/validation/$*; \
	FAILURE_DIR_SYMLINK=$(VALIDATOR_OUTPUT_DIR)/errors/$*; \
	LOG_FILENAME=$*.$(NOW).log; \
	SUCCESS_SYMLINK=$$LOG_DIR/success.log; \
	FAILURE_SYMLINK=$$LOG_DIR/latest-error.log; \
	rm -f $$SUCCESS_SYMLINK $$FAILURE_SYMLINK $$FAILURE_DIR_SYMLINK; \
	mkdir -p $$LOG_DIR; \
	if $(RUN) linkml validate \
		--schema $(SCHEMA_FILE) \
		--target-class $(call class_name_from_input,$<) \
		$< > $$LOG_DIR/$$LOG_FILENAME 2>&1; \
	then \
		echo "  ✓ $< passed." | tee -a $(DATA_VALIDATE_LOG); \
		ln -s $$LOG_FILENAME $$SUCCESS_SYMLINK; \
	else \
		echo "  ✗ $< failed. See $$FAILURE_DIR_SYMLINK/latest-error.log" | tee -a $(DATA_VALIDATE_LOG); \
		ln -s $$LOG_FILENAME $$FAILURE_SYMLINK; \
		ln -s ../validation/$* $$FAILURE_DIR_SYMLINK; \
	fi

$(VALIDATOR_OUTPUT_DIR)/_validation_complete: $(VALIDATE_LOGS)
	@echo
	@echo "Data validation summary written to $(DATA_VALIDATE_LOG)"
	@echo
	@echo Validation complete.
	@NUM_FAILURES=$$(ls $(VALIDATOR_OUTPUT_DIR)/errors | wc -l); \
	if [ $$NUM_FAILURES -gt 0 ]; then \
		echo Validation failures: $$NUM_FAILURES; \
		echo; \
		echo "Failing files:"; \
		ls -1 $(VALIDATOR_OUTPUT_DIR)/errors | sed -e 's/^/    /'; \
		echo; \
		echo "See $(VALIDATOR_OUTPUT_DIR)/errors for error logs."; \
		echo; \
	else \
		touch $@; \
	fi


.PHONY: validate-data
validate-data: $(VALIDATOR_OUTPUT_DIR)/_validation_complete


.PHONY: clean-validate
validate-clean:
	rm -rf $(VALIDATOR_OUTPUT_DIR)


.PHONY: validate-debug
validate-debug:
	@:$(info $(DEBUG))


# When adding linkml-map workflow, make $(VALIDATOR_OUTPUT_DIR)_validation_complete as
# a prerequisite. This file is only made when all validation passes.
