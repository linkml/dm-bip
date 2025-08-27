## Workflow
- Run `melt_conditions.py` over raw Conditions file to convert from a wide to long format with one row per participant per condition.
- Run your annotation tool, e.g. Harmonica, over the pivoted conditions file.

Result:
The new `conditions_long_annotated.tsv` now contains all participant-condition pairs, each with up-to-date ontology info.


## Files
`conditions_long_annotated.tsv`
This file is your final, fully “melted” and annotated table—the output of your preprocessing pipeline, ready for use in LinkML mapping or further data analysis.
It represents one row per participant per condition present, with all ontology labels and codes.
