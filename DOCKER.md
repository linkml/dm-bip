# dm-bip Docker Image

The dm-bip Docker image supports two execution modes for harmonizing BioData
Catalyst (BDC) cohort data:

| Mode | Entry point | When to use |
|---|---|---|
| **Single Consent Execution** | `bdc-workflow.sh` | Debug one consent group; production baseline per consent group |
| **Parallel Multi-Consent Execution** | `bdc-cohort-workflow.sh` | Full cohort run — harmonizes all consent groups in parallel, then runs hv_dataqc source-vs-harmonized comparison |

Both modes use the same Docker image. See
[docs/cohort-workflow.md](docs/cohort-workflow.md) for a complete walkthrough.

---

## Building the Image

```bash
docker build -t dm-bip-env .
```

To enable dev mode (allows `--trans-spec` branch overrides at runtime):

```bash
docker build --build-arg BDC_PULL_LATEST=true -t dm-bip-env-dev .
```

---

## Single Consent Execution Mode

Runs the dm-bip harmonization pipeline for exactly one consent group. This is
the original entry point — unchanged from before `feature/bdc-cohort-workflow`.

```bash
docker run --rm \
  -v /path/to/raw/COPDGene-c1:/data/COPDGene-c1:ro \
  -v /path/to/output:/root \
  dm-bip-env \
  /app/scripts/workflow/bdc-workflow.sh \
    --schema COPDGene \
    --source /data/COPDGene-c1
```

With a specific HV branch (requires `BDC_PULL_LATEST=true` image):

```bash
docker run --rm \
  -e BDC_PULL_LATEST=true \
  -v /path/to/raw/COPDGene-c1:/data/COPDGene-c1:ro \
  -v /path/to/output:/root \
  dm-bip-env-dev \
  /app/scripts/workflow/bdc-workflow.sh \
    --schema COPDGene \
    --source /data/COPDGene-c1 \
    --trans-spec RTIInternational/NHLBI-BDC-DMC-HV@main
```

Output is written to `$HOME/DMC_<consent-group>_<schema>_Processed_<timestamp>/`
(inside the container, i.e. under the `/root` mount above).

---

## Parallel Multi-Consent Execution Mode

Runs all consent groups for one cohort in parallel inside a single container,
then runs hv_dataqc (extract + compare) across all consent groups.

```bash
docker run --rm \
  -v /path/to/raw/COPDGene:/data/COPDGene:ro \
  -v /path/to/dbgap-cache:/dbgap-cache:ro \
  -v /path/to/output:/root \
  dm-bip-env \
  /app/scripts/workflow/bdc-cohort-workflow.sh \
    --schema COPDGene \
    --consent-group /data/COPDGene/COPDGene-c1 \
    --consent-group /data/COPDGene/COPDGene-c2 \
    --dbgap-cache /dbgap-cache
```

Output is written to `$HOME/DMC_COPDGene_<timestamp>/` containing per-consent
subdirectories and an `hv_dataqc/` folder with the comparison report.

See [docs/cohort-workflow.md](docs/cohort-workflow.md) for all options.

---

## Running Other Commands

```bash
docker run --rm -it dm-bip-env make test
docker run --rm -it dm-bip-env make lint
```


