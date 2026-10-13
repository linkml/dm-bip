from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.11.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'variable_lib_schema',
     'default_range': 'string',
     'description': 'Generation shim for the BDC variable library datamodel. '
                    'dm-bip emits SingleContinuousVariable and '
                    'SingleCategoricalVariable instances defined upstream; this '
                    'schema adds nothing of its own, it exists only because '
                    'gen-pydantic takes a local file rather than a URL. Any '
                    'dm-bip-specific additions belong here rather than in a '
                    'vendored copy of the upstream schema.',
     'id': 'https://w3id.org/dm-bip/variable-lib-schema',
     'imports': ['linkml:types',
                 'https://raw.githubusercontent.com/linkml/bdc-variable-library/main/src/bdc_variable_library/schema/bdc_variable_library'],
     'license': 'MIT',
     'name': 'variable_lib_schema',
     'prefixes': {'bdchm': {'prefix_prefix': 'bdchm',
                            'prefix_reference': 'https://w3id.org/bdchm/'},
                  'dbgap': {'prefix_prefix': 'dbgap',
                            'prefix_reference': 'https://identifiers.org/dbgap/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'variable_lib_schema': {'prefix_prefix': 'variable_lib_schema',
                                          'prefix_reference': 'https://w3id.org/dm-bip/variable-lib-schema/'}},
     'see_also': ['https://github.com/linkml/bdc-variable-library'],
     'source_file': 'src/dm_bip/variable_lib/schema/variable_lib_schema.yaml',
     'title': 'DM-BIP Variable Library Schema'} )

class ComparatorEnum(str, Enum):
    """
    Comparator for quantity values
    """
    lt = "lt"
    """
    Less than
    """
    le = "le"
    """
    Less than or equal to
    """
    ge = "ge"
    """
    Greater than or equal to
    """
    gt = "gt"
    """
    Greater than
    """


class HistoricalStatusEnum(str, Enum):
    """
    Indicates whether something is present, absent, historical, or its status is unknown.
    """
    present = "present"
    """
    Was present in the patient at observation time.
    """
    absent = "absent"
    """
    Was absent in the patient at observation time.
    """
    unknown = "unknown"
    """
    Was of unknown status in the patient at observation time.
    """
    historical = "historical"
    """
    Was present in the patient historically.
    """


class ProvenanceEnum(str, Enum):
    """
    A set of values indicating the source or origin of a clinical record.
    """
    ehr_billing_diagnosis = "ehr_billing_diagnosis"
    """
    Diagnosis from EHR billing.
    """
    ehr_chief_complaint = "ehr_chief_complaint"
    """
    Chief complaint from EHR.
    """
    ehr_encounter_diagnosis = "ehr_encounter_diagnosis"
    """
    Encounter diagnosis from EHR.
    """
    ehr_episode_entry = "ehr_episode_entry"
    """
    Episode entry from EHR.
    """
    ehr_problem_list_entry = "ehr_problem_list_entry"
    """
    Problem list entry from EHR.
    """
    first_position_condition = "first_position_condition"
    """
    First position condition.
    """
    primary_condition = "primary_condition"
    """
    Primary condition.
    """
    secondary_condition = "secondary_condition"
    """
    Secondary condition.
    """
    nlp_derived = "nlp_derived"
    """
    Derived from natural language processing.
    """
    observation_recorded_from_ehr = "observation_recorded_from_ehr"
    """
    Observation recorded from EHR.
    """
    patient_self_reported_condition = "patient_self_reported_condition"
    """
    Patient self-reported condition.
    """
    referral_record = "referral_record"
    """
    From referral record.
    """
    tumor_registry = "tumor_registry"
    """
    From tumor registry.
    """
    working_diagnosis = "working_diagnosis"
    """
    Working diagnosis.
    """
    clinical_diagnosis = "clinical_diagnosis"
    """
    Clinical diagnosis.
    """


class ConditionSeverityEnum(str, Enum):
    """
    A subjective assessment of the severity of a condition.
    """
    mild = "mild"
    """
    Lower intensity condition.
    """
    moderate = "moderate"
    """
    Medium intensity condition.
    """
    severe = "severe"
    """
    Higher intensity condition.
    """


class FamilyRelationshipEnum(str, Enum):
    """
    Values describing kinship connections between individuals.
    """
    oneself = "oneself"
    """
    Self-reference.
    """
    natural_parent = "natural_parent"
    """
    Mother or father unspecified.
    """
    natural_father = "natural_father"
    """
    Biological father.
    """
    natural_mother = "natural_mother"
    """
    Biological mother.
    """
    natural_sibling = "natural_sibling"
    """
    Sister or brother unspecified.
    """
    natural_brother = "natural_brother"
    """
    Biological brother.
    """
    natural_sister = "natural_sister"
    """
    Biological sister.
    """
    natural_child = "natural_child"
    """
    Biological offspring.
    """
    blood_relative = "blood_relative"
    """
    Generic consanguineous relation.
    """


class RouteAdminEnum(str, Enum):
    """
    Routes of drug administration
    """
    oral = "oral"
    """
    Oral administration
    """
    intravenous = "intravenous"
    """
    Intravenous administration
    """
    intramuscular = "intramuscular"
    """
    Intramuscular administration
    """
    subcutaneous = "subcutaneous"
    """
    Subcutaneous administration
    """
    intradermal = "intradermal"
    """
    Intradermal administration
    """
    transdermal = "transdermal"
    """
    Transdermal administration
    """
    rectal = "rectal"
    """
    Rectal administration
    """
    vaginal = "vaginal"
    """
    Vaginal administration
    """
    nasal = "nasal"
    """
    Nasal administration
    """
    topical = "topical"
    """
    Topical administration
    """
    sublingual = "sublingual"
    """
    Sublingual administration
    """
    buccal = "buccal"
    """
    Buccal administration
    """
    intra_articular = "intra_articular"
    """
    Intra-articular administration
    """
    intraperitoneal = "intraperitoneal"
    """
    Intraperitoneal administration
    """
    intrathecal = "intrathecal"
    """
    Intrathecal administration
    """
    epidural = "epidural"
    """
    Epidural administration
    """
    intra_arterial = "intra_arterial"
    """
    Intra-arterial administration
    """
    ophthalmic = "ophthalmic"
    """
    Ophthalmic administration
    """
    otic = "otic"
    """
    Otic (ear) administration
    """
    enteral = "enteral"
    """
    Enteral administration
    """
    percutaneous = "percutaneous"
    """
    Percutaneous administration
    """


class DataTypeEnum(str, Enum):
    """
    The data type of an observation value
    """
    decimal = "decimal"
    """
    Decimal number
    """
    integer = "integer"
    """
    Integer number
    """
    enum = "enum"
    """
    Enumerated value
    """
    boolean = "boolean"
    """
    Boolean value
    """
    string = "string"
    """
    String value
    """
    numeric = "numeric"
    """
    decimal or integer - from dbGAP data types
    """
    code = "code"
    """
    data are a list of acceptable values or a controlled vocabulary, from dbGAP data types, same as enum
    """
    uriorcurie = "uriorcurie"
    """
    A URI or CURIE value
    """


class MethodEnum(str, Enum):
    """
    The method used for a measurement or observation
    """
    anthropometry = "anthropometry"
    """
    physical measurement of the human body, including height, weight, and other body dimensions
    """
    survey = "survey"
    """
    list of questions given to a participant for data collection purposes - the survey is filled out by the participant independently
    """
    interview = "interview"
    """
    series of questions posed to a participant by an interviewer for data collection purposes
    """
    calculated = "calculated"
    """
    clinical record that results from a calculation rather than being directly measured
    """
    spirometry = "spirometry"
    """
    breathing test used to assess lung function
    """
    body_plesmography = "body_plesmography"
    """
    precise pulmonary function test where the patient sits in a sealed chamber and breathes into a specialized mouthpiece. This method uses Boyle's Law  and is considered a "gold standard"
    """
    gli = "gli"
    """
    a standard reference range and calculator for spirometry and lung function tests published by the Global Lung Function Initiative in 2012
    """
    gli_global = "gli_global"
    """
    a standard reference range and calculator for spirometry and lung function tests published by the Global Lung Function Initiative in 2022. This is an update of the 2012 standard that is more ethnically diverse
    """
    nhanesiii = "nhanesiii"
    """
    standard reference equations for spirometry published in 2005
    """


class InstrumentEnum(str, Enum):
    """
    The instrument used for a measurement
    """
    wall_mounted_stadiometer = "wall_mounted_stadiometer"
    """
    fixed, high-precision medical device used to measure human height, consisting of a vertical measuring rod or tape fastened to a wall with a sliding headpiece
    """
    flexible_measuring_tape = "flexible_measuring_tape"
    """
    flexible tape used to measure height or body circumference
    """
    portable_stadiometer = "portable_stadiometer"
    """
    portable device used to measure height, typically used in field settings
    """
    anthropometer_rod = "anthropometer_rod"
    """
    rigid rod-based instrument used to measure body dimensions including height
    """
    sonar_stadiometer = "sonar_stadiometer"
    """
    ultrasound-based device used to measure height without contact
    """
    mechanical_beam_balance_scale = "mechanical_beam_balance_scale"
    """
    medical device used to measure human weight
    """
    digital_scale = "digital_scale"
    """
    electronic device used to measure human weight using strain gauge sensors
    """
    spring_scale = "spring_scale"
    """
    mechanical device that measures weight by the displacement of a spring
    """
    spirometer = "spirometer"
    """
    medical device that measures lung function by recording the amount and speed of air a person can inhale and exhale
    """
    vitalograph = "vitalograph"
    """
    a portable medical device that measures lung function by recording the amount and speed of air a person can inhale and exhale
    """
    body_plesmograph = "body_plesmograph"
    """
    sealed, clear chamber with a mouthpiece for a person to breath through
    """
    peak_flow_meter = "peak_flow_meter"
    """
    portable, handheld device used to measure how fast and hard a person can exhale
    """


class ReagentKitEnum(str, Enum):
    """
    The reagent kit used for a measurement
    """
    placeholder = "placeholder"
    """
    Placeholder value
    """


class BodyPositionEnum(str, Enum):
    """
    The body position during a measurement
    """
    supine = "supine"
    """
    Lying face up
    """
    standing = "standing"
    """
    Standing upright
    """
    sitting = "sitting"
    """
    Seated position
    """


class ContextEnum(str, Enum):
    """
    The context in which a measurement was taken
    """
    fasted_8_hrs = "fasted_8_hrs"
    """
    Fasted for 8 hours
    """
    fasted_12_hrs = "fasted_12_hrs"
    """
    Fasted for 12 hours
    """
    before_bronchodilator = "before_bronchodilator"
    """
    Before bronchodilator administration
    """
    after_bronchodilator = "after_bronchodilator"
    """
    After bronchodilator administration
    """
    taking_lipid_lowering_medications = "taking_lipid_lowering_medications"
    """
    While taking lipid-lowering medications
    """
    before_physical_activity = "before_physical_activity"
    """
    Before physical activity
    """
    during_physical_activity = "during_physical_activity"
    """
    During physical activity
    """
    after_physical_activity = "after_physical_activity"
    """
    After physical activity
    """
    during_procedure = "during_procedure"
    """
    During a procedure
    """
    taking_diabetes_medication = "taking_diabetes_medication"
    """
    While taking diabetes medication
    """
    lowest = "lowest"
    """
    Lowest recorded value
    """


class CollectedByEnum(str, Enum):
    """
    Who collected the measurement
    """
    doctor = "doctor"
    """
    Collected by a doctor
    """
    nurse = "nurse"
    """
    Collected by a nurse
    """
    technician = "technician"
    """
    Collected by a technician
    """
    self_administered = "self_administered"
    """
    Self-administered by the patient
    """
    first_examiner = "first_examiner"
    """
    Collected by the first examiner
    """
    second_examiner = "second_examiner"
    """
    Collected by the second examiner
    """


class AssociatedEvidenceEnum(str, Enum):
    """
    The method used for diagnosis
    """
    placeholder = "placeholder"
    """
    Placeholder value
    """


class ActivityTypeEnum(str, Enum):
    """
    Type of activity being recorded
    """
    fasting = "fasting"
    bronchodilator_medication_use = "bronchodilator_medication_use"
    diabetes_medication_use = "diabetes_medication_use"
    antihyperlipidemics_medication_use = "antihyperlipidemics_medication_use"
    physical_activity = "physical_activity"
    medical_procedure = "medical_procedure"


class RelativeTimingEnum(str, Enum):
    """
    Set of values describing the relative timing of an activity
    """
    after = "after"
    before = "before"
    during = "during"


class DynamicAsthmaEnum(str):
    """
    Asthma and asthma-related terms from Mondo and HPO
    """
    pass


class DynamicHeartFailureEnum(str):
    """
    Heart failure and related terms from Mondo
    """
    pass


class DynamicObesityEnum(str):
    """
    Obesity and related terms from HPO
    """
    pass


class BdchmTypeEnum(str, Enum):
    """
    A list of BDCHM entities used to describe variables
    """
    observation = "observation"
    condition = "condition"
    procedure = "procedure"
    exposure = "exposure"
    drugexposure = "drugexposure"


class ClinicalMicroschemaEnum(str, Enum):
    """
    A list of slots describing clinical data in microschema
    """
    subject_identifier = "subject_identifier"
    measurement_type = "measurement_type"
    measurement_value = "measurement_value"
    unit = "unit"
    method = "method"
    instrument = "instrument"
    reagent_kit = "reagent_kit"
    calculated_from = "calculated_from"
    body_location = "body_location"
    body_position = "body_position"
    context = "context"
    collected_by = "collected_by"
    data_type = "data_type"
    age_at_measurement = "age_at_measurement"
    study_site = "study_site"
    absolute_time = "absolute_time"
    condition_type = "condition_type"
    associated_evidence = "associated_evidence"
    age_at_condition_start = "age_at_condition_start"
    age_at_condition_end = "age_at_condition_end"
    age_at_condition_record = "age_at_condition_record"
    condition_status = "condition_status"
    condition_provenance = "condition_provenance"
    condition_concept = "condition_concept"
    condition_severity = "condition_severity"
    relationship_to_participant = "relationship_to_participant"
    method_type = "method_type"
    drug_concept = "drug_concept"
    exposure_status = "exposure_status"
    exposure_provenance = "exposure_provenance"
    age_at_exposure_record = "age_at_exposure_record"



class MicroschemaDefinition(ConfiguredBaseModel):
    """
    A metaclass for classes that conform to the Microschema profile. Classes that instantiate this are designed for inline composition.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'annotations': {'must_be_inlined': {'tag': 'must_be_inlined', 'value': True},
                         'must_not_have_id_slot': {'tag': 'must_not_have_id_slot',
                                                   'value': True}},
         'comments': ['Classes instantiating this SHOULD NOT have identifier slots',
                      'Classes instantiating this SHOULD be used with inlined=true',
                      'Classes instantiating this MAY compose other microschemas via '
                      'attributes'],
         'from_schema': 'https://w3id.org/linkml/linkml-microschema-profile'})

    profile_version: Optional[str] = Field(default=None, description="""Version of microschema profile this conforms to""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })
    domain_of_use: Optional[list[str]] = Field(default=None, description="""Domains where this microschema is applicable""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })
    subject: str = Field(default=..., description="""Entity being measured, observed, or interviewed - person, animal, specimen, or environmental material""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })
    observation_type: str = Field(default=..., description="""Question being asked, measurement being taken, quality being observed""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })
    location: str = Field(default=..., description="""Spatial metadata specifying where the observation was made - geolocation, place name, site id, environment, or biome""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })
    temporality: str = Field(default=..., description="""Temporal metadata specifying when an observation was made. This can be relative or absolute - datetime, age of person, season, or geologic era""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })
    methodology: str = Field(default=..., description="""Information about how an observation was made - method, instrument, reagent kit, statistical modifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })
    observation_result: ValueMicroschemaDefinition = Field(default=..., description="""The outcome of the observation type - answer, value, result, determination""", json_schema_extra = { "linkml_meta": {'domain_of': ['MicroschemaDefinition']} })


class ValueMicroschemaDefinition(ConfiguredBaseModel):
    """
    A microschema representing a typed value with optional unit/system. Examples: Quantity, Timepoint, CodedValue, Range. This is the range for observation result
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'annotations': {'must_be_inlined': {'tag': 'must_be_inlined', 'value': True},
                         'must_not_have_id_slot': {'tag': 'must_not_have_id_slot',
                                                   'value': True}},
         'comments': ['Classes instantiating this SHOULD NOT have identifier slots',
                      'Classes instantiating this SHOULD be used with inlined=true',
                      'Classes instantiating this MAY compose other microschemas via '
                      'attributes'],
         'from_schema': 'https://w3id.org/linkml/linkml-microschema-profile'})

    pass


class Quantity(ConfiguredBaseModel):
    """
    A numerical value with unit
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/linkml-microschema-profile',
         'instantiates': ['ValueMicroschemaDefinition']})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class Timepoint(ConfiguredBaseModel):
    """
    A point in time, potentially relative
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/linkml-microschema-profile',
         'instantiates': ['ValueMicroschemaDefinition']})

    datetime: Optional[datetime ] = Field(default=None, description="""Absolute timestamp""", json_schema_extra = { "linkml_meta": {'domain_of': ['Timepoint']} })
    relative_to_event: Optional[str] = Field(default=None, description="""Event this is relative to""", json_schema_extra = { "linkml_meta": {'domain_of': ['Timepoint']} })
    offset: Optional[Quantity] = Field(default=None, description="""Offset from event (e.g., \"+3 days\")""", json_schema_extra = { "linkml_meta": {'domain_of': ['Timepoint']} })
    subject_age: Optional[Quantity] = Field(default=None, description="""Age of the subject at this timepoint (e.g., age when the event occurred)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Timepoint']} })


class TimeInterval(ConfiguredBaseModel):
    """
    A period between two timepoints
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/linkml-microschema-profile',
         'instantiates': ['ValueMicroschemaDefinition']})

    interval_start: Optional[Timepoint] = Field(default=None, description="""Start of the interval""", json_schema_extra = { "linkml_meta": {'domain_of': ['TimeInterval']} })
    interval_end: Optional[Timepoint] = Field(default=None, description="""End of the interval""", json_schema_extra = { "linkml_meta": {'domain_of': ['TimeInterval']} })
    duration: Optional[Quantity] = Field(default=None, description="""Duration as alternative to start/end""", json_schema_extra = { "linkml_meta": {'domain_of': ['TimeInterval']} })


class CodedValue(ConfiguredBaseModel):
    """
    A value from a controlled vocabulary
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/linkml-microschema-profile',
         'instantiates': ['ValueMicroschemaDefinition']})

    code: str = Field(default=..., description="""The code value as a CURIE""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodedValue']} })
    code_label: Optional[str] = Field(default=None, description="""Human-readable label for the code""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodedValue']} })
    code_system: Optional[str] = Field(default=None, description="""The code system URI""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodedValue']} })


class ClinicalMeasurementRecord(ConfiguredBaseModel):
    """
    A data structure with key and value attributes that represents a single observation. This can include results of clinical labs, scores and indices, socioeconomic, or behavioral observations.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'domain_of_use': {'tag': 'domain_of_use',
                                           'value': 'clinical'}},
         'class_uri': 'bdchm:Observation',
         'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'instantiates': ['MicroschemaDefinition'],
         'slot_usage': {'age_at_measurement': {'name': 'age_at_measurement',
                                               'required': True},
                        'measurement_type': {'name': 'measurement_type',
                                             'required': True},
                        'measurement_value': {'name': 'measurement_value',
                                              'required': True},
                        'subject_identifier': {'name': 'subject_identifier',
                                               'required': True}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: Quantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class ConditionStatusRecord(ConfiguredBaseModel):
    """
    Record suggesting the presence of a disease or medical condition stated as a diagnosis, sign, or symptom
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'domain_of_use': {'tag': 'domain_of_use',
                                           'value': 'clinical'}},
         'class_uri': 'bdchm:Condition',
         'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'instantiates': ['MicroschemaDefinition'],
         'slot_usage': {'age_at_condition_record': {'name': 'age_at_condition_record',
                                                    'required': True},
                        'condition_status': {'name': 'condition_status',
                                             'required': True},
                        'condition_type': {'name': 'condition_type', 'required': True},
                        'relationship_to_participant': {'name': 'relationship_to_participant',
                                                        'required': True},
                        'subject_identifier': {'name': 'subject_identifier',
                                               'required': True}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    condition_type: str = Field(default=..., description="""A CURIE from MONDO or HPO""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord'], 'slot_uri': 'bdchm:condition_concept'} })
    associated_evidence: Optional[AssociatedEvidenceEnum] = Field(default=None, description="""The method used for diagnosis""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    age_at_condition_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_record: Quantity = Field(default=..., description="""Age of participant when record of the condition was collected. This  slot can accommodate an \"age at encounter\" where a medical history was  collected, or a record was adjudicated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_status: HistoricalStatusEnum = Field(default=..., description="""A value indicating whether the medical condition described in this record is present, absent, historically present, or unknown for this individual patient.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_provenance: Optional[ProvenanceEnum] = Field(default=None, description="""A value representing the provenance of the Condition record.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_severity: Optional[ConditionSeverityEnum] = Field(default=None, description="""A subjective assessment of the severity of the condition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    relationship_to_participant: FamilyRelationshipEnum = Field(default=..., description="""A value indicating the relationship between the Participant to which the Condition is attributed and the individual who had the reported Condition. If the Condition is affecting the participant themselves, then 'Self' is the appropriate relationship.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })


class DrugStatusRecord(ConfiguredBaseModel):
    """
    Record suggesting exposure to a medication
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'domain_of_use': {'tag': 'domain_of_use',
                                           'value': 'clinical'}},
         'class_uri': 'bdchm:DrugExposure',
         'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'instantiates': ['MicroschemaDefinition'],
         'slot_usage': {'age_at_drug_record': {'name': 'age_at_drug_record',
                                               'required': True},
                        'drug_type': {'name': 'drug_type', 'required': True},
                        'subject_identifier': {'name': 'subject_identifier',
                                               'required': True}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    drug_type: str = Field(default=..., description="""A CURIE from RxNorm""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord'], 'slot_uri': 'bdchm:drug_concept'} })
    age_at_drug_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_record: Quantity = Field(default=..., description="""Age of participant when record of the drug was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medication list. """, json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    route_of_administration: Optional[RouteAdminEnum] = Field(default=None, description="""Routes of drug administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    dose: Optional[Quantity] = Field(default=None, description="""Amount of drug per administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    frequency: Optional[Quantity] = Field(default=None, description="""How often e.g. 2 per day""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    indication: Optional[str] = Field(default=None, description="""Condition/reason for drug (SNOMED, ICD, Mondo, HPO, etc)""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })


class ProcedureStatusRecord(ConfiguredBaseModel):
    """
    Record of activity or process ordered by or carried out by a healthcare provider for a diagnostic or therapeutic reason
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'domain_of_use': {'tag': 'domain_of_use',
                                           'value': 'clinical'}},
         'class_uri': 'bdchm:Procedure',
         'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'instantiates': ['MicroschemaDefinition'],
         'slot_usage': {'age_at_procedure_record': {'name': 'age_at_procedure_record',
                                                    'required': True},
                        'procedure_type': {'name': 'procedure_type', 'required': True},
                        'subject_identifier': {'name': 'subject_identifier',
                                               'required': True}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    procedure_type: str = Field(default=..., description="""A CURIE from OMOP""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord'], 'slot_uri': 'bdchm:procedure_concept'} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    age_at_procedure_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_record: Quantity = Field(default=..., description="""Age of participant when record of the procedure was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medical history.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })


class HumanBodyHeightRecord(ClinicalMeasurementRecord):
    """
    Measurement of linear distance of a human body from the bottom of a flat foot to the top-most point of the head
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'instrument': {'any_of': [{'equals_string': 'wall_mounted_stadiometer'},
                                                                                     {'equals_string': 'flexible_measuring_tape'},
                                                                                     {'equals_string': 'portable_stadiometer'},
                                                                                     {'equals_string': 'anthropometer_rod'},
                                                                                     {'equals_string': 'sonar_stadiometer'},
                                                                                     {'equals_string': 'infantometer'}],
                                                                          'name': 'instrument'},
                                                           'method': {'any_of': [{'equals_string': 'anthropometry'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': 'cm'},
                                                                               {'equals_string': '[in_i]'},
                                                                               {'equals_string': 'm'},
                                                                               {'equals_string': '[ft_i]'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OBA:VT0001253'},
                                                                                          {'equals_string': 'OMOP:903133'},
                                                                                          {'equals_string': 'LOINC:3036277'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyHeightQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyHeightQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyHeightRecord001(HumanBodyHeightRecord):
    """
    Measurement of linear distance of a standing human body from the bottom of a flat foot to the top-most point of the head measured in centimeters with a wall-mounted stadiometer
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'wall_mounted_stadiometer'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': 'cm'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyHeightQuantity001'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyHeightQuantity001 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyHeightRecord002(HumanBodyHeightRecord):
    """
    Measurement of linear distance of a standing human body from the bottom of a flat foot to the top-most point of the head measured in inches with a wall-mounted stadiometer
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'wall_mounted_stadiometer'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': '[in_i]'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyHeightQuantity002'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyHeightQuantity002 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyHeightRecord003(HumanBodyHeightRecord):
    """
    Measurement of linear distance of a standing human body from the bottom of a flat foot to the top-most point of the head measured in inches with a portable stadiometer
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'portable_stadiometer'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': '[in_i]'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyHeightQuantity002'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyHeightQuantity002 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyHeightRecord004(HumanBodyHeightRecord):
    """
    Measurement of linear distance of a standing human body from the bottom of a flat foot to the top-most point of the head measured in centimeters with an  anthropometer
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'anthropometer_rod'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': 'cm'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyHeightQuantity003'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyHeightQuantity003 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyHeightRecord005(HumanBodyHeightRecord):
    """
    Measurement of linear distance of a standing human body from the bottom of a flat foot to the top-most point of the head measured in feet with a wall-mounted stadiometer
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'wall_mounted_stadiometer'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': '[ft_i]'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyHeightQuantity004'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyHeightQuantity004 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyHeightRecord006(HumanBodyHeightRecord):
    """
    Measurement of linear distance of a human body from the bottom of a flat foot to the top-most point of the head in cm
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'unit': {'equals_string': 'cm',
                                                                    'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyHeightQuantity003'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyHeightQuantity003 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyWeightRecord(ClinicalMeasurementRecord):
    """
    Measurement of the force exerted by a human body on a scale due to gravity
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'instrument': {'any_of': [{'equals_string': 'mechanical_beam_balance_scale'},
                                                                                     {'equals_string': 'digital_scale'},
                                                                                     {'equals_string': 'spring_scale'},
                                                                                     {'equals_string': 'bariatric_scale'},
                                                                                     {'equals_string': 'body_composition_analyzer'}],
                                                                          'name': 'instrument'},
                                                           'method': {'any_of': [{'equals_string': 'anthropometry'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': 'kg'},
                                                                               {'equals_string': '[lb_av]'},
                                                                               {'equals_string': 'g'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OBA:VT0001259'},
                                                                                          {'equals_string': 'OMOP:903121'},
                                                                                          {'equals_string': 'LOINC:29463-7'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyWeightQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyWeightQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyWeightRecord001(HumanBodyWeightRecord):
    """
    Measurement of the force exerted by a human body on a mechanical beam balance due to gravity
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'mechanical_beam_balance_scale'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': 'kg'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyWeightQuantity001'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyWeightQuantity001 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyWeightRecord002(HumanBodyWeightRecord):
    """
    Measurement of the force exerted by a human body on a mechanical beam balance due to gravity
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'mechanical_beam_balance_scale'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': '[lb_av]'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyWeightQuantity002'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyWeightQuantity002 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyWeightRecord003(HumanBodyWeightRecord):
    """
    Measurement of the force exerted by a human body on a body composition analyzer due to gravity
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'standing'}],
                                                                             'name': 'body_position'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'body_composition_analyzer'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': 'kg'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBodyWeightQuantity003'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBodyWeightQuantity003 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class BodyMassIndexRecord(ClinicalMeasurementRecord):
    """
    A calculated numerical quantity representing an individual's weight-to-height ratio. BMI is calculated as weight (kg) divided by height (m) squared. The height is measured in cm and the weight is collected in kg.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'method': {'any_of': [{'equals_string': 'calculated'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': 'kg/m2'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OBA:0002045455'},
                                                                                          {'equals_string': 'OMOP:3038553'},
                                                                                          {'equals_string': 'LOINC:39156-5'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'BodyMassIndexQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: BodyMassIndexQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class BodyMassIndexRecord001(BodyMassIndexRecord):
    """
    A calculated numerical quantity representing an individual's weight-to-height ratio. BMI is calculated as weight (kg) divided by height (m) squared. The height is measured in cm and the weight is collected in kg.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'calculated_from': {'equals_expression': '{HumanBodyWeightRecord001} '
                                                                 '/ '
                                                                 '({HumanBodyHeightRecord001} '
                                                                 '/ 100)^2',
                                            'name': 'calculated_from'},
                        'measurement_value': {'name': 'measurement_value',
                                              'range': 'BodyMassIndexQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: BodyMassIndexQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'equals_expression': '{HumanBodyWeightRecord001} / '
                              '({HumanBodyHeightRecord001} / 100)^2'} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class BodyMassIndexRecord002(BodyMassIndexRecord):
    """
    A calculated numerical quantity representing an individual's weight-to-height ratio. BMI is calculated as weight (kg) divided by height (m) squared. The height is measured in inches and the weight is collected in lbs.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'calculated_from': {'equals_expression': '({HumanBodyWeightRecord002} '
                                                                 '/ 2.2) / '
                                                                 '({HumanBodyHeightRecord003} '
                                                                 '/ 39.37)^2',
                                            'name': 'calculated_from'},
                        'measurement_value': {'name': 'measurement_value',
                                              'range': 'BodyMassIndexQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: BodyMassIndexQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'equals_expression': '({HumanBodyWeightRecord002} / 2.2) / '
                              '({HumanBodyHeightRecord003} / 39.37)^2'} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanMeasuredFvcRecord(ClinicalMeasurementRecord):
    """
    Total amount of air a person can forcibly exhale after taking the deepest breath possible
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'context': {'any_of': [{'equals_string': 'before_bronchodilator'},
                                                                                  {'equals_string': 'after_bronchodilator'}],
                                                                       'name': 'context'},
                                                           'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'instrument': {'any_of': [{'equals_string': 'spirometer'},
                                                                                     {'equals_string': 'vitalograph'},
                                                                                     {'equals_string': 'body_plesmograph'}],
                                                                          'name': 'instrument'},
                                                           'method': {'any_of': [{'equals_string': 'spirometry'},
                                                                                 {'equals_string': 'body_plesmography'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': 'L'},
                                                                               {'equals_string': 'mL'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OMOP:4176265'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanMeasuredFvcQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanMeasuredFvcQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanMeasuredFvcRecord001(HumanMeasuredFvcRecord):
    """
    Total amount of air a person can forcibly exhale after taking the deepest breath possible
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'equals_string': 'sitting'}],
                                                                             'name': 'body_position'},
                                                           'context': {'any_of': [{'equals_string': 'before_bronchodilator'},
                                                                                  {'equals_string': 'after_bronchodilator'}],
                                                                       'name': 'context'},
                                                           'method': {'any_of': [{'equals_string': 'spirometry'}],
                                                                      'name': 'method'}}},
                    'preconditions': {'slot_conditions': {'instrument': {'any_of': [{'equals_string': 'spirometer'}],
                                                                         'name': 'instrument'},
                                                          'unit': {'any_of': [{'equals_string': 'L'}],
                                                                   'name': 'unit'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanMeasuredFvcQuantity001'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanMeasuredFvcQuantity001 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanPredictedFvcRecord(ClinicalMeasurementRecord):
    """
    Predicted total amount of air a person can forcibly exhale after taking the deepest breath possible. Predictions are based on a reference equation.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'instrument': {'any_of': [{'equals_string': 'GLI'},
                                                                                     {'equals_string': 'GLI-Global'},
                                                                                     {'equals_string': 'NHANESIII'}],
                                                                          'name': 'instrument'},
                                                           'method': {'any_of': [{'equals_string': 'calculated'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': 'L'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OMOP:4150403'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanPredictedFvcQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanPredictedFvcQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanPercentPredictedFvcRecord(ClinicalMeasurementRecord):
    """
    Percent of the predicted FVC that is achieved by the patient
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'calculated_from': {'equals_expression': '({HumanMeasuredFvcRecord001} '
                                                                                                    '/ '
                                                                                                    '{HumanPredictedFvcRecord}) '
                                                                                                    '* '
                                                                                                    '100',
                                                                               'name': 'calculated_from'},
                                                           'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'unit': {'any_of': [{'equals_string': '%'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OMOP:4253179'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanPercentPredictedFvcQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanPercentPredictedFvcQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanFev1Record(ClinicalMeasurementRecord):
    """
    Maximum amount of air a person can forcibly exhale in the first second of a breathing test
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'body_position': {'any_of': [{'range': 'BodyPositionEnum'}],
                                                                             'name': 'body_position'},
                                                           'context': {'any_of': [{'equals_string': 'before_bronchodilator'},
                                                                                  {'equals_string': 'after_bronchodilator'}],
                                                                       'name': 'context'},
                                                           'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'instrument': {'any_of': [{'equals_string': 'spirometer'},
                                                                                     {'equals_string': 'peak_flow_meter'}],
                                                                          'name': 'instrument'},
                                                           'method': {'any_of': [{'equals_string': 'spirometry'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': 'L'},
                                                                               {'equals_string': 'mL'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OMOP:4241837'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanFev1Quantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanFev1Quantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBasophilCountRecord(ClinicalMeasurementRecord):
    """
    Concentration of basophil cells in whole blood
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'rules': [{'postconditions': {'slot_conditions': {'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'instrument': {'any_of': [{'equals_string': 'flow '
                                                                                                       'cytometer'},
                                                                                     {'equals_string': 'microscope'}],
                                                                          'name': 'instrument'},
                                                           'method': {'any_of': [{'equals_string': 'CBC'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': '10*3/uL'},
                                                                               {'equals_string': '{#}/uL'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OBA:VT0002607'},
                                                                                          {'equals_string': 'OMOP:3006315'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBasophilCountQuantity'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBasophilCountQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBasophilCountRecord001(HumanBasophilCountRecord):
    """
    Concentration of basophil cells in whole blood
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBasophilCountQuantity001'},
                        'unit': {'any_of': [{'equals_string': '10*3/uL'}],
                                 'name': 'unit'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBasophilCountQuantity001 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': '10*3/uL'}],
         'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBasophilCountRecord002(HumanBasophilCountRecord):
    """
    Concentration of basophil cells in whole blood
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanBasophilCountQuantity001'},
                        'unit': {'any_of': [{'equals_string': '{#}/uL'}],
                                 'name': 'unit'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanBasophilCountQuantity001 = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': '{#}/uL'}],
         'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class AsthmaStatusRecord(ConditionStatusRecord):
    """
    Record suggesting the current or historical presence or absence of asthma  in the patient/participant or their blood relatives
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'condition_type': {'any_of': [{'range': 'DynamicAsthmaEnum'},
                                                      {'equals_string': 'ICD10:J45'},
                                                      {'equals_string': 'OMOP:764677'}],
                                           'name': 'condition_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    condition_type: Union[DynamicAsthmaEnum, str] = Field(default=..., description="""A CURIE from MONDO or HPO""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'DynamicAsthmaEnum'},
                    {'equals_string': 'ICD10:J45'},
                    {'equals_string': 'OMOP:764677'}],
         'domain_of': ['ConditionStatusRecord'],
         'slot_uri': 'bdchm:condition_concept'} })
    associated_evidence: Optional[AssociatedEvidenceEnum] = Field(default=None, description="""The method used for diagnosis""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    age_at_condition_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_record: Quantity = Field(default=..., description="""Age of participant when record of the condition was collected. This  slot can accommodate an \"age at encounter\" where a medical history was  collected, or a record was adjudicated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_status: HistoricalStatusEnum = Field(default=..., description="""A value indicating whether the medical condition described in this record is present, absent, historically present, or unknown for this individual patient.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_provenance: Optional[ProvenanceEnum] = Field(default=None, description="""A value representing the provenance of the Condition record.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_severity: Optional[ConditionSeverityEnum] = Field(default=None, description="""A subjective assessment of the severity of the condition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    relationship_to_participant: FamilyRelationshipEnum = Field(default=..., description="""A value indicating the relationship between the Participant to which the Condition is attributed and the individual who had the reported Condition. If the Condition is affecting the participant themselves, then 'Self' is the appropriate relationship.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })


class HeartFailureStatusRecord(ConditionStatusRecord):
    """
    Record suggesting the current or historical presence or absence of congestive  heart failure in the patient/participant or their blood relatives
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'condition_type': {'any_of': [{'range': 'DynamicHeartFailureEnum'},
                                                      {'equals_string': 'ICD10:I50'},
                                                      {'equals_string': 'OMOP:316139'}],
                                           'name': 'condition_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    condition_type: Union[DynamicHeartFailureEnum, str] = Field(default=..., description="""A CURIE from MONDO or HPO""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'DynamicHeartFailureEnum'},
                    {'equals_string': 'ICD10:I50'},
                    {'equals_string': 'OMOP:316139'}],
         'domain_of': ['ConditionStatusRecord'],
         'slot_uri': 'bdchm:condition_concept'} })
    associated_evidence: Optional[AssociatedEvidenceEnum] = Field(default=None, description="""The method used for diagnosis""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    age_at_condition_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_record: Quantity = Field(default=..., description="""Age of participant when record of the condition was collected. This  slot can accommodate an \"age at encounter\" where a medical history was  collected, or a record was adjudicated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_status: HistoricalStatusEnum = Field(default=..., description="""A value indicating whether the medical condition described in this record is present, absent, historically present, or unknown for this individual patient.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_provenance: Optional[ProvenanceEnum] = Field(default=None, description="""A value representing the provenance of the Condition record.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_severity: Optional[ConditionSeverityEnum] = Field(default=None, description="""A subjective assessment of the severity of the condition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    relationship_to_participant: FamilyRelationshipEnum = Field(default=..., description="""A value indicating the relationship between the Participant to which the Condition is attributed and the individual who had the reported Condition. If the Condition is affecting the participant themselves, then 'Self' is the appropriate relationship.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })


class ObesityStatusRecord(ConditionStatusRecord):
    """
    Record suggesting the current or historical presence or absence of obesity  in the patient/participant or their blood relatives
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'condition_type': {'any_of': [{'range': 'DynamicObesityEnum'},
                                                      {'equals_string': 'OMOP:433736'}],
                                           'name': 'condition_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    condition_type: Union[DynamicObesityEnum, str] = Field(default=..., description="""A CURIE from MONDO or HPO""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'DynamicObesityEnum'}, {'equals_string': 'OMOP:433736'}],
         'domain_of': ['ConditionStatusRecord'],
         'slot_uri': 'bdchm:condition_concept'} })
    associated_evidence: Optional[AssociatedEvidenceEnum] = Field(default=None, description="""The method used for diagnosis""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    age_at_condition_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the condition""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    age_at_condition_record: Quantity = Field(default=..., description="""Age of participant when record of the condition was collected. This  slot can accommodate an \"age at encounter\" where a medical history was  collected, or a record was adjudicated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_status: HistoricalStatusEnum = Field(default=..., description="""A value indicating whether the medical condition described in this record is present, absent, historically present, or unknown for this individual patient.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_provenance: Optional[ProvenanceEnum] = Field(default=None, description="""A value representing the provenance of the Condition record.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    condition_severity: Optional[ConditionSeverityEnum] = Field(default=None, description="""A subjective assessment of the severity of the condition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })
    relationship_to_participant: FamilyRelationshipEnum = Field(default=..., description="""A value indicating the relationship between the Participant to which the Condition is attributed and the individual who had the reported Condition. If the Condition is affecting the participant themselves, then 'Self' is the appropriate relationship.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConditionStatusRecord']} })


class AspirinStatusRecord(DrugStatusRecord):
    """
    Record suggesting exposure to aspirin
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'drug_type': {'any_of': [{'equals_string': 'OMOP:1112807'},
                                                 {'equals_string': 'RxNORM:1191'}],
                                      'name': 'drug_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    drug_type: str = Field(default=..., description="""A CURIE from RxNorm""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': 'OMOP:1112807'},
                    {'equals_string': 'RxNORM:1191'}],
         'domain_of': ['DrugStatusRecord'],
         'slot_uri': 'bdchm:drug_concept'} })
    age_at_drug_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_record: Quantity = Field(default=..., description="""Age of participant when record of the drug was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medication list. """, json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    route_of_administration: Optional[RouteAdminEnum] = Field(default=None, description="""Routes of drug administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    dose: Optional[Quantity] = Field(default=None, description="""Amount of drug per administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    frequency: Optional[Quantity] = Field(default=None, description="""How often e.g. 2 per day""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    indication: Optional[str] = Field(default=None, description="""Condition/reason for drug (SNOMED, ICD, Mondo, HPO, etc)""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })


class BetaBlockerStatusRecord(DrugStatusRecord):
    """
    Record suggesting exposure to aspirin
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'drug_type': {'any_of': [{'equals_string': 'OMOP:21601741'},
                                                 {'equals_string': 'ATC:C07A'}],
                                      'name': 'drug_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    drug_type: str = Field(default=..., description="""A CURIE from RxNorm""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': 'OMOP:21601741'}, {'equals_string': 'ATC:C07A'}],
         'domain_of': ['DrugStatusRecord'],
         'slot_uri': 'bdchm:drug_concept'} })
    age_at_drug_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_record: Quantity = Field(default=..., description="""Age of participant when record of the drug was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medication list. """, json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    route_of_administration: Optional[RouteAdminEnum] = Field(default=None, description="""Routes of drug administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    dose: Optional[Quantity] = Field(default=None, description="""Amount of drug per administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    frequency: Optional[Quantity] = Field(default=None, description="""How often e.g. 2 per day""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    indication: Optional[str] = Field(default=None, description="""Condition/reason for drug (SNOMED, ICD, Mondo, HPO, etc)""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })


class DiabetesMedicationStatusRecord(DrugStatusRecord):
    """
    Record suggesting exposure to aspirin
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'drug_type': {'any_of': [{'equals_string': 'ATC:A10'}],
                                      'name': 'drug_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    drug_type: str = Field(default=..., description="""A CURIE from RxNorm""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': 'ATC:A10'}],
         'domain_of': ['DrugStatusRecord'],
         'slot_uri': 'bdchm:drug_concept'} })
    age_at_drug_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of drug exposure""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    age_at_drug_record: Quantity = Field(default=..., description="""Age of participant when record of the drug was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medication list. """, json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    route_of_administration: Optional[RouteAdminEnum] = Field(default=None, description="""Routes of drug administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    dose: Optional[Quantity] = Field(default=None, description="""Amount of drug per administration""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    frequency: Optional[Quantity] = Field(default=None, description="""How often e.g. 2 per day""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })
    indication: Optional[str] = Field(default=None, description="""Condition/reason for drug (SNOMED, ICD, Mondo, HPO, etc)""", json_schema_extra = { "linkml_meta": {'domain_of': ['DrugStatusRecord']} })


class PacemakerStatusRecord(ProcedureStatusRecord):
    """
    Record of having a pacemaker implanted
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'procedure_type': {'any_of': [{'equals_string': 'OMOP:54772840'},
                                                      {'equals_string': 'NCIT:C99998'}],
                                           'name': 'procedure_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    procedure_type: str = Field(default=..., description="""A CURIE from OMOP""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': 'OMOP:54772840'},
                    {'equals_string': 'NCIT:C99998'}],
         'domain_of': ['ProcedureStatusRecord'],
         'slot_uri': 'bdchm:procedure_concept'} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    age_at_procedure_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_record: Quantity = Field(default=..., description="""Age of participant when record of the procedure was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medical history.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })


class CoronaryAngioplastyStatusRecord(ProcedureStatusRecord):
    """
    Record of having a coronary angioplasty
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'procedure_type': {'any_of': [{'equals_string': 'OMOP:4184832'}],
                                           'name': 'procedure_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    procedure_type: str = Field(default=..., description="""A CURIE from OMOP""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': 'OMOP:4184832'}],
         'domain_of': ['ProcedureStatusRecord'],
         'slot_uri': 'bdchm:procedure_concept'} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    age_at_procedure_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_record: Quantity = Field(default=..., description="""Age of participant when record of the procedure was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medical history.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })


class CoronaryBypassStatusRecord(ProcedureStatusRecord):
    """
    Record of having a coronary artery bypass graft
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'procedure_type': {'any_of': [{'equals_string': 'OMOP:4336464'}],
                                           'name': 'procedure_type'}}})

    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    procedure_type: str = Field(default=..., description="""A CURIE from OMOP""", json_schema_extra = { "linkml_meta": {'any_of': [{'equals_string': 'OMOP:4336464'}],
         'domain_of': ['ProcedureStatusRecord'],
         'slot_uri': 'bdchm:procedure_concept'} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    age_at_procedure_start: Optional[Quantity] = Field(default=None, description="""Age of the subject at the start of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_end: Optional[Quantity] = Field(default=None, description="""Age of the subject at the end of the procedure""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })
    age_at_procedure_record: Quantity = Field(default=..., description="""Age of participant when record of the procedure was collected. This  slot can accommodate an \"age at encounter\" where the participant was asked for their medical history.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProcedureStatusRecord']} })


class Relativity(ConfiguredBaseModel):
    """
    Mixin providing slots for bundling measured, predicted, and percent predicted values with their normal limits.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas', 'mixin': True})

    predicted_value: Optional[Decimal] = Field(default=None, description="""A predicted measurement value based on a reference population, range, equation, or other relevant information. Often used to normalize a measurement based on body size, age, or sex""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })
    lower_limit_normal: Optional[Decimal] = Field(default=None, description="""placeholder""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })
    upper_limit_normal: Optional[Decimal] = Field(default=None, description="""placeholder""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })
    percent_predicted_value: Optional[Decimal] = Field(default=None, description="""Ratio of the actual measured value to the predicted value""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })


class Context(ConfiguredBaseModel):
    """
    Mixin providing contextual slots that describe the activity type and relative timing associated with a clinical measurement.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas', 'mixin': True})

    activity_type: Optional[ActivityTypeEnum] = Field(default=None, description="""Activity that adds context to a clinical measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['Context']} })
    relative_timing: Optional[RelativeTimingEnum] = Field(default=None, description="""Timing of the activity relative to the clinical measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['Context']} })


class HumanFvcRecord(Context, Relativity, ClinicalMeasurementRecord):
    """
    Total amount of air a person can forcibly exhale after taking the deepest breath possible. This microschema uses the Relativity mixin to bundle measured, predicted, and percent predicted values.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'mixins': ['Relativity', 'Context'],
         'rules': [{'postconditions': {'slot_conditions': {'data_type': {'equals_string': 'decimal',
                                                                         'name': 'data_type'},
                                                           'instrument': {'any_of': [{'equals_string': 'spirometer'},
                                                                                     {'equals_string': 'vitalograph'},
                                                                                     {'equals_string': 'body_plesmograph'}],
                                                                          'name': 'instrument'},
                                                           'method': {'any_of': [{'equals_string': 'spirometry'},
                                                                                 {'equals_string': 'body_plesmography'}],
                                                                      'name': 'method'},
                                                           'unit': {'any_of': [{'equals_string': 'L'},
                                                                               {'equals_string': 'mL'}],
                                                                    'name': 'unit'}}},
                    'preconditions': {'slot_conditions': {'measurement_type': {'any_of': [{'equals_string': 'OMOP:4176265'}],
                                                                               'name': 'measurement_type'}}}}],
         'slot_usage': {'measurement_value': {'name': 'measurement_value',
                                              'range': 'HumanFvcQuantity'},
                        'percent_predicted_value': {'name': 'percent_predicted_value',
                                                    'required': True},
                        'predicted_value': {'name': 'predicted_value',
                                            'required': True}}})

    predicted_value: Decimal = Field(default=..., description="""A predicted measurement value based on a reference population, range, equation, or other relevant information. Often used to normalize a measurement based on body size, age, or sex""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })
    lower_limit_normal: Optional[Decimal] = Field(default=None, description="""placeholder""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })
    upper_limit_normal: Optional[Decimal] = Field(default=None, description="""placeholder""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })
    percent_predicted_value: Decimal = Field(default=..., description="""Ratio of the actual measured value to the predicted value""", json_schema_extra = { "linkml_meta": {'domain_of': ['Relativity']} })
    activity_type: Optional[ActivityTypeEnum] = Field(default=None, description="""Activity that adds context to a clinical measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['Context']} })
    relative_timing: Optional[RelativeTimingEnum] = Field(default=None, description="""Timing of the activity relative to the clinical measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['Context']} })
    subject_identifier: str = Field(default=..., description="""An identifier for the subject of the datum""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'ConditionStatusRecord',
                       'DrugStatusRecord',
                       'ProcedureStatusRecord']} })
    measurement_type: str = Field(default=..., description="""A CURIE from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'],
         'slot_uri': 'bdchm:observation_type'} })
    measurement_value: HumanFvcQuantity = Field(default=..., description="""The \"value\" in the observation key/value pair""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    method: Optional[MethodEnum] = Field(default=None, description="""The method used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:method_type'} })
    instrument: Optional[InstrumentEnum] = Field(default=None, description="""The instrument used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ConditionStatusRecord']} })
    reagent_kit: Optional[ReagentKitEnum] = Field(default=None, description="""The reagent kit used for the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    calculated_from: Optional[str] = Field(default=None, description="""An expression pointing at other CDE classes""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    body_location: Optional[str] = Field(default=None, description="""A CURIE from UBERON""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord'], 'slot_uri': 'bdchm:BodySite'} })
    body_position: Optional[BodyPositionEnum] = Field(default=None, description="""The body position during measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    context: Optional[ContextEnum] = Field(default=None, description="""The context of the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    collected_by: Optional[CollectedByEnum] = Field(default=None, description="""Who collected the measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord', 'ProcedureStatusRecord']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    age_at_measurement: Quantity = Field(default=..., description="""Age of the subject at the time of measurement""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    study_site: Optional[str] = Field(default=None, description="""Institution name, clinic name, or other indication of where a measurement was taken geographically""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })
    absolute_time: Optional[datetime ] = Field(default=None, description="""Calendar date when a measurement was taken""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord']} })


class HumanBodyHeightQuantity(Quantity):
    """
    Human body height. Negative heights are impossible.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyHeightQuantity001(HumanBodyHeightQuantity):
    """
    Standing wall-mounted or portable stadiometer human body height in cm, bounded 30–230.  Minimum represents observed limits on human height. Maximum represents limit of measurement device.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 230,
                                           'minimum_value': 30,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=30, le=230, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyHeightQuantity002(HumanBodyHeightQuantity):
    """
    Standing wall-mounted or portable stadiometer human body height in inches, bounded 20–90.  Minimum represents observed limits on human height. Maximum represents limit of measurement device.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 90,
                                           'minimum_value': 20,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=20, le=90, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyHeightQuantity003(HumanBodyHeightQuantity):
    """
    Standing anthropometer human body height in cm, bounded 30-250.  Minimum represents observed limits on human height. Maximum represents limit of measurement device.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 250,
                                           'minimum_value': 30,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=30, le=250, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyHeightQuantity004(HumanBodyHeightQuantity):
    """
    Standing wall-mounted or portable stadiometer human body height in ft, bounded 0.98-8.2.  Minimum represents observed limits on human height. Maximum represents limit of measurement device.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 8.2,
                                           'minimum_value': 0.98,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0.98, le=8.2, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyWeightQuantity(Quantity):
    """
    Human body weight. Negative weights are impossible.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyWeightQuantity001(HumanBodyWeightQuantity):
    """
    Mechanical-beam-balance human body weight in kg, bounded 0–230. Maximum weight set based on limits of measurement device.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 230,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=230, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyWeightQuantity002(HumanBodyWeightQuantity):
    """
    Mechanical-beam-balance human body weight in lbs, bounded 0–500. Maximum weight set based on limits of measurement device.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 500,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=500, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBodyWeightQuantity003(HumanBodyWeightQuantity):
    """
    Body composition analyzer human body weight in kg, bounded 0–270. Maximum weight set based on limits of measurement device.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 270,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=270, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class BodyMassIndexQuantity(Quantity):
    """
    Body mass index value in kg/m², bounded 5–200. Limits based on observed limits  of human body size.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 200,
                                           'minimum_value': 5,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=5, le=200, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanFvcQuantity(Quantity):
    """
    FVC measurement, bounded 0–12000.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 12000,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=12000, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanMeasuredFvcQuantity(Quantity):
    """
    Measured FVC, bounded 0–12000.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 12000,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=12000, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanMeasuredFvcQuantity001(HumanMeasuredFvcQuantity):
    """
    Measured FVC in L, bounded 0–12.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 12,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=12, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanPredictedFvcQuantity(Quantity):
    """
    Predicted FVC in L, bounded 0–12.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 12,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=12, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanPercentPredictedFvcQuantity(Quantity):
    """
    Percent-predicted FVC, bounded 0–150.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 150,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=150, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanFev1Quantity(Quantity):
    """
    FEV1 measurement, bounded 0–12000.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 12000,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=12000, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBasophilCountQuantity(Quantity):
    """
    Basophil concentration measurement. Negative values are impossible.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBasophilCountQuantity001(HumanBasophilCountQuantity):
    """
    Basophil concentration measurement, bounded 0-0.3 based on observed  biological limits.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 0.3,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=0.3, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class HumanBasophilCountQuantity002(HumanBasophilCountQuantity):
    """
    Basophil concentration measurement, bounded 0-300 based on observed  biological limits.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/clinical-microschemas',
         'slot_usage': {'quantity_value': {'maximum_value': 300,
                                           'minimum_value': 0,
                                           'name': 'quantity_value'}}})

    quantity_value: Decimal = Field(default=..., description="""The numeric value""", ge=0, le=300, json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })
    quantity_unit: str = Field(default=..., description="""Unit (UCUM, UO, QUDT, etc.)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity'], 'slot_uri': 'schema:unitCode'} })
    comparator: Optional[ComparatorEnum] = Field(default=None, description="""Comparison operator (less than, greater than, etc.) or exact if null""", json_schema_extra = { "linkml_meta": {'domain_of': ['Quantity']} })


class Entity(ConfiguredBaseModel):
    """
    Any resource that has its own identifier
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'class_uri': 'schema:Thing',
         'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class Variable(Entity):
    """
    A generic grouping for any variable
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class SingleContinuousVariable(Variable):
    """
    Represents a single entry in a data dictionary of a variable with a continuous value
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    source_id: Optional[str] = Field(default=None, description="""Identifier used by the organization providing the variable to BDC to uniquely identify the variable in their system. In most cases this will be a phv value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    file_id: Optional[str] = Field(default=None, description="""Identifier used by the organization providing the variable to BDC to uniquely identify the file or data table in their system. In most cases this will be a pht value""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    file_name: Optional[str] = Field(default=None, description="""Name of file containing variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    variable_name: Optional[str] = Field(default=None, description="""The name of the variable according to the original data provider Corresponds to the VARNAME field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    source_variable_description: Optional[str] = Field(default=None, description="""Description of the variable provided by the original data provider Corresponds to the VARDESC field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    minimum_value: Optional[Decimal] = Field(default=None, description="""The lowest value present in the data for this variable. Corresponds to  the MIN field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable']} })
    maximum_value: Optional[Decimal] = Field(default=None, description="""The highest value present in the data for this variable. Corresponds to the MAX field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable']} })
    resolution: Optional[int] = Field(default=None, description="""The number of decimal places a measurement is represented in the data. Corresponds to the RESOLUTION field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable']} })
    missing_value: Optional[list[MissingValue]] = Field(default=None, description="""Sentinel value to indicate a missing value or other data nuance""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    alert_values: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable']} })
    comment: Optional[str] = Field(default=None, description="""Any text comment provided by the original data provider. Corresponds to the  COMMENT field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class SingleCategoricalVariable(Variable):
    """
    Represents a single entry in a data dictionary of a variable with a categorical value
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    source_id: Optional[str] = Field(default=None, description="""Identifier used by the organization providing the variable to BDC to uniquely identify the variable in their system. In most cases this will be a phv value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    file_id: Optional[str] = Field(default=None, description="""Identifier used by the organization providing the variable to BDC to uniquely identify the file or data table in their system. In most cases this will be a pht value""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    file_name: Optional[str] = Field(default=None, description="""Name of file containing variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    variable_name: Optional[str] = Field(default=None, description="""The name of the variable according to the original data provider Corresponds to the VARNAME field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    source_variable_description: Optional[str] = Field(default=None, description="""Description of the variable provided by the original data provider Corresponds to the VARDESC field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    data_type: Optional[DataTypeEnum] = Field(default=None, description="""The data type of the observation""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'SingleCategoricalVariable']} })
    missing_value: Optional[list[MissingValue]] = Field(default=None, description="""Sentinel value to indicate a missing value or other data nuance""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    coded_values: Optional[list[EnumValue]] = Field(default=None, description="""List of allowable values. Should only be used if the data_type is enum. Corresponds to VALUES field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleCategoricalVariable']} })
    comment: Optional[str] = Field(default=None, description="""Any text comment provided by the original data provider. Corresponds to the  COMMENT field in dbGAP""", json_schema_extra = { "linkml_meta": {'domain_of': ['SingleContinuousVariable', 'SingleCategoricalVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class CompoundVariable(Variable):
    """
    Represents a variable and all metadata
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class IntegratedVariable(Variable):
    """
    Represents a variable that contains data from multiple studies. Typically, some or all of the data must undergo a transformation in order to be successfully integrated
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    integrates: Optional[list[str]] = Field(default=None, description="""List of variables combined in the IntegratedVariable""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegratedVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class MissingValue(ConfiguredBaseModel):
    """
    Character used to indicate a missing value in a data set
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    indicator_char: Optional[str] = Field(default=None, description="""Value used to add information to a datum, indicate a missing datum, or give  a specific answer""", json_schema_extra = { "linkml_meta": {'domain_of': ['MissingValue', 'AlertValue', 'EnumValue']} })
    indicator_meaning: Optional[str] = Field(default=None, description="""Meaning of the indicator character verbatim from original data provider when possible""", json_schema_extra = { "linkml_meta": {'domain_of': ['MissingValue', 'AlertValue', 'EnumValue']} })


class AlertValue(ConfiguredBaseModel):
    """
    Character used to add information to a datum
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    indicator_char: Optional[str] = Field(default=None, description="""Value used to add information to a datum, indicate a missing datum, or give  a specific answer""", json_schema_extra = { "linkml_meta": {'domain_of': ['MissingValue', 'AlertValue', 'EnumValue']} })
    indicator_meaning: Optional[str] = Field(default=None, description="""Meaning of the indicator character verbatim from original data provider when possible""", json_schema_extra = { "linkml_meta": {'domain_of': ['MissingValue', 'AlertValue', 'EnumValue']} })


class EnumValue(ConfiguredBaseModel):
    """
    One possible answer in a list of enumerated values
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    indicator_char: Optional[str] = Field(default=None, description="""Value used to add information to a datum, indicate a missing datum, or give  a specific answer""", json_schema_extra = { "linkml_meta": {'domain_of': ['MissingValue', 'AlertValue', 'EnumValue']} })
    indicator_meaning: Optional[str] = Field(default=None, description="""Meaning of the indicator character verbatim from original data provider when possible""", json_schema_extra = { "linkml_meta": {'domain_of': ['MissingValue', 'AlertValue', 'EnumValue']} })
    indicator_type: Optional[str] = Field(default=None, description="""CURIE describing the meaning of the indicator""", json_schema_extra = { "linkml_meta": {'domain_of': ['EnumValue']} })


class MetadataVariable(Entity):
    """
    Specific data point used to add information to an observation. This will typically be a unique identifier for a SingleVariable and a slot from a  microschema
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    microschema_slot: Optional[list[ClinicalMicroschemaEnum]] = Field(default=None, description="""The slot that the variable identified in the variable path should go""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetadataVariable', 'DocumentationVariable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class DocumentationVariable(ConfiguredBaseModel):
    """
    Information derived from study documentation or text in a data dictionary that provides essential metadata for a variable
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'rules': [{'postconditions': {'slot_conditions': {'contr_vocab': {'name': 'contr_vocab',
                                                                           'range': 'InstrumentEnum'}}},
                    'preconditions': {'slot_conditions': {'microschema_slot': {'equals_string': 'instrument',
                                                                               'name': 'microschema_slot'}}}},
                   {'postconditions': {'slot_conditions': {'contr_vocab': {'name': 'contr_vocab',
                                                                           'range': 'MethodEnum'}}},
                    'preconditions': {'slot_conditions': {'microschema_slot': {'equals_string': 'method_type',
                                                                               'name': 'microschema_slot'}}}},
                   {'postconditions': {'slot_conditions': {'contr_vocab': {'any_of': [{'pattern': '^MONDO:\\d{7}$'},
                                                                                      {'pattern': '^HP:\\d{7}$'}],
                                                                           'name': 'contr_vocab'}}},
                    'preconditions': {'slot_conditions': {'microschema_slot': {'equals_string': 'condition_concept',
                                                                               'name': 'microschema_slot'}}}},
                   {'postconditions': {'slot_conditions': {'contr_vocab': {'name': 'contr_vocab',
                                                                           'range': 'ProvenanceEnum'}}},
                    'preconditions': {'slot_conditions': {'microschema_slot': {'equals_string': 'condition_provenance',
                                                                               'name': 'microschema_slot'}}}}]})

    contr_vocab: Optional[str] = Field(default=None, description="""Value from an enum""", json_schema_extra = { "linkml_meta": {'domain_of': ['DocumentationVariable']} })
    microschema_slot: Optional[list[ClinicalMicroschemaEnum]] = Field(default=None, description="""The slot that the variable identified in the variable path should go""", json_schema_extra = { "linkml_meta": {'domain_of': ['MetadataVariable', 'DocumentationVariable']} })


class CompoundHeight002(CompoundVariable):
    """
    Height variable with metadata, measured in inches and collected using a wall-mounted stadiometer
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'instantiates': ['HumanBodyHeightRecord002']})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class CompoundHeight001(CompoundVariable):
    """
    Height variable with metadata, measured in cm and collected using a wall-mounted stadiometer
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'instantiates': ['HumanBodyHeightRecord001']})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class IntegratedHeight001(IntegratedVariable):
    """
    Height variable containing data from multiple studies, normalized to cm
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    integrates: Optional[list[str]] = Field(default=None, description="""List of variables combined in the IntegratedVariable""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegratedVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class CompoundAsthma001(CompoundVariable):
    """
    A record of participant asthma status
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'instantiates': ['AsthmaStatusRecord']})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class IntegratedAsthma001(IntegratedVariable):
    """
    Participant asthma status containing data from multiple studies
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    integrates: Optional[list[str]] = Field(default=None, description="""List of variables combined in the IntegratedVariable""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegratedVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class CompoundHeartFailure001(CompoundVariable):
    """
    A record of a participant heart failure status
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'instantiates': ['HeartFailureStatusRecord']})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class IntegratedHeartFailure001(IntegratedVariable):
    """
    Participant heart failure status containing data from multiple studies
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    integrates: Optional[list[str]] = Field(default=None, description="""List of variables combined in the IntegratedVariable""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegratedVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class CompoundObesity001(CompoundVariable):
    """
    A record of a participant obesity status
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'instantiates': ['ObesityStatusRecord']})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class IntegratedObesity001(IntegratedVariable):
    """
    Participant obesity status containing data from multiple studies
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    integrates: Optional[list[str]] = Field(default=None, description="""List of variables combined in the IntegratedVariable""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegratedVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class CompoundAspirin001(CompoundVariable):
    """
    A record of participant aspirin usage status
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'instantiates': ['AspirinStatusRecord']})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class IntegratedAspirin001(IntegratedVariable):
    """
    Participant aspirin status containing data from multiple studies
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    integrates: Optional[list[str]] = Field(default=None, description="""List of variables combined in the IntegratedVariable""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegratedVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class CompoundPacemaker001(CompoundVariable):
    """
    A record of participant pacemaker status
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library',
         'instantiates': ['PacemakerStatusRecord']})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    row_metadata: Optional[list[MetadataVariable]] = Field(default=None, description="""List of variable identifiers providing metadata for a compound variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    documentation_metadata: Optional[list[DocumentationVariable]] = Field(default=None, description="""List of metadata elements that derive from study documentation or descriptive information in the data dictionary""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    alert_value: Optional[list[AlertValue]] = Field(default=None, description="""List of values that provide extra optional information about a variable. Often this is used to indicate a violation of QA/QC""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class IntegratedPacemaker001(IntegratedVariable):
    """
    Participant pacemaker status containing data from multiple studies
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    cde_id: Optional[str] = Field(default=None, description="""CURIE from Condor""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    bdchm_type: Optional[BdchmTypeEnum] = Field(default=None, description="""Entity type from BDCHM that defines the variable type""", json_schema_extra = { "linkml_meta": {'domain_of': ['CompoundVariable', 'IntegratedVariable']} })
    unit: Optional[str] = Field(default=None, description="""A unit from UCUM""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClinicalMeasurementRecord',
                       'SingleContinuousVariable',
                       'CompoundVariable',
                       'IntegratedVariable'],
         'slot_uri': 'bdchm:unit'} })
    integrates: Optional[list[str]] = Field(default=None, description="""List of variables combined in the IntegratedVariable""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntegratedVariable']} })
    associated_study: Optional[str] = Field(default=None, description="""The study that produced the variable data""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable'], 'slot_uri': 'bdchm:ResearchStudy'} })
    variable_description: Optional[str] = Field(default=None, description="""Human readable description of the variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    concept_type: Optional[str] = Field(default=None, description="""CURIE describing the main content of the variable. This can be from OBA, OMOP, or LOINC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    variable_label: Optional[str] = Field(default=None, description="""Human readable label describing the variable""", json_schema_extra = { "linkml_meta": {'domain_of': ['Variable']} })
    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


class ResearchStudy(Entity):
    """
    Name of research study that produced the variable
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'bdchm:ResearchStudy',
         'from_schema': 'https://w3id.org/linkml/bdc-variable-library'})

    id: str = Field(default=..., description="""A unique identifier for a variable within BDC""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'schema:identifier'} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
MicroschemaDefinition.model_rebuild()
ValueMicroschemaDefinition.model_rebuild()
Quantity.model_rebuild()
Timepoint.model_rebuild()
TimeInterval.model_rebuild()
CodedValue.model_rebuild()
ClinicalMeasurementRecord.model_rebuild()
ConditionStatusRecord.model_rebuild()
DrugStatusRecord.model_rebuild()
ProcedureStatusRecord.model_rebuild()
HumanBodyHeightRecord.model_rebuild()
HumanBodyHeightRecord001.model_rebuild()
HumanBodyHeightRecord002.model_rebuild()
HumanBodyHeightRecord003.model_rebuild()
HumanBodyHeightRecord004.model_rebuild()
HumanBodyHeightRecord005.model_rebuild()
HumanBodyHeightRecord006.model_rebuild()
HumanBodyWeightRecord.model_rebuild()
HumanBodyWeightRecord001.model_rebuild()
HumanBodyWeightRecord002.model_rebuild()
HumanBodyWeightRecord003.model_rebuild()
BodyMassIndexRecord.model_rebuild()
BodyMassIndexRecord001.model_rebuild()
BodyMassIndexRecord002.model_rebuild()
HumanMeasuredFvcRecord.model_rebuild()
HumanMeasuredFvcRecord001.model_rebuild()
HumanPredictedFvcRecord.model_rebuild()
HumanPercentPredictedFvcRecord.model_rebuild()
HumanFev1Record.model_rebuild()
HumanBasophilCountRecord.model_rebuild()
HumanBasophilCountRecord001.model_rebuild()
HumanBasophilCountRecord002.model_rebuild()
AsthmaStatusRecord.model_rebuild()
HeartFailureStatusRecord.model_rebuild()
ObesityStatusRecord.model_rebuild()
AspirinStatusRecord.model_rebuild()
BetaBlockerStatusRecord.model_rebuild()
DiabetesMedicationStatusRecord.model_rebuild()
PacemakerStatusRecord.model_rebuild()
CoronaryAngioplastyStatusRecord.model_rebuild()
CoronaryBypassStatusRecord.model_rebuild()
Relativity.model_rebuild()
Context.model_rebuild()
HumanFvcRecord.model_rebuild()
HumanBodyHeightQuantity.model_rebuild()
HumanBodyHeightQuantity001.model_rebuild()
HumanBodyHeightQuantity002.model_rebuild()
HumanBodyHeightQuantity003.model_rebuild()
HumanBodyHeightQuantity004.model_rebuild()
HumanBodyWeightQuantity.model_rebuild()
HumanBodyWeightQuantity001.model_rebuild()
HumanBodyWeightQuantity002.model_rebuild()
HumanBodyWeightQuantity003.model_rebuild()
BodyMassIndexQuantity.model_rebuild()
HumanFvcQuantity.model_rebuild()
HumanMeasuredFvcQuantity.model_rebuild()
HumanMeasuredFvcQuantity001.model_rebuild()
HumanPredictedFvcQuantity.model_rebuild()
HumanPercentPredictedFvcQuantity.model_rebuild()
HumanFev1Quantity.model_rebuild()
HumanBasophilCountQuantity.model_rebuild()
HumanBasophilCountQuantity001.model_rebuild()
HumanBasophilCountQuantity002.model_rebuild()
Entity.model_rebuild()
Variable.model_rebuild()
SingleContinuousVariable.model_rebuild()
SingleCategoricalVariable.model_rebuild()
CompoundVariable.model_rebuild()
IntegratedVariable.model_rebuild()
MissingValue.model_rebuild()
AlertValue.model_rebuild()
EnumValue.model_rebuild()
MetadataVariable.model_rebuild()
DocumentationVariable.model_rebuild()
CompoundHeight002.model_rebuild()
CompoundHeight001.model_rebuild()
IntegratedHeight001.model_rebuild()
CompoundAsthma001.model_rebuild()
IntegratedAsthma001.model_rebuild()
CompoundHeartFailure001.model_rebuild()
IntegratedHeartFailure001.model_rebuild()
CompoundObesity001.model_rebuild()
IntegratedObesity001.model_rebuild()
CompoundAspirin001.model_rebuild()
IntegratedAspirin001.model_rebuild()
CompoundPacemaker001.model_rebuild()
IntegratedPacemaker001.model_rebuild()
ResearchStudy.model_rebuild()
