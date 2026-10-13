"""Generated datamodel for the BDC variable library schema, and which class each variable kind takes."""

from bdc_varlib.pipeline.classify import VariableKind

from dm_bip.variable_lib.datamodel.variable_lib import SingleCategoricalVariable, SingleContinuousVariable

#: The entry class ``bdc_varlib.pipeline.emit.to_entries`` instantiates for each kind.
ENTRY_CLASSES = {
    VariableKind.continuous: SingleContinuousVariable,
    VariableKind.categorical: SingleCategoricalVariable,
}
