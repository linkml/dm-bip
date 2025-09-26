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


