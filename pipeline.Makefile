RUN := poetry run

INPUT_DIR ?= input
OUTPUT_DIR ?= output
INPUT_FILES ?= $(shell find $(INPUT_DIR) -type f -regex '.*\.[ct]sv')
INPUT_FILENAMES := $(INPUT_FILES:$(INPUT_DIR)/%=%)

step_files = $(foreach filename,$(INPUT_FILENAMES),$(OUTPUT_DIR)/$(1)/$(filename))

STEP_0_NAME := 00-original
STEP_0_FILES := $(call step_files,$(STEP_0_NAME))

STEP_1_NAME := 01-cleaned
STEP_1_FILES := $(call step_files,$(STEP_1_NAME))

STEP_2_NAME := 02-schema-inferred
STEP_2_FILES := $(call step_files,$(STEP_2_NAME))

z:
	@echo input: $(INPUT_FILES)
	@echo
	@echo input names: $(INPUT_FILENAMES)
	@echo
	@echo step 0: $(STEP_0_FILES)
	@echo
	@echo step 1: $(STEP_1_FILES)
	@echo
	@echo step 2: $(STEP_2_FILES)

$(OUTPUT_DIR)/00-original/%: $(INPUT_DIR)/%
	cp $< $@

$(OUTPUT_DIR)/01-cleaned/%: $(OUTPUT_DIR)/0-original/%
	$(RUN) src/dm_bip/clean_data.py $< > $@

$(OUTPUT_DIR)/02-schema-inferred/%: $(OUTPUT_DIR)/1-cleaned/%
	$(RUN) schemauto generalize-csv $< -o $@
