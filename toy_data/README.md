# Purpose of Toy Data Sets
This README.md will document the effort toward creating toy data sets for verifying that we can install an run each of the tools. The toy data sets are not intended to test any specific functionality of the tools or to demonstrate any fitness for purpose. However, ideally we may grow these tools as an initial test suite for developers to validate the tools are working as expected and providing expected functionality.

# Defining Toy Data Sets
The purpose of these toy data sets is to have a small amount of data that we can use quickly to make sure that key parts of our tool chain are working as expected. To this end, we should keep in mind two targets. First, we just need some small data set created from something easily used that can serve as a starting point for our toy data set and for tools to be integrated into the project with basic checks that they are working. Our second target is sort of an ideal toy data set. The ideal toy data set should have a limited amount of data, no restrictions on it's use, and be large and robust enough to serve as a check of key functionality in our ingest pipeline and of the models that we plan to use.

## Toy Data Set Key Features
A good toy data set should be small, cover a reasonable amount of test cases

The key features of a good toy data set
1. Multiple files similar to expected data
1. Limited to ~20-40 columns
  1. Similar to expected data
  1. Cover required target model data
  1. A few fields excluded from target model
  1. Include fields with complexity, if possible
1. Limited to ~250 rows
  1. Keep data set as small as reasonable
  1. Cover all expected data types, if possible
  1. Have expected data anomalies
  1. Expected data ranges and distributions, if possible

## Initial Toy Data Set
Our initial toy data set will be prepared from the synthetic data set provided by BioData Catalyst. This data is not especially relevant to our ideal toy data set but will give us a limited data set we can use immmediately for testing without requiring a lot of effort. A couple of quick fixes will make this a reasonable toy data set.

1. Remove all empty columns
1. Limit data to 250 rows
1. Reduce to ~20-40 columns
  1. Keep columns important to target model
  1. Keep columns with anomalies or complexity

# Description of Toy Data Sets
We intend to have  a toy data set for each meaningful step of the data ingest process. The following sections describe the target tool for the data set and the form the data set will take.

## Initial Data Cleaning
The purpose of the first data set is to show we can use a a simple Python script to do some data cleaning. Ideally, this will resemble expected incoming data but the immediate purpose is actually to use these simple cleaning scripts to produce an initial synthetic data set. See the synthetic_data/README.md for more information.
 - Filename: toy_data/01_simple_cleanup.tsv
 - Format: TSV
 - Notes: 