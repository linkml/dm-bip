# Required elements of the INCLUDE model

We need to identify required elements of the [INCLUDE model](https://github.com/include-dcc/include-linkml).

Previously this was in a numer of different yaml files. Now the INCLUDE model uses a single data file. Here are the fields based on that file.

- Study
    - studyCode
    - studyTitle
    - program
    - studyDescription
    - studyContactName
    - studyContactInstitution
    - studyContactEmail
    - researchDomain
    - participantLifespanStage
    - studyDesign
    - clinicalDataSourceType
    - guidType
    - principalInvestigatorName
    - expectedNumberOfParticipants
- Dataset
    - datasetName
    - datasetGlobalId
    - expectedNumberOfFiles
    - dataCollectionStartYear
    - dataCollectionEndYear
    - dataCategory
    - dataType
    - accessLimitations
    - accessRequirements
- Participant
    - participantGlobalId
    - participantExternalId
    - familyType
    - familyRelationship
    - sex
    - race
    - ethnicity
    - downSyndromeStatus
    - ageAtFirstPatientEngagement
    - firstPatientEngagementEvent
- Biospecimen
    - participantGlobalId
    - participantExternalId    
    - sampleGlobalId
    - sampleExternalId
    - sampleType
    - sampleAvailability
- Datafile
    - fileName
    - fileGlobalId
    - fileS3Location
    - drsUri
    - dataAccess
    - dataCategory
    - fileFormat


 ## Notes
 Here are some notes from the evaluation of the INCLUDE data model

 ### Dataset
 The slots datasetGlobalID, expectedNumberOfFiles, dataCollectionStartYear, accessLimitations, and accessRequirements are marked required=false with a note to change to true when something is figured out; I'm going to consider these true for simplicity.

 ### Condition
The Condition class in include_participant.yaml has annotations:required with a value of tag=required, value=false, which appears to mean that Condition is not required as all of the slots in condition are not required.

### Datafile
Muliple slots in the Datafile class are in a state of TBD usage so I think we should exclude those: participantGlobalId, participantExternalId, sampleGlobalId, and sampleExternalId.
