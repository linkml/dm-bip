# Required elements of the INCLUDE model

We need to identify required elements of the [INCLUDE model](https://github.com/include-dcc/include-linkml).

Looking through the separate YAML files, there are no actionable elements in the include_core.yaml and include_schema.yaml files. These files will be handled during data conversion as they are part of the the schema is organized rather than describing core fields that need to contain data.

Here are the remaining data files and their required classes with the classes required slots.

 - include_study.yaml
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
    - Dataset
        - studyCode
        - datasetName
        - datasetGlobalId
        - expectedNumberOfFiles
        - dataCollectionStartYear
        - dataCollectionEndYear
        - dataCategory
        - dataType
        - experimentalStrategy
        - experimentalPlatform
        - accessLimitations
        - accessRequirements
 - include_participant.yaml
    - Participant
        - studyCode
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
- include_assay.yaml
    - Biospecimen
        - studyCode
        - participantGlobalId
        - participantExternalId    
        - sampleGlobalId
        - sampleExternalId
        - sampleType
        - sampleAvailability
        - containerAvailability
    - Datafile
        - studyCode
        - fileName
        - fileGlobalId
        - fileS3Location
        - drsUri
        - dataAccess
        - dataCategory
        - dataType
        - fileFormat


 ## Notes
 Here are some notes from the evaluation of the INCLUDE data model

 ### Dataset
 The slots datasetGlobalID, expectedNumberOfFiles, dataCollectionStartYear, accessLimitations, and accessRequirements are marked required=false with a note to change to true when something is figured out; I'm going to consider these true for simplicity.

 ### Condition
The Condition class in include_participant.yaml has annotations:required with a value of tag=required, value=false, which appears to mean that Condition is not required as all of the slots in condition are not required.

### Datafile
Muliple slots in the Datafile class are in a state of TBD usage so I think we should exclude those: participantGlobalId, participantExternalId, sampleGlobalId, and sampleExternalId.
