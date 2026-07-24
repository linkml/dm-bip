DM_RAW_SOURCE        := toy_data/data/raw
DM_SCHEMA_NAME       := ToyFromRaw
DM_OUTPUT_DIR        := $(or $(TOY_OUTPUT_DIR),output/ToyFromRaw)
DM_INPUT_DIR         := $(DM_OUTPUT_DIR)/prepared
DM_TRANS_SPEC_DIR    := toy_data/from_raw/specs
DM_MAPPING_SPEC      := $(DM_TRANS_SPEC_DIR)
DM_MAP_TARGET_SCHEMA := toy_data/target-schema.yaml
DM_MAPPING_PREFIX    := TOY
DM_MAPPING_POSTFIX   := -data
DM_MAP_STRICT        := false

# Allow narrow enum inference (≤3 unique values per column) so the
# SEX_CODE string column on pht000001 gets typed as a source enum and
# enum_derivations in demography.yaml can derive sex_derived from it.
# Threshold is tight on purpose: other low-cardinality string columns
# (e.g., SMOKING with 5 distinct values) stay non-enum so existing
# value_mappings on those slots keep working as the comparison baseline.
DM_MAX_ENUM_SIZE := 3
