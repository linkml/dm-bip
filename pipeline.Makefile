RUN := poetry run


# DM-BIP PIPELINE
# ============
# The pipeline consists of these steps:
#   1. Create the schema with schema-automator
#   2. Validate the data files with `linkml validate`
#   3. Transform the data files with `linkml-map` (TODO)

# There are four configurable parameters:
#
#   1. DM_INPUT_DIR - Input CSV and/or TSV files
#   2. DM_INPUT_FILES - Input directory containing CSV and/or TSV files
#   3. DM_SCHEMA_NAME - The name of the schema
#   4. DM_OUTPUT_DIR - The directory where all generated files go
#
# All other variables are derived from these.



# Configurable parameters via environment variables
# ============
DM_INPUT_DIR   ?=
DM_INPUT_FILES ?=
DM_SCHEMA_NAME ?= Schema
DM_OUTPUT_DIR  ?= output/$(DM_SCHEMA_NAME)


# Derived output files
# ============
SCHEMA_FILE                 := $(DM_OUTPUT_DIR)/$(DM_SCHEMA_NAME).yaml
VALIDATE_OUTPUT_DIR         := $(DM_OUTPUT_DIR)/validation-logs
VALIDATED_FILES_LIST        := $(VALIDATE_OUTPUT_DIR)/input-files.txt


# Logging files
# ============
SCHEMA_LINT_LOG             := $(VALIDATE_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-schema-lint.log
SCHEMA_VALIDATE_LOG         := $(VALIDATE_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-schema-validate.log
DATA_VALIDATE_LOG           := $(VALIDATE_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-data-validate.log
DATA_VALIDATE_FILES_DIR     := $(VALIDATE_OUTPUT_DIR)/data-validation
DATA_VALIDATE_ERRORS_DIR    := $(VALIDATE_OUTPUT_DIR)/data-validation-errors

VALIDATION_SUCCESS_SENTINEL := $(VALIDATE_OUTPUT_DIR)/_data_validation_complete


# Pipeline inputs
# ============
ifdef DM_INPUT_FILES
	INPUT_FILES := $(DM_INPUT_FILES)
else ifdef DM_INPUT_DIR
	INPUT_FILES := $(shell find $(DM_INPUT_DIR) -type f -regex '.*\.[ct]sv' 2> /dev/null)
else
	INPUT_FILES :=
endif

# Call this function in any recipe that depends on input files
check_input_files = \
	$(if $(INPUT_FILES),,\
	$(info No input files detected. Debug information:)\
	$(info $(DEBUG))\
	$(error no input files detected))



# Variables for logging
# ============

# The names of the files used as inputs, with the base input directory stripped (if it exists)
INPUT_FILENAMES := $(INPUT_FILES:$(if $(DM_INPUT_DIR),$(DM_INPUT_DIR)/,)%=%)

# unix timestamp of the invocation
NOW := $(shell date +%s)

# Derive validate data log target names from INPUT_FILENAMES
INPUT_FILE_KEYS := $(subst /,__,$(INPUT_FILENAMES))
VALIDATE_SUCCESS_LOGS := $(INPUT_FILE_KEYS:%=$(DATA_VALIDATE_FILES_DIR)/%/success.log)


# Information for those running the pipeline
# ============
define DEBUG
Configured variables:
  DM_SCHEMA_NAME = $(DM_SCHEMA_NAME)
  DM_INPUT_DIR   = $(DM_INPUT_DIR)
  DM_INPUT_FILES = $(DM_INPUT_FILES)
  DM_OUTPUT_DIR  = $(DM_OUTPUT_DIR)

Generated variables
  input files:                    $(if $(INPUT_FILES),$(INPUT_FILES),(none))
  schema output:                  $(SCHEMA_FILE)

Generated logs:
  schema lint log:                $(SCHEMA_LINT_LOG)
  schema validation log:          $(SCHEMA_VALIDATE_LOG)
  data validation log:            $(DATA_VALIDATE_LOG)
  data validation logs by file:   $(DATA_VALIDATE_FILES_DIR)
  data validation errors by file: $(DATA_VALIDATE_ERRORS_DIR)

endef

define HELP
dm-bip pipeline
============
To specify the files to feed into the pipeline, set one of the following environment variables:

    DM_INPUT_DIR       A directory containing TSV/CSV files
    DM_INPUT_FILES     A list of TSV/CSV files

If `DM_INPUT_FILES` is defined, `DM_INPUT_DIR` will be ignored.

To specify the name of the schema, set the following environment variables:

    DM_SCHEMA_NAME     (default: Schema)

All output for the pipeline is written to one directory, also set by an environment variable:

    DM_SCHEMA_OUTPUT   (default: output)


Examples
============
1. Run the pipeline for all CSV/TSV files in the directory `~/data/cancer-study`, with a schema named `CancerStudy`

    make pipeline DM_INPUT_DIR=~/data/cancer-study DM_SCHEMA_NAME=CancerStudy

2. Run the pipeline for two files: `StudyA/data.tsv` and `StudyB/data.tsv`, with the default schema name:

    make pipeline DM_INPUT_FILES="StudyA/data.tsv StudyB/data.tsv"
endef

.PHONY: help
help::
	@:$(info $(HELP))
	@:$(info )
	@:$(info Defined variables)
	@:$(info =================)
	@:$(info $(DEBUG))



# Pipeline goal
# ============
# VERY IMPORTANT: Make sure that there is one dependency for the endpoint of the pipeline!
# It makes it so that if someone types `make`, it does everything.
.DEFAULT_GOAL := pipeline

.PHONY: pipeline
pipeline: $(VALIDATION_SUCCESS_SENTINEL)

.PHONY: pipeline-debug
pipeline-debug:
	@:$(info $(DEBUG))



# Schema creation goals
# ============
.PHONY: schema-all
schema-all: $(SCHEMA_FILE) schema-lint

.PHONY: schema-clean
schema-clean:
	rm -f $(SCHEMA_FILE)

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
	@mkdir -p $(VALIDATE_OUTPUT_DIR)
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


# Schema Validator goals
# ============
#
.PHONY: validate-schema
validate-schema: $(SCHEMA_FILE)
	@mkdir -p $(VALIDATE_OUTPUT_DIR)
	@echo "Validating schema $(SCHEMA_FILE)..."
	@if $(RUN) linkml validate --schema $< > $(SCHEMA_VALIDATE_LOG) 2>&1; then \
			echo "  ✓ $$f passed." | tee -a $(SCHEMA_VALIDATE_LOG); \
		else \
			echo "  ✗ $$f failed. See $$out" | tee -a $(SCHEMA_VALIDATE_LOG); \
		fi;
	@echo "Schema validation written to $(SCHEMA_VALIDATE_LOG)"



# Given the name of an output log, determine the file that produced it.
input_file_from_validation_log = $(if $(DM_INPUT_DIR),$(DM_INPUT_DIR)/,)$(subst __,/,$(1))

# Given an input file, determine the class name that schema automator assigned to it.
class_name_from_input = $(shell echo $(notdir $(basename $(1))) | tr '-' '_' | tr '[:upper:]' '[:lower:]')

# Pattern rule to handle validation per file
#
# Here are the variables in the following recipe, assuming an input file named "data/study.tsv" and
# the default values for $(DM_OUTPUT_DIR) and $(VALIDATE_OUTPUT_DIR):
#
# Make variables:
#     % and $*: data__study.tsv
#     $<: data/study.tsv
#
# Shell variables
#     LOG_DIR:             output/validation-logs/validation/data__study.tsv/
#     FAILURE_DIR_SYMLINK: output/validation-logs/errors/data__study.tsv/
#     LOG_FILENAME:        $LOG_DIR/data__study.tsv.92475972.log
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
$(DATA_VALIDATE_FILES_DIR)/%/success.log: $(call input_file_from_validation_log,%) $(SCHEMA_FILE)
	@:$(call check_input_files)
	@mkdir -p $(DATA_VALIDATE_FILES_DIR) $(DATA_VALIDATE_ERRORS_DIR)
	@echo "Validating $< as class '$(call class_name_from_input,$<)'..." | tee -a $(DATA_VALIDATE_LOG)
	@LOG_DIR=$(DATA_VALIDATE_FILES_DIR)/$*; \
	FAILURE_DIR_SYMLINK=$(DATA_VALIDATE_ERRORS_DIR)/$*; \
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
		ln -s ../data-validation/$* $$FAILURE_DIR_SYMLINK; \
	fi


$(VALIDATED_FILES_LIST):
	mkdir -p $(@D)
	echo $(INPUT_FILE_KEYS) | tr ' ' '\n' > $@

$(VALIDATION_SUCCESS_SENTINEL): $(VALIDATED_FILES_LIST) $(VALIDATE_SUCCESS_LOGS)
	@echo
	@echo "Data validation summary written to $(DATA_VALIDATE_LOG)"
	@echo
	@echo Validation complete.
	@echo Number of input files: $$(cat $< | wc -l)
	@NUM_FAILURES=$$(ls $(DATA_VALIDATE_ERRORS_DIR) | grep -F -f $< | wc -l); \
	if [ $$NUM_FAILURES -gt 0 ]; then \
		echo Number of files with validation errors: $$NUM_FAILURES; \
		echo; \
		echo "Failing files:"; \
		ls -1 $(DATA_VALIDATE_ERRORS_DIR) | grep -F -f $< | sed -e 's/^/    /'; \
		echo; \
		echo "See $(DATA_VALIDATE_ERRORS_DIR) for error logs."; \
		echo; \
	else \
		touch $@; \
	fi

.PHONY: validate-data
validate-data: $(VALIDATION_SUCCESS_SENTINEL)

.PHONY: clean-validate
validate-clean:
	rm -rf $(VALIDATE_OUTPUT_DIR)

.PHONY: validate-debug
validate-debug:
	@:$(info $(DEBUG))
