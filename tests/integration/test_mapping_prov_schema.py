"""
Integration test validating mapping-provenance output against its LinkML schema.

Needs network access: the mapping-provenance schema imports the upstream PROV schema
by URL, so this doubles as a check that upstream changes have not drifted away from
what the extractor (built on the generated, checked-in datamodel) produces.
"""

from pathlib import Path

import yaml
from linkml.validator import validate

from dm_bip.mapping_prov.extract import collect_spec_paths, extract_provenance, to_yaml

ROOT = Path(__file__).parents[2]
SCHEMA_PATH = ROOT / "src" / "dm_bip" / "mapping_prov" / "schema" / "mapping_prov_schema.yaml"
INPUT_DIR = ROOT / "tests" / "input" / "mapping_prov"


def test_extractor_output_validates_against_schema():
    """Every study document the extractor emits validates as an Entity instance of the schema."""
    studies = extract_provenance(collect_spec_paths([INPUT_DIR]))
    documents = yaml.safe_load(to_yaml(studies))
    assert documents, "expected at least one study document"

    for document in documents:
        report = validate(document, str(SCHEMA_PATH), target_class="Entity")
        assert report.results == [], f"{document['id']}: {[r.message for r in report.results]}"
