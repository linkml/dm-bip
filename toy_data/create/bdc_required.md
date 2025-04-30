# Required Elements of the BDC Model

I need to research and document the required elements of the [BioData Catalyst Harmonized Model (BDC-HM)](https://github.com/RTIInternational/NHLBI-BDC-DMC-HM).

Looking at the YAML and data model, as well as having an LLM analyze it, I have determined these fields to be a basal requirement for data that would be converted to the BDC-HM.

These top level entities are the minimum required, each will need to have its minimum data fields represented as well.
1. Person - The basis of almost all of this data is a person with some form of number to identify that person without sensitive information
2. Demography - Demographic information about a person and study participant
3. Participant - Information about a person participating in a study, with study based information such as the age of the participation when the study was conducted
	1. Consent - All information about how the participant is properly consented to the study
4. Research Study - The information about the research study or studies in the dataset and the individual participants linked with these studies, i.e age and consent
5. Condition - Any conditions of interest that a participant in the study may have
6. Measurement - Any measurements taken on the participant

In addition, some additional entities are likely of interest and should be included.
 1. Visit - Information about the visit or visits the participant had for the study
 2. Questionnaire - Any information recorded through questionnaires
 3. Procedure - Any procedure that may occur on the participant that the study tracks either as part of the study or as relevant information
 4. Observation - Any observed information about the participant, this has sub-types capturing specific observations

## Class and Slot Analysis
Unlike INCLUDE, the BDC schema is all in one YAML file so we don't need to examine the files separately. In addition, BDC doesn't include a method for determining whether a class is required so we'll need to select what classes we think are necessary based on our assumptions on the data we expect to see. Generally, it might be best to assume we should get some data from each class. We can also ignore the clear metaclasses, marked with abstract=true. Given the class selection, we should determine the minimum required slots for each of the classes. Again, it appears that the BDC schema is more flexible than the INCLUDE data model so most of the slots do not appear to be required. As we don't have many slot requirements we should choose some reasonable slots for each of the classes to create an example data set.

### Classes and Slots to Include
Here are the classes and slots we should probably include in the toy dataset in order to get reasonable covereage of the BDC data model. We're includding Person here only to make sure that we can wire up the connection to Participant in the BDC model.
- Person
	- species
	- identity
- Demography
    - sex
    - ethnicity
    - race
	- identity
    - associated_participant
- Participant
    - description
    - member_of_research_study
    - age_at_index
    - associated_person
    - identity
- ResearchStudy
    - name
    - identity
- Visit
    - visit_category
    - associated_participant
- Condition
    - condition_status
    - condition_severity
    - associated_participant
    - associated_visit
    - identity
- ObservationSet
    - category
    - focus
    - associated_participant
    - associated_visit
    - method_type
    - performed_by
    - observations
- Observation
    - age_at_observation
    - category
    - observation_type
    - method_type
    - focus
    - associated_participant
    - associated_visit
    - performed_by
    - value_string
    - value_boolean
    - value_quantity
    - value_enum

For now, I'm excluding all of the observation based slots except for observation because I think they make things complicated for a first run, they also don't add texture to the robust toy data set above what they add in complexity. Once we have the mapping figured out for Observation, expanding to the different types of Observation should be straightforward.

Many of these classes have an 'identity' slot that would be a unique identifier and likely not provided by the studies. We will probably be auto-generating these. I'm leaving these in here for targeting the mapping but they will not be specific fields we create in the toy data set.

### Classses and Slots to Exclude
This is the list of Classes and slots to leave out of the toy dataset with rationale for some on why we made that decision.

- Entity  --- Abstract
- Person  --- These don't seem very important or may be privacy issues.
    - breed
    - year_of_birth
    - vital_status
    - age_at_death
    - year_of_death
    - cause_of_death
- Participant
    - description  --- Probably a free-form field, so uninteresting
    - index_timepoint  --- Not ready to deal with timepoints
    - originating_site
    - study_arm
    - consents
- ResearchStudy  --- Free-form or not clear what value
    - description
    - description_shortened
    - sponsor
    - part_of
    - principal_investigator
    - associated_timepoint
    - name_shortened
    - date_started
    - date_ended
    - url
    - research_project_type
    - consents
- Consent  --- Not ready to deal with consent
- Visit  --- These don't seem especially informative
    - age_at_visit_start
    - age_at_visit_end
    - visit_provenance
- Organization  --- I don't think this gets us anything new
    - name
    - alias
    - organization_type
	- identity
- TimePoint  --- This feels more complicated than we are ready for
    - date_time
    - index_time_point
    - offset_from_index
    - event_type
- TimePeriod  --- Again feels like too much
	- period_start
    - period_end
- ResearchStudyCollection  --- Too meta for now
      entries
- Questionnaire  --- I think I'm going to leave all the questionaire stuff out of the toy
    all slots and related classes
- Condition
    - condition_concept
    - age_at_condition_start
    - age_at_condition_end
    - condition_provenance
    - relationship_to_participant
- Procedure  --- Seems like we can deal with this later
- Exposure  --- Also leave until later, and all related
- DimensionalObservation
- DimensionalObservationSet
- File  --- Out of scope, at least for now
- Document  --- Out of scope, at least for now
- Specimen  --- Seems out of scope, and all related
- BiologicalProduct  --- Out of scope for now
- Substance  --- Likely not specified in current data
    - substance_type
    - role  
    - substance_quantity
- BodySite
    - observations
- Quantity
    - value_decimal
    - value_integer
    - value_concept
    - unit
- MeasurementObservationSet
    - observations
- MeasurementObservation  --- Inherits from Observation
    - range_low
    - range_high
- SdohObservationSet
    - observations
    - category
- SdohObservation
    - related_questionnaire_item
    - category

## Example files

### Participant.csv

(Includes demographics directly)
participant_id	sex	ethnicity	race	year_of_birth
P001	MALE	NOT_HISPANIC_OR_LATINO	WHITE	1985
P002	FEMALE	HISPANIC_OR_LATINO	ASIAN	1992

### ClinicalData.csv

(Combines Visits, Conditions, and Measurements—one row per visit/event)
participant_id	visit_category	age_at_visit	condition	condition_status	systolic_bp	diastolic_bp	measurement_unit
P001	Outpatient	14000	Hypertension	PRESENT	130	85	mmHg
P002	Inpatient	11000	None	N/A	120	75	mmHg


### ResearchStudy.csv

(We generate this ourselves during transformation)
research_study_id	name
RS001	Hypertension Monitoring Study