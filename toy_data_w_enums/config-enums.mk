DM_RAW_SOURCE        := toy_data_w_enums/data/raw
DM_SCHEMA_NAME       := ToyEnums
DM_OUTPUT_DIR        := $(or $(TOY_OUTPUT_DIR),output/ToyEnums/enums)
DM_INPUT_DIR         := $(DM_OUTPUT_DIR)/prepared
DM_TRANS_SPEC_DIR    := toy_data_w_enums/specs/with_enum_derivations
DM_MAPPING_SPEC      := $(DM_TRANS_SPEC_DIR)
DM_MAP_TARGET_SCHEMA := toy_data_w_enums/target-schema-enums.yaml
DM_MAPPING_PREFIX    := TOY
DM_MAPPING_POSTFIX   := -data
DM_MAP_STRICT        := false

# Enum inference
DM_ENUM_THRESHOLD           := 0.1
DM_MAX_ENUM_SIZE            := 50
DM_INFER_ENUM_FROM_INTEGERS := true
