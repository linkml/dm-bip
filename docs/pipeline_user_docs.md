# User Documentation for LinkML Data Model Ingest Pipeline Users

## 	Set-up Local Environment

- Clone the repo at: https://github.com/linkml/dm-bip 
- Follow the instructions in the repo README (https://github.com/linkml/dm-bip?tab=readme-ov-file#overview) up to the “Development” section.
- NOTE: For Mac users, the preferred environment is to use pyenv. However, currently for Windows users, specifically WSL, if you already have Conda installed there are instructions to install the environment for the dm-bip repo using Conda. Additionally for Windows users, Git Bash is required in order to avoid file path issues in commands due to differences between Windows and Mac/Linux.
- NOTE: If you have not previously installed `make` this should also be installed.


## Create data directories
The overall set of directories will be up to each user's discretion. However, a structure to consider is to create the following directories under the `data` directory. Note, the `data` directory is not under git version control. First, under the `data` directory create a directory for the study you will be processing and then create the following dirctories:

```
├── data_dictionary
├── conditions_data
├── target_schema
├── linkml_formatted_data
├── model_transformation
├── raw_data
└── implicit_study_specific_model
```

Directory description:
- data_dictionary: study data dictionary files
- conditions_data: results of annotated conditions data
- target_schema: the tagged release version of the target LinkML schema
- linkml_formatted_data: data harmonized to the target LinkML model
- model_transformation: mapping transformation specification files
- raw_data: the original study data
	- TSV: the “raw” data files^1^
	- TSV_Preprocessed: preprocessed study data
- implicit_study_specific_model (optional): data transformed to LinkML, but not harmonized to target LinkML model

1 - the “raw” files are files that have been prepared for use in the data ingest pipeline as described below


## Prepare “raw” files for data ingest
- The files used as input into the LinkML data ingest pipeline at this time require a few minimal changes:
	- The file must be a “.tsv” file. You can convert a file from CSV to TSV using this python one-liner: 
	```
	python -c "import pandas as pd; pd.read_csv('YOUR-FILE-NAME.csv').to_csv('YOUR-FILE-NAME.tsv', sep='\t', index=False)"
	```
	Remember to replace YOUR-FILE-NAME with your actual filename. 
	- The filenames must be all lowercase.
	- The filenames must not contain any spaces or special characters.


## Create the implicit study specific “mini-model”
- The LinkML data ingest pipeline can be run over the files generally without modification of the data content in the files. However, you may want to pre-process the files to remove PHI, etc.
- Run the pipeline as:
```
make pipeline DM_INPUT_DIR=data/YOUR-STUDY-DIRECTORY/raw_data/TSV DM_SCHEMA_NAME=YOUR-STUDY-NAME_INCLUDE_SCHEMA DM_OUTPUT_DIR=data/YOUR-STUDY-DIRECTORY/study_specific_model
```
	- Explanation of command parameters:
	- `DM_INPUT_DIR`:  this is the directory with your “raw” files
	- `DM_SCHEMA_NAME`: this is the name to call the resulting LinkML schema file. It will be appended with “.yaml” by the `make` goal
	- `DM_OUTPUT_DIR`: the directory to save the LinkML schema file
- This step can be done initially to create the implicit study specific model and validate the files against this model. Various file preprocessing steps may be needed to transform the “raw” files into a format suitable for the pipeline and this step then needs to be run again on the preprocessed files in order to create the implicit study specific model. Examples of preprocessing that may be needed are to combine all data columns for a given target LinkML model class into one data file or to annotate conditions with ontology terms.


## Create Transformed Files
- Since the data for each class in the transformation specification currently needs to be in one data file and the data for each slot needs to be within one column in the data file, the input files may need to be preprocesed to combine columns across data files.
- The preprocessing can be done using any data science methods of the user’s choice e.g. R, pandas, dbt, etc.
- Once the transformed files are generated, run the pipeline using these preprocessed files to create a new implicit study specific model files.

```
make pipeline DM_INPUT_DIR=data/YOUR-STUDY/raw_data/TSV DM_SCHEMA_NAME=YOUR_SCHEMA DM_OUTPUT_DIR=YOUR-OUTPUT-DIRECTORY -B
```


## Prepare Transformation Mapping specification file
- The current suggestion is to create one mapping transformation specification file for each class in the model. The transformation mapping specification is formatted as a YAML file.


### LinkML Transformation Spec
- The LinkML transformation specification consists of a collection of ClassDerivation and SlotDerivation objects. See the [LinkML-Map documentation](https://linkml.io/linkml-map/) for more information.
- The file is formatted as:
```
- class_derivations:
    ClassName:
      populated_from: filename
      slot_derivations:
```
- The `ClassName` is the name of your LinkML model class, e.g. Participant.
- The `populated_from` directly under the `ClassName` field indicates what file the data is from.
- The `slot_derivations` are the LinkML model slots for the class.
- Each `class_derivation` block represented in the transformation spec represents one row in your input data file.


#### Slot Derivations
- The slot derivations represent the LinkML model slots and provide the mapping between the “raw” data file to the target LinkML model.
- For example, in the example below this indicates that the `participantExternalId` is populated from the id column in the “raw” data file.
```
slot_derivations:
        participantExternalId:
          populated_from: id
```


#### Slot Values
- The data to populate a slot must be found within one column in one “raw” data file or be specified to be a hard-coded value.
- Slot values can also be dynamically created, based on the single column value, using value mappings, expressions, or unit conversions.
- Examples:
	```
	slot_derivations:
		familyType:
			value: Example Family type --> a hard-coded, constant value
		sex:
			populated_from: gender
			value_mappings:
				'1': male --> '1' in "raw" data file maps to 'male'
				'2': female
	```

