RUN := poetry run


# Configurable parameters via environment variables
DM_INPUT_DIR ?=
DM_INPUT_FILES ?=
DM_SCHEMA_NAME ?= Schema
DM_OUTPUT_DIR ?= output/$(DM_SCHEMA_NAME)

# Derived output files
SCHEMA_FILE := $(DM_OUTPUT_DIR)/schema-automator-data/$(DM_SCHEMA_NAME).yaml


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

    DM_INPUT_FILES=toy_data/initial/demographics.tsv make create_schema
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
	$(RUN) schemauto generalize-tsvs $^ -o $@
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
	$(RUN) linkml-lint $<

.PHONY: help
.PHONY: schema-help
help::
schema-help:
	@:$(info $(HELP))
	@:$(info )
	@:$(info Defined variables)
	@:$(info =================)
	@:$(info $(DEBUG))


# .PHONY: validate-schema
# validate: $(SCHEMA_FILE)
# 	$(RUN) linkml-validate -s $< -C $(INPUT_FILES)
