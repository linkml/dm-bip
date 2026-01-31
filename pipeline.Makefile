RUN := uv run

# DM-BIP PIPELINE
# ============
# The pipeline consists of these steps:
#   0. Prepare raw dbGaP files (New cleaning step)
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

# External config file support
# ============
# Use CONFIG=path/to/file.mk to load variables from an external file.
# The config file should set variables using make syntax (e.g., DM_INPUT_DIR = /path).
CONFIG ?=
-include $(CONFIG)

# Configurable parameters via environment variables
# ============
DM_INPUT_DIR   ?=
DM_INPUT_FILES ?=
DM_SCHEMA_NAME ?= Schema
DM_OUTPUT_DIR  ?= output/$(DM_SCHEMA_NAME)
DM_TRANS_SPEC_DIR ?=
DM_MAP_TARGET_SCHEMA ?=
DM_MAPPING_PREFIX ?=
DM_MAPPING_POSTFIX ?=
DM_MAP_OUTPUT_TYPE ?= yaml
DM_MAP_CHUNK_SIZE ?= 10000

# --- Raw Data Preparation Variables ---
# The raw directory containing .txt.gz files
DM_RAW_SOURCE ?=
# The directory containing the YAML mapping files for the study filtering
DM_MAPPING_SPEC ?= $(DM_TRANS_SPEC_DIR)

# Schema generation options
# ============
# Enum inference is controlled by both DM_ENUM_THRESHOLD and DM_MAX_ENUM_SIZE.
# To enable enum inference, set BOTH variables (e.g., DM_ENUM_THRESHOLD=0.1 and DM_MAX_ENUM_SIZE=50).
#
# DM_ENUM_THRESHOLD: ratio of distinct values to total rows for enum consideration.
#   Default 1.0 disables threshold-based enum creation (ratio cannot exceed 1.0).
#   Set to 0.1 (schema-automator default) to enable.
DM_ENUM_THRESHOLD ?= 1.0
# DM_MAX_ENUM_SIZE: maximum distinct values for a column to be considered an enum.
#   Default 0 disables size-based enum creation.
#   Set to 50 (schema-automator default) to enable.
DM_MAX_ENUM_SIZE ?= 0

# Derived output files
# ============
SCHEMA_FILE                 := $(DM_OUTPUT_DIR)/$(DM_SCHEMA_NAME).yaml
VALIDATE_OUTPUT_DIR         := $(DM_OUTPUT_DIR)/validation-logs
VALIDATED_FILES_LIST        := $(VALIDATE_OUTPUT_DIR)/input-files.txt
MAPPING_OUTPUT_DIR          := $(DM_OUTPUT_DIR)/mapped-data

# Logging files
# ============
SCHEMA_LINT_LOG             := $(VALIDATE_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-schema-lint.log
SCHEMA_VALIDATE_LOG         := $(VALIDATE_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-schema-validate.log
DATA_VALIDATE_LOG           := $(VALIDATE_OUTPUT_DIR)/$(DM_SCHEMA_NAME)-data-validate.log
DATA_VALIDATE_FILES_DIR     := $(VALIDATE_OUTPUT_DIR)/data-validation
DATA_VALIDATE_ERRORS_DIR    := $(VALIDATE_OUTPUT_DIR)/data-validation-errors

VALIDATION_SUCCESS_SENTINEL := $(VALIDATE_OUTPUT_DIR)/_data_validation_complete
MAPPING_SUCCESS_SENTINEL := $(MAPPING_OUTPUT_DIR)/_mapping_complete


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
  DM_SCHEMA_NAME     = $(DM_SCHEMA_NAME)
  DM_INPUT_DIR       = $(DM_INPUT_DIR)
  DM_INPUT_FILES     = $(DM_INPUT_FILES)
  DM_RAW_SOURCE      = $(DM_RAW_SOURCE)
  DM_OUTPUT_DIR      = $(DM_OUTPUT_DIR)
  DM_ENUM_THRESHOLD  = $(DM_ENUM_THRESHOLD)
  DM_MAX_ENUM_SIZE   = $(DM_MAX_ENUM_SIZE)

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
pipeline:
	@$(MAKE) prepare-input
	@$(MAKE) $(MAPPING_SUCCESS_SENTINEL)

.PHONY: pipeline-debug
pipeline-debug:
	@:$(info $(DEBUG))

# Preparation Step
# ============
.PHONY: prepare-input
prepare-input:
	@if [ -n "$(DM_RAW_SOURCE)" ]; then \
		echo "--- [0/3] Cleaning and standardizing raw dbGaP files ---"; \
		mkdir -p $(DM_INPUT_DIR); \
		$(RUN) python src/dm_bip/cleaners/prepare_input.py \
			--source $(DM_RAW_SOURCE) \
			--mapping $(DM_MAPPING_SPEC) \
			--output $(DM_INPUT_DIR) \
			--verbose; \
	else \
		echo "--- Skipping cleaning step (DM_RAW_SOURCE not set) ---"; \
	fi


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
	$(RUN) schemauto generalize-tsvs -n $(DM_SCHEMA_NAME) \
		--enum-threshold $(DM_ENUM_THRESHOLD) \
		--max-enum-size $(DM_MAX_ENUM_SIZE) \
		$^ -o $@
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

# Mapping (Transformation) Goals
# ==============================

MAP_TARGET_SCHEMA_FILE := $(DM_MAP_TARGET_SCHEMA)

MAP_TRANS_SPEC_FILES := $(shell find $(DM_TRANS_SPEC_DIR) -maxdepth 1 -type f -name '*.yaml' 2>/dev/null)

# Call this function in any recipe that depends on input files
check_map_input_files = \
    $(if $(wildcard $(MAP_TARGET_SCHEMA_FILE)),,\
        $(info Target schema file missing: $(MAP_TARGET_SCHEMA_FILE))\
        $(info $(DEBUG))\
        $(error No target schema file detected) \
    ) \
    $(if $(MAP_TRANS_SPEC_FILES),,\
        $(info No transformation spec files found in $(DM_TRANS_SPEC_DIR))\
        $(info $(DEBUG))\
        $(error No transformation spec files detected) \
    )

.PHONY: map-data
map-data: $(MAPPING_SUCCESS_SENTINEL)

$(MAPPING_SUCCESS_SENTINEL): $(SCHEMA_FILE) $(VALIDATION_SUCCESS_SENTINEL)
	@$(call check_map_input_files)
	@echo "Running LinkML-Map transformation..."
	@mkdir -p $(MAPPING_OUTPUT_DIR)
	$(RUN) python ./src/dm_bip/map_data/map_data.py \
		--source-schema $(SCHEMA_FILE) \
		--target-schema $(DM_MAP_TARGET_SCHEMA) \
		--data-dir $(DM_INPUT_DIR) \
		--var-dir $(DM_TRANS_SPEC_DIR) \
		--output-dir $(MAPPING_OUTPUT_DIR) \
		$(if $(DM_MAPPING_PREFIX),--output-prefix $(DM_MAPPING_PREFIX)) \
		$(if $(DM_MAPPING_POSTFIX),--output-postfix "$(DM_MAPPING_POSTFIX)") \
		--output-type $(DM_MAP_OUTPUT_TYPE) \
		--chunk-size $(DM_MAP_CHUNK_SIZE)
	@echo "✓ Data mapping complete. Output written to $(MAPPING_OUTPUT_DIR)"
	@touch $@

.PHONY: map-debug
map-debug:
	@echo "DM_TRANS_SPEC_DIR: $(DM_TRANS_SPEC_DIR)"
	@echo "DM_MAP_TARGET_SCHEMA: $(DM_MAP_TARGET_SCHEMA)"
	@echo "MAPPING_OUTPUT_DIR: $(MAPPING_OUTPUT_DIR)"

.PHONY: map-clean
map-clean:
	rm -rf $(MAPPING_OUTPUT_DIR)
