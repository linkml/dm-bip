# Creating a good toy data set
In order to create a useful and robust toy data set we need to gather some information about the systems we will be transforming the data to and the data we will be transforming.

 1. Gather the required fields from the BioData Catalyst Harmonized Model and the Include LinkML Model.
 2. Identify those data fields in the BDCHM Prioritized variables
 3. Review other prioritized variables to identify the most valuable to develop and test on.
 4. Use the above as a list variables for the toy synthetic data set
 5. Provide the list of fields for synthetic data to an LLM with descriptions of what we would like to generate and have the LLM generate a small synthetic data set.

## Aligned Fields by Class and Slot Similarity

The table below compares fields from two models: **BDC-HM** (BioData Catalyst Harmonized Model) and **INCLUDE Model**.

| **BDC-HM**                          | **INCLUDE Model**                   |
|-------------------------------------|-------------------------------------|
| Person:species                      |                                     |
| Demography:sex                      | Participant:sex                     |
| Demography:ethnicity                | Participant:ethnicity               |
| Demography:race                     | Participant:race                    |
| Demography:associated_participant   |                                     |
| Participant:description             |                                     |
| Participant:member_of_research_study|                                     |
| Participant:age_at_index            | Participant:ageAtFirstPatientEngagement |
| Participant:associated_person       |                                     |
|                                     | Participant:participantGlobalId     |
|                                     | Participant:participantExternalId   |
| Visit:visit_category                |                                     |
| Visit:associated_participant        |                                     |
| Condition:condition_status          |  Participant:downSyndromeStatus     |
| Condition:condition_severity        |                                     |
| Condition:associated_participant    |                                     |
| Condition:associated_visit          |                                     |
|                                     | Participant:firstPatientEngagementEvent |
| ResearchStudy:name                  | Study:studyTitle                    |
|                                     | Study:studyCode                     |
|                                     | Study:program                       |
|                                     | Study:studyDescription              |
|                                     | Study:studyContactName              |
|                                     | Study:studyContactInstitution       |
|                                     | Study:studyContactEmail             |
|                                     | Study:researchDomain                |
|                                     | Study:participantLifespanStage      |
|                                     | Study:studyDesign                   |
|                                     | Study:clinicalDataSourceType        |
|                                     | Study:guidType                      |
| ObservationSet:category             | Dataset:dataCategory                |
| ObservationSet:focus                |                                     |
| ObservationSet:associated_participant|                                    |
| ObservationSet:associated_visit     |                                     |
| ObservationSet:method_type          |                                     |
| ObservationSet:performed_by         |                                     |
| ObservationSet:observations         |                                     |
|                                     | Dataset:datasetGlobalId             |
|                                     | Dataset:experimentalStrategy        |
|                                     | Dataset:experimentalPlatform        |
|                                     | Dataset:accessLimitations           |
|                                     | Dataset:dataType                    |
|                                     | Dataset:accessRequirements          |
| Observation:age_at_observation      |                                     |
| Observation:category                |                                     |
|                                     | Dataset:dataCollectionStartYear     |
|                                     | Dataset:dataCollectionEndYear       |
| Observation:observation_type        |                                     |
| Observation:method_type             |                                     |
| Observation:focus                   |                                     |
| Observation:associated_participant  |                                     |
| Observation:associated_visit        |                                     |
| Observation:performed_by            |                                     |
| Observation:value_string            |                                     |
| Observation:value_boolean           |                                     |
| Observation:value_quantity          |                                     |
| Observation:value_enum              |                                     |
|                                     | Biospecimen:studyCode               |
|                                     | Biospecimen:participantGlobalId     |
|                                     | Biospecimen:participantExternalId   |
|                                     | Biospecimen:sampleGlobalId          |
|                                     | Biospecimen:sampleExternalId        |
|                                     | Biospecimen:sampleType              |
|                                     | Biospecimen:sampleAvailability      |
|                                     | Biospecimen:containerAvailability   |
|                                     | Datafile:studyCode                  |
|                                     | Datafile:fileName                   |
|                                     | Datafile:fileGlobalId               |
|                                     | Datafile:fileS3Location             |
|                                     | Datafile:drsUri                     |
|                                     | Datafile:dataAccess                 |
|                                     | Datafile:dataCategory               |
|                                     | Datafile:dataType                   |
|                                     | Datafile:fileFormat                 |

This is now a good working start for the needed fields and overlap for creating the toy data set attempting to meet all the requirements for both models. Now we can gather this as a list of needed fields, remove duplicates (values stored in more than one Class to link classes together), and gather the additional fields from the TOPMed Prioritized variables. These are the linking fields I'm dropping: 
Demography:associated_participant
Participant:member_of_research_study
Participant:associated_person
Participant:participantGlobalId
Participant:participantExternalId
Visit:associated_participant
Condition:associated_participant
Condition:associated_visit
ObservationSet:associated_participant


I'm also going to leave out some other fields that don't make sense to be in the dataset (these are set at ingest or derived):
Person:species
Participant:description
Study:guidType
Dataset:datasetGlobalID
Dataset:accessLimitations
Dataset:dataType
Dataset:accessRequirements
Observation:associated_visit
Observation:performed_by


I'm also leaving out everything from Datafile and Biospecimen because I don't know how to handle these; I suspect they are generated during ingest.

Observation value information will be dropped as well in favor of a single value for given observation data. We'll also start by using the same general layout of the initial toy data set because I believe it to share data layout with TOPMed studies. This removes these fields:
Observation:value_string
Observation:value_boolean
Observation:value_quantity
Observation:value_enum


## Selected Fields from Models
| **BDC-HM**                          | **INCLUDE Model**                   |
|-------------------------------------|-------------------------------------|
| Demography:sex                      | Participant:sex                     |
| Demography:ethnicity                | Participant:ethnicity               |
| Demography:race                     | Participant:race                    |
| Participant:age_at_index            | Participant:ageAtFirstPatientEngagement |
| Visit:visit_category                |                                     |
| Condition:condition_status          | Participant:downSyndromeStatus      |
| Condition:condition_severity        |                                     |
|                                     | Participant:firstPatientEngagementEvent |
| ResearchStudy:name                  | Study:studyTitle                    |
|                                     | Study:studyCode                     |
|                                     | Study:program                       |
|                                     | Study:studyDescription              |
|                                     | Study:studyContactName              |
|                                     | Study:studyContactInstitution       |
|                                     | Study:studyContactEmail             |
|                                     | Study:researchDomain                |
|                                     | Study:participantLifespanStage      |
|                                     | Study:studyDesign                   |
|                                     | Study:clinicalDataSourceType        |
| ObservationSet:category             | Dataset:dataCategory                |
| ObservationSet:focus                |                                     |
| ObservationSet:associated_participant|                                    |
| ObservationSet:associated_visit     |                                     |
| ObservationSet:method_type          |                                     |
| ObservationSet:performed_by         |                                     |
| ObservationSet:observations         |                                     |
|                                     | Dataset:datasetGlobalId             |
|                                     | Dataset:experimentalStrategy        |
|                                     | Dataset:experimentalPlatform        |
|                                     | Dataset:accessLimitations           |
|                                     | Dataset:dataType                    |
|                                     | Dataset:accessRequirements          |
| Observation:age_at_observation      |                                     |
| Observation:category                |                                     |
|                                     | Dataset:dataCollectionStartYear     |
|                                     | Dataset:dataCollectionEndYear       |
| Observation:observation_type        |                                     |
| Observation:method_type             |                                     |
| Observation:focus                   |                                     |

This is more fields than I had initially hoped for but a lot of this is Study, Dataset, or Observation parameters that can likely be grouped in ways that don't make them too difficult to understand.

## Model Selected vs TOPMed Harmonized
| **TOPMed Harmonized**               | **BDC-HM or INCLUDE Model**         |
|-------------------------------------|-------------------------------------|
| annotated_sex_1                     | Demography:sex                      |
| ethnicity                           | Demography:ethnicity                |
| race_us_1                           | Demography:race                     |
| age_at_index?                       | Participant:age_at_index            |
| VISIT                               | Visit:visit_category                |
| [ select multiple ]                 | Condition:condition_status          |
| [ per selections ]                  | Condition:condition_severity        |
| date1                               | Participant:firstPatientEngagementEvent |
| "ToyData_2"                         | ResearchStudy:name                  |
| "ToyStudy"                          | Study:studyCode                     |
| "ToyProgram"                        | Study:program                       |
| "A toy dataset for testing"         | Study:studyDescription              |
| "Corey Cox"                         | Study:studyContactName              |
| "University of North Carolina"      | Study:studyContactInstitution       |
| ""                                  | Study:studyContactEmail             |
| "General"                           | Study:researchDomain                |
| "Adult"                             | Study:participantLifespanStage      |
| "None"                              | Study:studyDesign                   |
| "None"                              | Study:clinicalDataSourceType        |
| [ select multiple ]                 | ObservationSet:category             |
|          |                          | ObservationSet:focus                |
|          |                          | ObservationSet:associated_participant|
|          V                          | ObservationSet:associated_visit     |
|                                     | ObservationSet:method_type          |
|                                     | ObservationSet:performed_by         |
|                                     | ObservationSet:observations         |
|                                     | Dataset:datasetGlobalId             |
|                                     | Dataset:experimentalStrategy        |
|                                     | Dataset:experimentalPlatform        |
|                                     | Dataset:accessLimitations           |
|                                     | Dataset:dataType                    |
|                                     | Dataset:accessRequirements          |
|                                     | Observation:age_at_observation      |
|                                     | Observation:category                |
|                                     | Dataset:dataCollectionStartYear     |
|                                     | Dataset:dataCollectionEndYear       |
|                                     | Observation:observation_type        |
|                                     | Observation:method_type             |
|                                     | Observation:focus                   |

For condition and related slots we should select a few conditions to model on. For ObservationSet, Observation, and DataSet we should select a significant group of observations (5-10), grouped as reasonable into datasets of observation sets.

# Demographics
Here are the selections for demographics.

sex
race
ethnicity


# Select Fields for Condition and ObservationSet
Initial selection of fields:
Condition:
Asthma
Stroke
Heart Disease (Cardiac conditions)
Diabetes

Measurement:
Blood Pressure
Cholesterol
Use of Inhaler

bmi_baseline_1
current_smoker_baseline_1
ever_smoker_baseline_1
height_baseline_1
weight_baseline_1
sleep_duration_1

Creatinine in blood
