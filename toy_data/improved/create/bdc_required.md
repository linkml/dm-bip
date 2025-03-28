# Required Elemenets of the BDC Model

I need to research and document the required elements of the BioData Catalyst Harmonized Model (BDC-HM).

Looking at the YAML and data model, as well as having an LLM analyze it, I have determined these fields to be a basal requirement for data that would be converted to the BDC-HM.

These top level entities are the minimum required, each will need to have it's minimum data fields represented as well.
1. Person - The basis of almost all of this data is a person with some form of number to identify that person without sensitive information
2. Demography - Demographic information about a person and study participant
3. Participant - Information about a person participating in a study, with study based information such as the age of the participation when the study was conducted
	1. Consent - All information about how the participant is properly consented to the study
4. Research Study - The information about the research study or studies in the dataset and the individual participants linked with these studies, i.e age and consent
5. Condition - Any conditions of interest that a participant in the study may have
6. Measurement - Any measurements taken on the participant

In addition, some additional entities are likely interest and should likely be included.
 1. Visit - Information about the visit or visits the participant had for the study
 2. Questionnaire - Any information recorded through questionnaires
 3. Procedure - Any procedure that may occur on the participant that the study tracks either as part of the study or as relevant information
 4. Observation - Any observed information about the participant, this has sub-types capturing specific observations

Here is an example of what these files might look like.

Participant.csv

(Includes demographics directly)
participant_id	sex	ethnicity	race	year_of_birth
P001	MALE	NOT_HISPANIC_OR_LATINO	WHITE	1985
P002	FEMALE	HISPANIC_OR_LATINO	ASIAN	1992
ClinicalData.csv

(Combines Visits, Conditions, and Measurements—one row per visit/event)
participant_id	visit_category	age_at_visit	condition	condition_status	systolic_bp	diastolic_bp	measurement_unit
P001	Outpatient	14000	Hypertension	PRESENT	130	85	mmHg
P002	Inpatient	11000	None	N/A	120	75	mmHg
ResearchStudy.csv

(We generate this ourselves during transformation)
research_study_id	name
RS001	Hypertension Monitoring Study