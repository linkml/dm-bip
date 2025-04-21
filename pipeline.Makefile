RUN := poetry run

DM_INPUT_DIR ?= input
DM_INPUT_FILES ?=
DM_SCHEMA_NAME ?= Schema
DM_OUTPUT_DIR ?= output/$(DM_SCHEMA_NAME)

ifdef DM_INPUT_FILES
	INPUT_FILES := $(DM_INPUT_FILES)
else
	INPUT_FILES := $(shell find $(DM_INPUT_DIR) -type f -regex '.*\.[ct]sv' 2> /dev/null)
endif

INPUT_FILENAMES := $(INPUT_FILES:$(INPUT_DIR)/%=%)

SCHEMA_FILE := $(DM_OUTPUT_DIR)/schema-automator-data/$(DM_SCHEMA_NAME).yaml

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

    DM_INPUT_FILE=toy_data/initial/demographics.tsv make create_schema
endef

check_input_files = \
	$(if $(INPUT_FILES),,\
	$(info No input files detected. Debug information:)\
	$(info $(DEBUG))\
	$(error no input files detected))



# VALIDATE_TARGETS := $(addprefix validate-,$(basename $(notdir $(INPUT_FILENAMES))))

.PHONY: clean-schema
clean-schema:
	rm -rf $(DM_OUTPUT_DIR)

$(SCHEMA_FILE): $(INPUT_FILES)
	@:$(call check_input_files)
	mkdir -p $(@D)
	$(RUN) schemauto generalize-tsvs $^ -o $@
	@echo
	@echo "  Created schema at $@"
	@echo

.PHONY: debug-schema
debug-schema:
	@:$(info $(DEBUG))

help::
	@:$(info $(HELP))
	@:$(info )
	@:$(info Defined variables)
	@:$(info =================)
	@:$(info $(DEBUG))

.PHONY: ensure-input
ensure-input:
	@:$(call check_input_files)

.PHONY: create-schema
create-schema: $(SCHEMA_FILE)

.PHONY: lint-schema
lint-schema: $(SCHEMA_FILE)
	$(RUN) linkml-lint $<

# .PHONY: validate-schema
# validate: $(SCHEMA_FILE)
# 	$(RUN) linkml-validate -s $< -C $(INPUT_FILES)
