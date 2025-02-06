1. Joint Working Repository
    1. Overall Project Documentation - Initial - Completed, Ongoing
    1. Automatic Project Documentation Deployment - Initial - In Progress
    1. Project Testing Suite - Initial - Completed, Needs Sub-tasks
    1. Automated Pre-Commit Project Testing - Completed
    1. Automated Build and Deployment Toolset - Makefile - Initial - In Progress
1. Ingest-Wide Toy Data Set
    1. Single Toy Data Set for Testing and Build Environment Validation Across Full Pipeline - Initial - In Progress
    1. Integration of Toy Data Set with Automated Build/Test Harness - Not Started
1. Ingest-Wide Synthetic Data Set
    1. Initial Synthetic Data Set Based on Data Available (BDC Synthetic) - In Progress
    1. Initial Synthetic Data Set Generated from BDC Model identified variables - Not Started
1. Schema Automator
    1. Add Schema-Automator to Project and verify it works - In Progress
        1. Had to Downgrade Python Version from 3.13 to 3.12 for now
        1. Used BDC Synthetic Data and produced Schema, no true testing or validation
        1. Add Schema-Automator usage and installation process to documentation
    1. Create Toy Data Set to verify functionality and start testing harness
    1. Validate Schema-Automator on Toy Data Set and Write Tests
    1. Create Synthetic Data Set for advanced Schema-Automator functionality
    1. Validate Schema-Automator on Synthetic Data Set and Write Tests
    1. Use Schema-Automator on a real data set and evaluate gaps
    1. Close Schema Automator Gaps
        1. Add richer data to synthetic or toy data set to represent gaps
        1. Development on Schema Automator to add functionality
        1. Development on Upstream Complex Mapper for hard to add functionality
1. Schema Sheets for Data Dictionary
    1. Add Schema Sheets as additional tool to create data models
1. Annotation of the Data
1. Schema Validator
    1. Add Schema Validator to project and verify it works
    1. Create Toy Data Set to verify functionality and start testing harness
        1. Toy Data Set resembling output of Schema Automator
        1. Toy Data Set of data input to Schema Automator to validate to Schema
        1. Valid and invalid data sets for testing
    1. Validate Schema Validator on Toy Data Set and Write Tests
    1. 
1. Schema Data Map - Yaml file that describes the map from one data model to another
    1. Manually Curated data map from BDC Data Model Team
    1. Attempt Automatic generation of map from LLM working group
1. LinkML Mapper - Doing the Transformation
    1. Add LinkML Mapper to Project and verify it works
    1. 
1. Simple Data Cleaner
    1. Simple scripts necessary for Data cleaning outside of ingest pipeline
        1. Poorly formatted Enums (Male, male, M, 1 - all meaning male)
        1. Bad missing data representation (i.e. 9 for no data)
        1. Empty columns
        1. Other bad data practices we can’t expect our ingest to handle
1. Complex Data Mapper
        1. One-off scripts on per dataset basis to map data that is too complex for the tools as the exist
1. Execution and Deployment pipeline
    1. Wrapping tools and steps into containers for deployment to cloud environments (BDC Catalyst through AWS, Google Cloud)
    1. Local system execution of pipeline in fully automated way if possible or with checkpoints and human-in-the-loop.
1. Running all of the real data through pipeline to produce a harmonized whole

