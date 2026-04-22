"""Create synthetic test data files for prepare_metadata tests.

Run once to generate unit_key.xlsx and raw_metadata.xlsx.
"""

from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def create_unit_key():
    unit_key = pd.DataFrame({
        "source_value": ["percent", "lbs", "inches", "mmhg", "mg/dl", "gm/dl"],
        "standard_value": ["%", "[lb_av]", "[in_us]", "mm[Hg]", "mg/dL", "g/dL"],
        "note": [""] * 6,
    })
    conversions = pd.DataFrame({
        "this_unit": ["[in_us]", "[lb_av]", "mmol/L"],
        "that_unit": ["cm", "kg", "mg/dL"],
        "conversion_rule": ["* 2.54", "* 0.453592", "* 38.67"],
        "conversion_formula": ["", "", ""],
        "conversion_condition": ["", "", ""],
    })
    equivalencies = pd.DataFrame({
        "this_unit": ["meq/L"],
        "that_unit": ["mmol/L"],
        "equivalency_always": ["1"],
    })
    ucum = pd.DataFrame({
        "ucum_code": ["cm", "kg", "g/dL", "mg/dL", "mm[Hg]", "%", "kg/m2", "h",
                       "[in_us]", "[lb_av]", "mmol/L", "{#}/wk", "{#}/d", "meq/L"],
    })

    with pd.ExcelWriter(HERE / "unit_key.xlsx") as writer:
        unit_key.to_excel(writer, sheet_name="unit_key", index=False)
        conversions.to_excel(writer, sheet_name="conversions", index=False)
        equivalencies.to_excel(writer, sheet_name="equivalencies", index=False)
        ucum.to_excel(writer, sheet_name="ucum", index=False)


def create_raw_metadata():
    rows = [
        {"cohort": "aric", "bdchm_label": "albumin in blood", "var_id": "phv00202900.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "ALBUMIN", "var_desc": "albumin level in blood", "var_units": "gm/dl",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "bmi", "var_id": "phv00202901.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "BMI", "var_desc": "body mass index kg/m2", "var_units": "",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "body height", "var_id": "phv00202902.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "HEIGHT", "var_desc": "standing height", "var_units": "inches",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "body weight", "var_id": "phv00202903.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "WEIGHT", "var_desc": "body weight", "var_units": "lbs",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "blood pressure", "var_id": "phv00202904.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "SBPA", "var_desc": "systolic blood pressure", "var_units": "mmhg",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "blood pressure", "var_id": "phv00202905.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "DBPA", "var_desc": "diastolic blood pressure", "var_units": "mmhg",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "hdl", "var_id": "phv00202906.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004028.v1",
         "var_name": "HDL", "var_desc": "hdl cholesterol", "var_units": "mmol/L",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "sleep hours", "var_id": "phv00202907.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "SLEEP", "var_desc": "number of hours of sleep", "var_units": "",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "alcohol consumption", "var_id": "phv00202908.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "ALCOHOL", "var_desc": "alcohol per week", "var_units": "",
         "var_type": "integer", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "stroke status", "var_id": "phv00202909.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "STROKE", "var_desc": "stroke event", "var_units": "",
         "var_type": "Uriorcurie", "bdchm_entity": "Condition"},
        {"cohort": "aric", "bdchm_label": "glucose in blood", "var_id": "phv00202910.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht009999.v1",
         "var_name": "GLUCOSE", "var_desc": "fasting glucose", "var_units": "mg/dl",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "aric", "bdchm_label": "medication adherence", "var_id": "phv00202911.v1",
         "study_id": "phs000280.v1", "data_table_id": "pht004027.v1",
         "var_name": "MEDADHERE", "var_desc": "medication adherence score", "var_units": "",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
        {"cohort": "jhs", "bdchm_label": "albumin in blood", "var_id": "phv00100100.v1",
         "study_id": "phs000286.v1", "data_table_id": "pht001200.v1",
         "var_name": "ALB", "var_desc": "serum albumin", "var_units": "g/dL",
         "var_type": "decimal", "bdchm_entity": "MeasurementObservation"},
    ]
    df = pd.DataFrame(rows)
    df.to_excel(HERE / "raw_metadata.xlsx", index=False)


if __name__ == "__main__":
    create_unit_key()
    create_raw_metadata()
    print("Test data created.")
