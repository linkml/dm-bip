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
    """The run activity and every study document validate against their schema classes."""
    from datetime import datetime, timezone

    from dm_bip.mapping_prov.extract import run_activity

    studies = extract_provenance(collect_spec_paths([INPUT_DIR]))
    now = datetime.now(timezone.utc)
    documents = yaml.safe_load(to_yaml([run_activity(studies, now, now), *studies]))
    assert documents, "expected at least one document"

    for document in documents:
        target_class = "Activity" if "started_at_time" in document else "Entity"
        report = validate(document, str(SCHEMA_PATH), target_class=target_class)
        assert report.results == [], f"{document['id']}: {[r.message for r in report.results]}"
