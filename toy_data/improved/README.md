# Creating a good toy data set
In order to create a useful and robust toy data set we need to gather some information about the systems we will be transforming the data to and the data we will be transforming.

 1. Gather the required fields from the BioData Catalyst Harmonized Model and the Include LinkML Model.
 2. Identify those data fields in the BDCHM Prioritized variables
 3. Review other prioritized variables to identify the most valuable to develop and test on.
 4. Use the above as a list variables for the toy synthetic data set
 5. Provide the list of fields for synthetic data to an LLM with descriptions of what we would like to generate and have the LLM generate a small synthetic data set.

## Fields from BDC-HM and INCLUDE

| **BDC-HM**                    | **INCLUDE Model**                   |
|-------------------------------------|-------------------------------------|
| Person:species                      | Study:studyCode                     |
|                                     | Study:studyTitle                    |
| Demography:sex                      | Study:program                       |
| Demography:ethnicity                | Study:studyDescription              |
| Demography:race                     | Study:studyContactName              |
|                                     | Study:studyContactInstitution       |
| Demography:associated_participant   | Study:studyContactEmail             |
| Participant:description             | Study:researchDomain                |
| Participant:member_of_research_study| Study:participantLifespanStage      |
| Participant:age_at_index            | Study:studyDesign                   |
| Participant:associated_person       | Study:clinicalDataSourceType        |
|                                     | Study:guidType                      |
| ResearchStudy:name                  | Dataset:studyCode                   |
|                                     | Dataset:datasetName                 |
| Visit:visit_category                | Dataset:datasetGlobalId             |
| Visit:associated_participant        | Dataset:expectedNumberOfFiles       |
| Condition:condition_status          | Dataset:dataCollectionStartYear     |
| Condition:condition_severity        | Dataset:dataCollectionEndYear       |
| Condition:associated_participant    | Dataset:dataCategory                |
| Condition:associated_visit          | Dataset:dataType                    |
|                                     | Dataset:experimentalStrategy        |
| ObservationSet:category             | Dataset:experimentalPlatform        |
| ObservationSet:focus                | Dataset:accessLimitations           |
| ObservationSet:associated_participant| Dataset:accessRequirements          |
| ObservationSet:associated_visit     | Participant:studyCode               |
| ObservationSet:method_type          | Participant:participantGlobalId     |
| ObservationSet:performed_by         | Participant:participantExternalId   |
| ObservationSet:observations         | Participant:familyType              |
| Observation:age_at_observation      | Participant:familyRelationship      |
| Observation:category                | Participant:sex                     |
| Observation:observation_type        | Participant:race                    |
| Observation:method_type             | Participant:ethnicity               |
| Observation:focus                   | Participant:downSyndromeStatus      |
| Observation:associated_participant  | Participant:ageAtFirstPatientEngagement |
| Observation:associated_visit        | Participant:firstPatientEngagementEvent |
| Observation:performed_by            | Biospecimen:studyCode               |
| Observation:value_string            | Biospecimen:participantGlobalId     |
| Observation:value_boolean           | Biospecimen:participantExternalId   |
| Observation:value_quantity          | Biospecimen:sampleGlobalId          |
| Observation:value_enum              | Biospecimen:sampleExternalId        |
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
