# Overview - Synthetic Data Sets
The purpose of synthetic data sets in the Data Model-Based Ingestion Pipeline is two-fold. First, good synthetic data sets allow us to quickly integrate tools for the ingestion pipeline and verify they meet our needs with data that resembles the expected data. Second, synthetic data sets allow us to check this data into our repository and distribute it with the ingestion pipeline software. This second point enables using this data both to test in specific deployment environments and to use the synthetic data to develop our internal tests for the software.

# Key Features
The primary and most important feature of the synthetic Data set for the dm-bip are that they be truly synthetic. We need to simulate a real data set but be certain that nothing in our Synthetic Dataset contains any real data or anything that prevents us from sharing the data freely. This means that while we want the synthetic data to look like the real data it cannot use real data.

We need at least one synthetic data set for expansive testing of the pipeline and each tool within the pipeline suite, preferably 2.

I think the main features of a good synthetic data set are:

    Contains no real data and thereby is immune from having any sensitive or potentially sensitive information
    Substantially represents one or more real-world data set we are targeting

I'll be using this issue to track our effort in creating gold standard synthetic data sets for the Data Model-Based Ingestion Pipeline.

Some key aspects of representing a data set are:

    similar data field names (exactly the same if reasonable)
    similar data field ranges
    similar data distribution
    similar data field discrepancies
    representation of missing values within appropriate fields
    representation of data errors within appropriate fields

The synthetic dataset can be significantly smaller than the original data set as long as it presents most of the key features in the dataset, especially key challenges.

# Ideal Synthetic Data Set
An ideal synthetic data set will have the following features.

1. Contains no real data or any sensitive information
1. Substantially represents a single real data set
    1. Has the same file structure, including file names and types
    1. Substantially represents all data fields
        1. Similar number and kind of data fields
        1. Data in each field has the same range and distribution
        1. Each data field has the same data anomalies
