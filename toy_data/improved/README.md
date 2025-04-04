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
| ObservationSet:focus                | Dataset:dataType                    |
| ObservationSet:associated_participant|                                    |
| ObservationSet:associated_visit     | Dataset:datasetGlobalId             |
| ObservationSet:method_type          | Dataset:experimentalStrategy        |
| ObservationSet:performed_by         | Dataset:experimentalPlatform        |
| ObservationSet:observations         | Dataset:accessLimitations           |
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

This is now a good working start for the needed fields and overlap for creating the toy data set attempting to meet all the requirements for both models. Now we can gather this as a list of needed fields, remove duplicates (values stored in more than one Class to link classes together), and gather the addtional fields from the TOPMed Prioritized variables.