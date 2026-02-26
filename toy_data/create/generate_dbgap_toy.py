# ruff: noqa: S311

"""
Generate synthetic dbGaP-style .txt.gz files for pipeline testing.

Creates 4 tables under toy_data/dbgap/raw/ with realistic dbGaP formatting:
  - pht000001: Demographics (sex, race, ethnicity, age)
  - pht000002: Clinical Measurements (height, weight, systolic/diastolic BP, smoking)
  - pht000003: Lab Results (HDL, LDL, total cholesterol)
  - pht000099: Unused table (should be filtered out by get_required_phts)

Each file includes:
  - # comment metadata lines
  - ## header with phv.version column names
  - Duplicate dbGaP_Subject_ID human-readable header line
  - Data rows with realistic values
  - Empty lines and "Intentionally Blank" rows
"""

import gzip
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "dbgap" / "raw"
NUM_ROWS = 25
SEED = 42


def _write_table(filename, header_cols, human_cols, generate_row, *, extra_junk=True):
    """Write a single dbGaP-formatted .txt.gz file."""
    output_path = OUTPUT_DIR / filename
    lines = []

    lines.append("# Study accance: phs000000.v1.p1\n")
    lines.append("# Table accession: {}\n".format(filename.split(".")[2]))
    lines.append("# Consent group: All subjects\n")
    lines.append("# Citation: Synthetic TOY data for pipeline testing\n")
    lines.append("#\n")

    lines.append("##\t" + "\t".join(header_cols) + "\n")
    lines.append("dbGaP_Subject_ID\t" + "\t".join(human_cols) + "\n")

    if extra_junk:
        lines.append("\n")

    for i in range(1, NUM_ROWS + 1):
        subject_id = str(1000 + i)
        row_vals = generate_row(i, subject_id)
        lines.append(subject_id + "\t" + "\t".join(str(v) for v in row_vals) + "\n")

        if extra_junk and i == 10:
            lines.append("\n")
        if extra_junk and i == 20:
            lines.append("Intentionally Blank\t" + "\t".join([""] * len(header_cols)) + "\n")

    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  Wrote {output_path.name} ({NUM_ROWS} data rows)")


def _generate_demographics(_i, _subject_id):
    sex = random.choice([1, 2])
    race = random.choice([1, 2, 3, 4, 5])
    ethnicity = random.choice([1, 0])
    age = random.randint(25, 80)
    return [sex, race, ethnicity, age]


def _generate_clinical(_i, _subject_id):
    height_in = round(random.uniform(58, 76), 1)
    weight_lb = round(random.uniform(110, 280), 1)
    systolic = random.randint(100, 180)
    diastolic = random.randint(60, 110)
    smoking = random.choice([1, 2, 3])
    return [height_in, weight_lb, systolic, diastolic, smoking]


def _generate_lab(_i, _subject_id):
    hdl = random.randint(30, 90)
    ldl = random.randint(70, 190)
    total_chol = hdl + ldl + random.randint(20, 60)
    return [hdl, ldl, total_chol]


def _generate_unused(_i, _subject_id):
    return [random.choice(["A", "B", "C"]), random.randint(1, 100)]


def main():
    """Generate all toy dbGaP .txt.gz files."""
    random.seed(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating dbGaP toy data in {OUTPUT_DIR}/")

    _write_table(
        "phs000000.v1.pht000001.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=["phv00000001.v1.p1", "phv00000002.v1", "phv00000003.v1", "phv00000004.v1", "phv00000005.v1"],
        human_cols=["SUBJECT_ID", "SEX", "RACE", "ETHNICITY", "AGE_YEARS"],
        generate_row=_generate_demographics,
    )

    _write_table(
        "phs000000.v1.pht000002.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=[
            "phv00000011.v1.p1",
            "phv00000012.v1",
            "phv00000013.v1",
            "phv00000014.v1",
            "phv00000015.v1",
            "phv00000016.v1",
        ],
        human_cols=["SUBJECT_ID", "HEIGHT_IN", "WEIGHT_LB", "SYSTOLIC_BP", "DIASTOLIC_BP", "SMOKING"],
        generate_row=_generate_clinical,
    )

    _write_table(
        "phs000000.v1.pht000003.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=["phv00000021.v1.p1", "phv00000022.v1", "phv00000023.v1", "phv00000024.v1"],
        human_cols=["SUBJECT_ID", "HDL", "LDL", "TOTAL_CHOL"],
        generate_row=_generate_lab,
    )

    _write_table(
        "phs000000.v1.pht000099.v1.p1.c1.ex0_1s.HMB.txt.gz",
        header_cols=["phv00000091.v1", "phv00000092.v1"],
        human_cols=["CATEGORY", "SCORE"],
        generate_row=_generate_unused,
        extra_junk=False,
    )

    print("\nDone! Generated 4 .txt.gz files.")


if __name__ == "__main__":
    main()
