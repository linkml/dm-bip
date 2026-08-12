# Mapping Provenance

`dm-bip extract-mapping-provenance` reads linkml-map transformation specs and reports
which dbGaP studies, datasets (`pht` accessions), and variables (`phv` accessions)
contribute to each harmonized concept, by extracting the specs' `populated_from` values.
This is the *mapping* provenance layer of
[linkml/dm-bip#352](https://github.com/linkml/dm-bip/issues/352) — available from the
specs alone, as opposed to the *execution* provenance recorded at pipeline runtime.

## Usage

```sh
# One directory of specs (one study), YAML to stdout
dm-bip extract-mapping-provenance path/to/priority_variables_transform/ARIC-ingest

# Several studies at once, written to a file
dm-bip extract-mapping-provenance path/to/priority_variables_transform -o mapping-prov.yaml
```

Directories are searched recursively for `*.yaml` spec files. Identifiers for specs and
derived entities are formed from paths relative to the deepest common directory of the
inputs.

## Output

A YAML list of study documents conforming to the
[mapping-provenance schema](https://github.com/linkml/dm-bip/blob/main/src/dm_bip/mapping_prov/schema/mapping_prov_schema.yaml),
an extension of the [PROV LinkML schema](https://github.com/diatomsRcool/prov-schema)
expressing the dbGaP granularity issue #352 calls for. Following the direction of
[prov-schema#10](https://github.com/diatomsRcool/prov-schema/issues/10), everything is a
generic PROV `Entity` typed by a controlled vocabulary (`entity_type`) rather than
dedicated classes, and containment — which carries the study → dataset → variable
alignment — uses a `dcterms:hasPart` relation, rendered nested:

```yaml
- id: bdchm:Study/phs000280
  entity_type: study
  name: Atherosclerosis Risk in Communities (ARIC)
  has_part:
  - id: dbgap:pht004063
    entity_type: dataset
    name: pht004063
    has_part:
    - id: dbgap:phv00204719
      entity_type: variable
      name: phv00204719
      description: Source for Quantity.value_decimal
  - id: dmcprov:ARIC-ingest/bmi.yaml
    entity_type: transformation_spec
    name: ARIC-ingest/bmi.yaml
  - id: dmcprov:ARIC-ingest/bmi/MeasurementObservation/pht004063
    name: MeasurementObservation derived from pht004063 (ARIC-ingest/bmi.yaml)
    derived_from:
    - dbgap:pht004063
    - dbgap:phv00204719
    - dmcprov:ARIC-ingest/bmi.yaml
```

A study's `has_part` holds its datasets (each nesting its variables), its transformation
specs, and its derived entities, in that order. Each derivation fragment in a spec
becomes one derived entity, keeping the pairing between a dataset and the variables
drawn from it (one fragment per contributing dataset/exam). The `derived_from` list
names the source dataset, the source variables, and the transformation spec itself —
value-level mapping detail (e.g. `0 → ABSENT`) intentionally lives only in the spec,
which the provenance points back to.

## Study identity

The study rooting each document comes from the spec directory's `researchstudy.yaml`
(its `accession_number` constant, e.g. `phs000280`, becomes `bdchm:Study/phs000280`).
Directories without one fall back to a placeholder study named after the directory, with
a warning.

Variables referenced only inside `expr` expressions (e.g. join keys such as
`{phv00204812}`) are also captured as sources; their `description` is marked
`(via expression)`.

## Spec identifiers

When a spec file is read from a clean git checkout with a GitHub `origin` remote, it is
identified by a commit-pinned permalink — e.g.
`https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/blob/<commit>/priority_variables_transform/ARIC-ingest/bmi.yaml`
— an immutable URL naming the spec exactly as it was read. Specs that are untracked or
locally modified (where a commit URL would misrepresent their content), or not in a
GitHub checkout at all, fall back to local-path `dmcprov:` identifiers with a warning.
Derived-entity identifiers always use the `dmcprov:` form: they are this tool's records,
not repository artifacts.

## Regenerating the datamodel

The extractor constructs classes generated from the LinkML schema. After editing
`mapping_prov_schema.yaml`, regenerate with `make datamodel` (requires network access:
the schema imports the upstream PROV schema by URL).
