#!/usr/bin/env python3

import click
from datetime import datetime
import uuid
import logging
from oaklib import get_adapter
from oaklib.datamodels.search import SearchProperty, SearchConfiguration
from oaklib.implementations.sqldb.sql_implementation import SqlImplementation
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
import sys
import yaml
from pathlib import Path
import os
import openai
import json
import re


openai.api_key = os.getenv("OPENAI_API_KEY")


__all__ = [
    "main",
]


# Explicitly remove handlers that may have been added automatically
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure logger
logger = logging.getLogger("harmonica")

# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s.%(msecs)03d [%(levelname)s] (%(module)s) (%(name)s): %(message)s",
#     datefmt='%Y-%m-%d,%H:%M:%S',
#     handlers=[
#         logging.FileHandler("error.log"),
#         logging.StreamHandler()
#     ],
#     force=True
# )

# Silence root logger
logging.getLogger().setLevel(logging.WARNING)

# Silence oak logger
logging.getLogger("sql_implementation").setLevel(logging.WARNING)


# Silence SQLAlchemy and related sub-loggers
for name in [
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.engine.Engine",
    "sqlalchemy.pool"
]:
    logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger(name).propagate = False


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
# @click.version_option(__version__)
def main(verbose: int, quiet: bool):
    """
    The main click group containing with parameters for logging levels.
    :param verbose: Levels of log messages to display.
    :param quiet: Boolean to be quiet or verbose.
    """
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)


def clear_cached_db(ontology_id: str):
    """Clear ontology database files (.db and .db.gz) cached by OAK."""
    base_path = Path.home() / ".data" / "oaklib"
    db_files = [
        base_path / f"{ontology_id}.db",
        base_path / f"{ontology_id}.db.gz"
    ]

    for file in db_files:
        logger.debug("DB refresh set to True.")
        if file.exists():
            logger.debug(f"Removing cached DB: {file}")
            file.unlink()
        else:
            logger.debug(f"No cached DB found at: {file}")




def fetch_ontology(ontology_id: str, refresh: bool = False) -> SqlImplementation:
    """
    Download ontology of interest and convert to SQLite database.
    :param ontology_id: The OBO identifier of the ontology.
    :param refresh: Whether to force refresh the cached ontology.
    :returns adapter: The connector to the ontology database.
    """

    if refresh:
        clear_cached_db(ontology_id)

    # Download and cache the ontology if not already present
    adapter = get_adapter(f"sqlite:obo:{ontology_id}")

    # Display ontology metadata
    try:
        for ont in adapter.ontologies():
            metadata = adapter.ontology_metadata_map(ont)
            version_iri = metadata.get("owl:versionIRI", "unknown")
            logger.debug(f"{ontology_id.upper()} version: {version_iri}")
    except Exception as e:
        logger.debug(f"Could not fetch version metadata for {ontology_id}: {e}")

    return adapter




def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        click.echo(f"Error reading config file: {e}", err=True)
        sys.exit(1)

    # Basic validation
    required_keys = ["ontologies", "columns_to_annotate"]
    for key in required_keys:
        if key not in config:
            click.echo(f"Missing required config key: {key}", err=True)
            sys.exit(1)

    if not isinstance(config["ontologies"], list) or not all(isinstance(o, str) for o in config["ontologies"]):
        click.echo("Config error: 'ontologies' should be a list of strings", err=True)
        sys.exit(1)

    if not isinstance(config["columns_to_annotate"], list) or not all(isinstance(c, str) for c in config["columns_to_annotate"]):
        click.echo("Config error: 'columns_to_annotate' should be a list of strings", err=True)
        sys.exit(1)

    return config


def search_ontology(ontology_id: str, adapter: SqlImplementation, df: pd.DataFrame, columns: list, config: dict) -> pd.DataFrame:
    """
    Search for exact matches to the ontology term label.
    :param adapter: The connector to the ontology database.
    :param df: Dataframe containing terms to search and find matches to the ontology.
    """

    ontology_prefix = 'hpo' if ontology_id.lower() == 'hp' else ontology_id
    exact_search_results = []

    column_to_use = columns[0]  # assuming just one for now

    # Create a tqdm instance to display search progress
    #progress_bar = tqdm(total=len(df), desc="Processing Rows", unit="row")

    for index, row in df.iterrows():
        for result in adapter.basic_search(row[column_to_use], config=config):
            exact_search_results.append([row["UUID"], result, adapter.label(result)])
            # Update the progress bar
            #progress_bar.update(1)

    # Close the progress bar
    #progress_bar.close()

    # Convert search results to dataframe
    results_df = pd.DataFrame(exact_search_results)
    logger.debug(results_df.head())

    # Add column headers
    if results_df.empty:
        results_df = pd.DataFrame(columns=['UUID', f'{ontology_prefix}_result_curie', f'{ontology_prefix}_result_label'])
    else:
        results_df.columns = ['UUID', f'{ontology_prefix}_result_curie', f'{ontology_prefix}_result_label']

    # Filter rows to keep those where '{ontology}_result_curie' starts with the "ontology_id", keep in mind hp vs. hpo
    # TODO: Decide whether these results should still be filtered out
    results_df = results_df[results_df[f'{ontology_prefix}_result_curie'].str.startswith(f'{ontology_id}'.upper())]

    # Group by 'UUID' and aggregate curie and label into lists
    search_results_df = results_df.groupby('UUID').agg({
        f'{ontology_prefix}_result_curie': list,
        f'{ontology_prefix}_result_label': list
    }).reset_index()

    # Convert lists to strings
    search_results_df[f'{ontology_prefix}_result_curie'] = search_results_df[f'{ontology_prefix}_result_curie'].astype(str).str.strip('[]').str.replace("'", "")
    search_results_df[f'{ontology_prefix}_result_label'] = search_results_df[f'{ontology_prefix}_result_label'].astype(str).str.strip('[]').str.replace("'", "")

    # TODO: Maintain individual columns of result_match_type for each ontology searched!
    # Add column to indicate type of search match
    if str(config.properties[0]) == 'LABEL':
        search_results_df[f'{ontology_prefix}_result_match_type'] = np.where(
            search_results_df[f'{ontology_prefix}_result_curie'].notnull(), f'{ontology_prefix.upper()}_EXACT_LABEL', '')
    
    if str(config.properties[0]) == 'ALIAS':
        search_results_df[f'{ontology_prefix}_result_match_type'] = np.where(
            search_results_df[f'{ontology_prefix}_result_curie'].notnull(), f'{ontology_prefix.upper()}_EXACT_ALIAS', '')

    return search_results_df



def clean_json_response(content: str) -> str:
    """
    Clean common formatting issues in GPT output before JSON parsing.
    """
    # Replace smart quotes with standard quotes
    content = content.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")

    # Strip any leading junk like ```json ... ```
    content = re.sub(r"^```(json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content.strip())

    return content


def get_alternative_names(term: str) -> dict:
    prompt = (
        f"For the term '{term}', return a JSON object with three keys:\n"
        "- 'input': the original term\n"
        "- 'alt_names': a list of up to five alternative names\n"
        "- 'source': the string 'openai'\n\n"
        "Example format:\n"
        "{\n"
        '  "input": "hole in heart",\n'
        '  "alt_names": [\n'
        '    "atrial septal defect",\n'
        '    "ventricular septal defect",\n'
        '    "congenital heart defect",\n'
        '    "septal defect",\n'
        '    "cardiac shunt"\n'
        "  ],\n"
        '  "source": "openai"\n'
        "}"
    )


    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150,
        )
        content = response['choices'][0]['message']['content']
        cleaned = clean_json_response(content)
        result = json.loads(cleaned)
        return result
    except json.JSONDecodeError:
        logger.debug(f"Could not parse JSON: {content}")
        return []
    except Exception as e:
        logger.debug(f"Error retrieving alt names for '{term}': {e}")
        return []


def generate_uuid() -> str:
    """Function to generate UUID"""
    return str(uuid.uuid4())


def _clean_up_columns(df: pd.DataFrame, ontology_id: str) -> pd.DataFrame:
    """
    Copy over the search results to the columns from the input dataframe
    amd remove the extra columns added with the search results.
    :param df: The dataframe from the merge of the search results with the original dataframe.
    :param ontology_id: The ontology identifier, ie. the ontology being searched  
    """
    ontology_prefix = 'hpo' if ontology_id.lower() == 'hp' else ontology_id

    # Handle clean-up after a second round of synonym search
    if f'{ontology_prefix}_result_match_type_x' in df.columns and f'{ontology_prefix}_result_match_type_y' in df.columns:
        # Copy result label values to original df column and then drop result column
        df[f'{ontology_prefix}Label'] = np.where(df[f'{ontology_prefix}_result_label'].notnull(), df[f'{ontology_prefix}_result_label'], df[f'{ontology_prefix}Label'])
        df.drop([f'{ontology_prefix}_result_label'], axis=1, inplace=True)

        # Copy result curie values to original df column and then drop result column
        df[f'{ontology_prefix}Code'] = np.where(df[f'{ontology_prefix}_result_curie'].notnull(), df[f'{ontology_prefix}_result_curie'], df[f'{ontology_prefix}Code'])
        df.drop([f'{ontology_prefix}_result_curie'], axis=1, inplace=True)

        # Copy type of result match to original df column and then drop result column and rename original df column
        df[f'{ontology_prefix}_result_match_type_x'] = np.where(df[f'{ontology_prefix}_result_match_type_y'].notnull(), df[f'{ontology_prefix}_result_match_type_y'], df[f'{ontology_prefix}_result_match_type_x'])
        df.drop([f'{ontology_prefix}_result_match_type_y'], axis=1, inplace=True)
        df = df.rename(columns={f'{ontology_prefix}_result_match_type_x': f'{ontology_prefix}_result_match_type'})
    else:
        # Update values in the existing columns
        df[f'{ontology_prefix}Label'] = df[f'{ontology_prefix}_result_label']
        df[f'{ontology_prefix}Code'] = df[f'{ontology_prefix}_result_curie']
    
        # Drop the search_results columns
        df.drop([f'{ontology_prefix}_result_label'], axis=1, inplace=True)
        df.drop([f'{ontology_prefix}_result_curie'], axis=1, inplace=True)


    return df


def _check_ontology_versions(ontology_ids: tuple):
    """
    Check and print the cached ontology versions for each ID.
    :param ontology_ids: Tuple of ontology IDs to check.
    """
    logger.debug("\nChecking local ontology versions...")
    for oid in ontology_ids:
        try:
            adapter = get_adapter(f"sqlite:obo:{oid}")
            for ont in adapter.ontologies():
                meta = adapter.ontology_metadata_map(ont)
                version = meta.get("owl:versionIRI", "Unknown")
                logger.debug(f"  - {oid.upper()}: {version}")
        except Exception as e:
            logger.debug(f"  - {oid.upper()}: Error loading version ({e})")



def custom_join(series):
    non_empty = series.dropna().astype(str).str.strip()
    non_empty = [v for v in non_empty if v]
    unique_vals = list(dict.fromkeys(non_empty))
    return ', '.join(unique_vals) if unique_vals else ''



@main.command("annotate")
@click.option('--config', type=click.Path(exists=True), help='Path to YAML config file')
@click.option('--input_file', type=click.Path(exists=True), required=True, help="Path to data file to annotate")
@click.option('--output_dir', type=click.Path(), required=False, help='Optional override for output directory')
@click.option('--refresh', is_flag=True, help='Force refresh of ontology cache')
@click.option('--no_openai', is_flag=True, help='Disable OpenAI-based fallback searches')
def annotate(config: str, input_file: str, output_dir: str, refresh: bool, no_openai: bool):
    """
    Annotate a data file with ontology terms.
    :param config: Path to the config file.
    :param data_filename: The name of the file with terms to search for ontology matches.
    """

    config_data = load_config(config)

    ontologies = config_data["ontologies"]
    columns = config_data["columns_to_annotate"]

    if not ontologies or not columns:
        raise click.ClickException("Config file must contain 'ontologies' and 'columns_to_annotate'.")
    
    # Determine output directory from CLI or config or fallback
    output_dir = Path(output_dir or config_data.get("output_dir", "data/output/")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Using ontologies: {ontologies}")
    click.echo(f"Annotating columns: {columns}")
    click.echo(f"Output directory: {output_dir}")
    if refresh:
        click.echo("Refresh mode enabled")

    oid = tuple(o.lower() for o in config_data["ontologies"])
 
    filename_prefix = '_'.join(oid)

    # Get the current formatted timestamp
    timestamp = datetime.now()
    formatted_timestamp = timestamp.strftime("%Y%m%d-%H%M%S")

    # Read in the data file
    file_path = Path(input_file).resolve()

    data_df = pd.read_csv(file_path, sep='\t')
    logger.debug(data_df[columns])
    
    # Add a new column 'UUID' with unique identifier values
    data_df['UUID'] = data_df.apply(lambda row: generate_uuid(), axis=1)
    logger.debug(data_df.nunique())
    logger.info("Number of total rows in dataframe: %s", len(data_df))

    # Check ontology versions 
    _check_ontology_versions(oid)


    # Collect all annotation results
    all_final_results = []

    for ontology_id in oid:
        ontology_prefix = 'hpo' if ontology_id.lower() == 'hp' else ontology_id
        adapter = fetch_ontology(ontology_id, refresh=refresh)

        # === Exact LABEL match ===
        label_config = SearchConfiguration(properties=[SearchProperty.LABEL], force_case_insensitive=True)
        label_hits_df = search_ontology(ontology_id, adapter, data_df, columns, label_config)
        label_hits_df["annotation_source"] = "oak"
        label_hits_df["annotation_method"] = "exact_label"
        label_hits_df["ontology"] = ontology_id.lower()

        # Filter unmatched
        matched_uuids_label = set(label_hits_df["UUID"])
        filtered_df = data_df[~data_df["UUID"].isin(matched_uuids_label)]

        # === Synonym match ===
        synonym_config = SearchConfiguration(properties=[SearchProperty.ALIAS], force_case_insensitive=True)
        synonym_hits_df = search_ontology(ontology_id, adapter, filtered_df, columns, synonym_config)
        synonym_hits_df["annotation_source"] = "oak"
        synonym_hits_df["annotation_method"] = "exact_synonym"
        synonym_hits_df["ontology"] = ontology_id.lower()

        matched_uuids_syn = set(synonym_hits_df["UUID"])
        filtered_df = filtered_df[~filtered_df["UUID"].isin(matched_uuids_syn)]

        # === OpenAI alternative names ===
        openai_hits = []
        if not no_openai:
            for term in tqdm(filtered_df[columns[0]].dropna().unique()):
                # Normalize the term
                match = re.match(r"^(.*?)\s*\((\w{3,5})\)$", term.strip())
                normalized_term = match.group(1).strip() if match else term.strip()

                alt_response = get_alternative_names(normalized_term)
                if not alt_response:
                    continue

                uuid_series = filtered_df[filtered_df[columns[0]] == term]["UUID"]
                if uuid_series.empty:
                    continue
                uuid = uuid_series.iloc[0]

                found_match = False

                for alt in alt_response.get("alt_names", []):
                    # First: exact label match
                    df_search = pd.DataFrame({"UUID": [uuid], columns[0]: [alt]})
                    label_match_df = search_ontology(ontology_id, adapter, df_search, columns, label_config)
                    if not label_match_df.empty:
                        label_match_df["annotation_source"] = "openai"
                        label_match_df["annotation_method"] = "alt_term_label"
                        label_match_df["original_term"] = normalized_term
                        label_match_df["ontology"] = ontology_id.lower()
                        openai_hits.append(label_match_df)
                        found_match = True
                        break

                    # Then: synonym match if label fails
                    synonym_match_df = search_ontology(ontology_id, adapter, df_search, columns, synonym_config)
                    if not synonym_match_df.empty:
                        synonym_match_df["annotation_source"] = "openai"
                        synonym_match_df["annotation_method"] = "alt_term_synonym"
                        synonym_match_df["original_term"] = normalized_term
                        synonym_match_df["ontology"] = ontology_id.lower()
                        openai_hits.append(synonym_match_df)
                        found_match = True
                        break

                if not found_match:
                    openai_hits.append(pd.DataFrame([{
                        "UUID": uuid,
                        "annotation_source": "openai",
                        "annotation_method": "no_match",
                        "original_term": normalized_term,
                        "alt_names": ', '.join(alt_response.get("alt_names", [])),
                        "ontology": ontology_id.lower()
                    }]))


        openai_hits_df = pd.concat(openai_hits, ignore_index=True) if openai_hits else pd.DataFrame()
        results_sources = [label_hits_df, synonym_hits_df]
        if not openai_hits_df.empty:
            results_sources.append(openai_hits_df)

        results_df = pd.concat(results_sources, ignore_index=True)
        if not results_df.empty:
            all_final_results.append(results_df)

    # === Exit if no results  ===
    if not all_final_results:
        logger.warning("No annotation results found for any ontology.")
        return

    # === Combine all results ===
    full_results = pd.concat(all_final_results, ignore_index=True)

    # === Merge with input metadata ===
    data_df["UUID"] = data_df["UUID"].astype(str).str.strip()
    full_results["UUID"] = full_results["UUID"].astype(str).str.strip()
    final_df = pd.merge(data_df, full_results, on="UUID", how="left")

    # Drop duplicated or unnecessary columns
    final_df.drop(columns=["source_column_value_y", "original_term"], inplace=True, errors="ignore")

    # === Save final output ===
    final_df = final_df.fillna("")
    output_path = Path(output_dir) / f"{filename_prefix}-combined_ontology_annotations-{formatted_timestamp}.tsv"
    final_df.to_csv(output_path, sep='\t', index=False)
    print(f"\nAnnotation results written to: {output_path}")


if __name__ == "__main__":
    main()