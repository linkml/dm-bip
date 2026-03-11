# ruff: noqa: S311

"""
Generate synthetic toy data for pipeline testing in two presentations.

Outputs:
  data/raw/       - 5 dbGaP-style .txt.gz files (phv headers, coded values)
  data/pre_cleaned/ - 3 human-readable TSVs (decoded values, plain column names)

Raw tables (dbGaP format):
  - pht000001: Demographics (sex, race, ethnicity, age, smoking status)
  - pht000002: Clinical Measurements (height, weight, systolic/diastolic BP, pain severity)
  - pht000003: Lab Results (HDL, LDL, total cholesterol, urine albumin dipstick)
  - pht000005: Longitudinal data (height/age/smoking across 3 visits, cohort, condition)
  - pht000099: Unused table (should be filtered out by get_required_phts)

Pre-cleaned tables (human-readable):
  - demographics.tsv: decoded sex/race/ethnicity, age, smoking_status
  - clinical.tsv: height_in, weight_lb, systolic/diastolic BP, pain_severity
  - longitudinal.tsv: multi-visit data with readable column names

Hand-maintained files (not generated here):
  - data/pre_cleaned/subject.tsv
  - data/pre_cleaned/study.tsv

Column types exercised:
  - Pure numeric (most fields)
  - Pure text categorical (PAIN_SEVERITY: None/Mild/Moderate/Severe)
  - Pure text categorical (SMOKING: Current/Former/Never/Unknown)
  - Dipstick-style mixed (URINE_ALBUMIN: NEGATIVE/TRACE/10/30/100/300)
  - Longitudinal multi-visit (same measurement across visits)
  - Cohort indicator for case() routing
  - Binary categorical (CONDITION_STATUS: 0/1)
"""

import csv
import gzip
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_RAW = SCRIPT_DIR.parent / "data" / "raw"
OUTPUT_CLEAN = SCRIPT_DIR.parent / "data" / "pre_cleaned"
NUM_ROWS = 110
SEED = 42

SEX_DECODE = {1: "Male", 2: "Female"}
RACE_DECODE = {
    1: "White",
    2: "Black or African American",
    3: "Asian",
    4: "Native Hawaiian or Other Pacific Islander",
    5: "American Indian or Alaska Native",
}
ETHNICITY_DECODE = {1: "Hispanic or Latino", 0: "Not Hispanic or Latino"}


def _write_raw_table(filename, header_cols, human_cols, rows, *, extra_junk=True):
    """Write a single dbGaP-formatted .txt.gz file."""
    output_path = OUTPUT_RAW / filename
    lines = []

    lines.append("# Study accession: phs000000.v1.p1\n")
    lines.append("# Table accession: {}\n".format(filename.split(".")[2]))
    lines.append("# Consent group: All subjects\n")
    lines.append("# Citation: Synthetic TOY data for pipeline testing\n")
    lines.append("#\n")

    lines.append("##\t" + "\t".join(header_cols) + "\n")
    lines.append("dbGaP_Subject_ID\t" + "\t".join(human_cols) + "\n")

    if extra_junk:
        lines.append("\n")

    for i, (subject_id, row_vals) in enumerate(rows, 1):
        lines.append(subject_id + "\t" + "\t".join(str(v) for v in row_vals) + "\n")

        if extra_junk and i == 10:
            lines.append("\n")
        if extra_junk and i == 20:
            lines.append("Intentionally Blank\t" + "\t".join([""] * len(header_cols)) + "\n")

    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  Wrote {output_path.name} ({len(rows)} data rows)")


def _write_clean_tsv(filename, columns, rows):
    """Write a clean TSV file with human-readable headers and values."""
    output_path = OUTPUT_CLEAN / filename
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"  Wrote {output_path.name} ({len(rows)} data rows)")


def _generate_demographics():
    """Generate demographics data, returning (raw_rows, clean_rows)."""
    raw_rows = []
    clean_rows = []
    for i in range(1, NUM_ROWS + 1):
        subject_id = str(1000 + i)
        sex = random.choice([1, 2])
        race = random.choice([1, 2, 3, 4, 5])
        ethnicity = random.choice([1, 0])
        age = random.randint(25, 80)
        smoking = random.choice(["Current", "Former", "Never", "Unknown"])

        raw_rows.append((subject_id, [subject_id, sex, race, ethnicity, age, smoking]))
        clean_rows.append([
            subject_id,
            SEX_DECODE[sex],
            RACE_DECODE[race],
            ETHNICITY_DECODE[ethnicity],
            age,
            smoking,
        ])
    return raw_rows, clean_rows


def _generate_clinical():
    """Generate clinical measurements data, returning (raw_rows, clean_rows)."""
    raw_rows = []
    clean_rows = []
    for i in range(1, NUM_ROWS + 1):
        subject_id = str(1000 + i)
        height_in = round(random.uniform(58, 76), 1)
        weight_lb = round(random.uniform(110, 280), 1)
        systolic = random.randint(100, 180)
        diastolic = random.randint(60, 110)
        pain_severity = random.choice(["None", "Mild", "Moderate", "Severe"])

        raw_rows.append((subject_id, [subject_id, height_in, weight_lb, systolic, diastolic, pain_severity]))
        clean_rows.append([subject_id, height_in, weight_lb, systolic, diastolic, pain_severity])
    return raw_rows, clean_rows


def _generate_lab():
    """Generate lab results data, returning raw_rows only (no pre_cleaned equivalent)."""
    raw_rows = []
    for i in range(1, NUM_ROWS + 1):
        subject_id = str(1000 + i)
        hdl = random.randint(30, 90)
        ldl = random.randint(70, 190)
        total_chol = hdl + ldl + random.randint(20, 60)
        urine_albumin = random.choice(["NEGATIVE", "TRACE", "10", "30", "100", "300"])
        raw_rows.append((subject_id, [subject_id, hdl, ldl, total_chol, urine_albumin]))
    return raw_rows


def _generate_longitudinal():
    """Generate longitudinal data, returning (raw_rows, clean_rows)."""
    raw_rows = []
    clean_rows = []
    for i in range(1, NUM_ROWS + 1):
        subject_id = str(1000 + i)
        cohort = random.choice([1, 2])
        height_v1 = round(random.uniform(58, 76), 1)
        height_v2 = round(height_v1 + random.uniform(-0.5, 0.5), 1)
        height_v3 = round(height_v1 + random.uniform(-1.0, 0.3), 1)
        age_v1 = random.randint(25, 70)
        age_v2 = age_v1 + 2
        age_v3 = age_v1 + 5
        smoking_v1 = random.choice([0, 1])
        smoking_v2 = random.choice([0, 1])
        condition_status = random.choice([0, 1])

        raw_rows.append((
            subject_id,
            [subject_id, cohort, height_v1, height_v2, height_v3, age_v1, age_v2, age_v3, smoking_v1, smoking_v2, condition_status],
        ))
        clean_rows.append([
            subject_id, cohort, height_v1, height_v2, height_v3,
            age_v1, age_v2, age_v3, smoking_v1, smoking_v2, condition_status,
        ])
    return raw_rows, clean_rows


def _generate_unused():
    """Generate unused table data (raw only, tests from_raw filtering)."""
    raw_rows = []
    for _i in range(1, NUM_ROWS + 1):
        subject_id = str(1000 + _i)
        raw_rows.append((subject_id, [random.choice(["A", "B", "C"]), random.randint(1, 100)]))
    return raw_rows


def main():
    """Generate all toy data files in both raw and pre_cleaned formats."""
    random.seed(SEED)
    OUTPUT_RAW.mkdir(parents=True, exist_ok=True)
    OUTPUT_CLEAN.mkdir(parents=True, exist_ok=True)

    print(f"Generating toy data ({NUM_ROWS} rows)...")
    print(f"  Raw output:   {OUTPUT_RAW}/")
    print(f"  Clean output: {OUTPUT_CLEAN}/")
    print()

    # --- Demographics ---
    demo_raw, demo_clean = _generate_demographics()

    _write_raw_table(
        "phs000000.v1.pht000001.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=["phv00000001.v1.p1", "phv00000002.v1", "phv00000003.v1", "phv00000004.v1", "phv00000005.v1", "phv00000016.v1"],
        human_cols=["SUBJECT_ID", "SEX", "RACE", "ETHNICITY", "AGE_YEARS", "SMOKING"],
        rows=demo_raw,
    )
    _write_clean_tsv(
        "demographics.tsv",
        columns=["subject_id", "sex", "race", "ethnicity", "age", "smoking_status"],
        rows=demo_clean,
    )

    # --- Clinical Measurements ---
    clin_raw, clin_clean = _generate_clinical()

    _write_raw_table(
        "phs000000.v1.pht000002.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=["phv00000011.v1.p1", "phv00000012.v1", "phv00000013.v1", "phv00000014.v1", "phv00000015.v1", "phv00000017.v1"],
        human_cols=["SUBJECT_ID", "HEIGHT_IN", "WEIGHT_LB", "SYSTOLIC_BP", "DIASTOLIC_BP", "PAIN_SEVERITY"],
        rows=clin_raw,
    )
    _write_clean_tsv(
        "clinical.tsv",
        columns=["subject_id", "height_in", "weight_lb", "systolic_bp", "diastolic_bp", "pain_severity"],
        rows=clin_clean,
    )

    # --- Lab Results (raw only) ---
    lab_raw = _generate_lab()

    _write_raw_table(
        "phs000000.v1.pht000003.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=["phv00000021.v1.p1", "phv00000022.v1", "phv00000023.v1", "phv00000024.v1", "phv00000025.v1"],
        human_cols=["SUBJECT_ID", "HDL", "LDL", "TOTAL_CHOL", "URINE_ALBUMIN"],
        rows=lab_raw,
    )

    # --- Longitudinal ---
    long_raw, long_clean = _generate_longitudinal()

    _write_raw_table(
        "phs000000.v1.pht000005.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=[
            "phv00000041.v1.p1", "phv00000042.v1", "phv00000043.v1", "phv00000044.v1", "phv00000045.v1",
            "phv00000046.v1", "phv00000047.v1", "phv00000048.v1", "phv00000049.v1", "phv00000050.v1", "phv00000051.v1",
        ],
        human_cols=[
            "SUBJECT_ID", "COHORT", "HEIGHT_V1", "HEIGHT_V2", "HEIGHT_V3",
            "AGE_V1", "AGE_V2", "AGE_V3", "SMOKING_V1", "SMOKING_V2", "CONDITION_STATUS",
        ],
        rows=long_raw,
    )
    _write_clean_tsv(
        "longitudinal.tsv",
        columns=[
            "subject_id", "cohort", "height_v1", "height_v2", "height_v3",
            "age_v1", "age_v2", "age_v3", "smoking_v1", "smoking_v2", "condition_status",
        ],
        rows=long_clean,
    )

    # --- Unused table (raw only, tests from_raw filtering) ---
    unused_raw = _generate_unused()

    _write_raw_table(
        "phs000000.v1.pht000099.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=["phv00000091.v1", "phv00000092.v1"],
        human_cols=["CATEGORY", "SCORE"],
        rows=unused_raw,
        extra_junk=False,
    )

    print(f"\nDone! Generated 5 .txt.gz files + 3 .tsv files ({NUM_ROWS} rows each).")


if __name__ == "__main__":
    main()
