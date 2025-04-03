# Creating a good toy data set
In order to create a useful and robust toy data set we need to gather some information about the systems we will be transforming the data to and the data we will be transforming.

 1. Gather the required fields from the BioData Catalyst Harmonized Model and the Include LinkML Model.
 2. Identify those data fields in the BDCHM Prioritized variables
 3. Review other prioritized variables to identify the most valuable to develop and test on.
 4. Use the above as a list variables for the toy synthetic data set
 5. Provide the list of fields for synthetic data to an LLM with descriptions of what we would like to generate and have the LLM generate a small synthetic data set.

 ## Fields from BDC-HM and INCLUDE

BDC-HM
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

INCLIDE Model
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
