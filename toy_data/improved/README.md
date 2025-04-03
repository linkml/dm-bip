# Creating a good toy data set
In order to create a useful and robust toy data set we need to gather some information about the systems we will be transforming the data to and the data we will be transforming.

 1. Gather the required fields from the BioData Catalyst Harmonized Model and the Include LinkML Model.
 2. Identify those data fields in the BDCHM Prioritized variables
 3. Review other prioritized variables to identify the most valuable to develop and test on.
 4. Use the above as a list variables for the toy synthetic data set
 5. Provide the list of fields for synthetic data to an LLM with descriptions of what we would like to generate and have the LLM generate a small synthetic data set.

 ## Fields from BDC-HM and INCLUDE

| **BDC-HM**                    |
|-------------------------------------|
| Person:species                      |
| Person:identity                     |
| Demography:sex                      |
| Demography:ethnicity                |
| Demography:race                     |
| Demography:identity                 |
| Demography:associated_participant   |
| Participant:description             |
| Participant:member_of_research_study|
| Participant:age_at_index            |
| Participant:associated_person       |
| Participant:identity                |
| ResearchStudy:name                  |
| ResearchStudy:identity              |
| Visit:visit_category                |
| Visit:associated_participant        |
| Condition:condition_status          |
| Condition:condition_severity        |
| Condition:associated_participant    |
| Condition:associated_visit          |
| Condition:identity                  |
| ObservationSet:category             |
| ObservationSet:focus                |
| ObservationSet:associated_participant|
| ObservationSet:associated_visit     |
| ObservationSet:method_type          |
| ObservationSet:performed_by         |
| ObservationSet:observations         |
| Observation:age_at_observation      |
| Observation:category                |
| Observation:observation_type        |
| Observation:method_type             |
| Observation:focus                   |
| Observation:associated_participant  |
| Observation:associated_visit        |
| Observation:performed_by            |
| Observation:value_string            |
| Observation:value_boolean           |
| Observation:value_quantity          |
| Observation:value_enum              |



| **INCLUDE Model**                   |
|-------------------------------------|
| Study:studyCode                     |
| Study:studyTitle                    |
| Study:program                       |
| Study:studyDescription              |
| Study:studyContactName              |
| Study:studyContactInstitution       |
| Study:studyContactEmail             |
| Study:researchDomain                |
| Study:participantLifespanStage      |
| Study:studyDesign                   |
| Study:clinicalDataSourceType        |
| Study:guidType                      |
| Dataset:studyCode                   |
| Dataset:datasetName                 |
| Dataset:datasetGlobalId             |
| Dataset:expectedNumberOfFiles       |
| Dataset:dataCollectionStartYear     |
| Dataset:dataCollectionEndYear       |
| Dataset:dataCategory                |
| Dataset:dataType                    |
| Dataset:experimentalStrategy        |
| Dataset:experimentalPlatform        |
| Dataset:accessLimitations           |
| Dataset:accessRequirements          |
| Participant:studyCode               |
| Participant:participantGlobalId     |
| Participant:participantExternalId   |
| Participant:familyType              |
| Participant:familyRelationship      |
| Participant:sex                     |
| Participant:race                    |
| Participant:ethnicity               |
| Participant:downSyndromeStatus      |
| Participant:ageAtFirstPatientEngagement |
| Participant:firstPatientEngagementEvent |
| Biospecimen:studyCode               |
| Biospecimen:participantGlobalId     |
| Biospecimen:participantExternalId   |
| Biospecimen:sampleGlobalId          |
| Biospecimen:sampleExternalId        |
| Biospecimen:sampleType              |
| Biospecimen:sampleAvailability      |
| Biospecimen:containerAvailability   |
| Datafile:studyCode                  |
| Datafile:fileName                   |
| Datafile:fileGlobalId               |
| Datafile:fileS3Location             |
| Datafile:drsUri                     |
| Datafile:dataAccess                 |
| Datafile:dataCategory               |
| Datafile:dataType                   |
| Datafile:fileFormat                 |
