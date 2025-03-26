# Required Elemenets of the BDC Model

I need to research and document the required elements of the BioData Catalyst Harmonized Model (BDC-HM).

Looking at the YAML and data model, as well as having an LLM analyze it, I have determined these fields to be a basal requirement for data that would be converted to the BDC-HM.

These top level entities are the minimum required, each will need to have it's minimum data fields represented as well.
1. Person - The basis of almost all of this data is a person with some form of number to identify that person without sensitive information
2. Demography - Demographic information about a person and study participant
3. Participant - Information about a person participating in a study, with study based information such as the age of the participation when the study was conducted
	1. Consent - 
4. Research Study - The information about the research study or studies in the dataset and the individual participants linked with these studies, i.e age and consent
5. Condition - Any conditions of interest that a participant in the study may have
6. Measurement - Any measurements taken on the participant

In addition, some additional entities are likely interest and should likely be included.
 1. Visit - Information about the visit or visits the participant had for the study
 2. Questionnaire - Any information recorded through questionnaires
 3. Procedure - 
 4. Observation -

