`conditions_long_annotated.tsv`
This file is your final, fully “melted” and annotated table—the output of your preprocessing pipeline, ready for use in LinkML mapping or further data analysis.

It represents one row per participant per condition present, with all HPO labels and codes attached via your lookup table.


`condition_lookup_to_fill.tsv`
Purpose:
This file is a temporary “working” lookup file created by your melt/annotation script whenever it finds new, previously unseen condition names in your participant data.

What’s inside:
All unique condition names, including any new ones that lack HPO label/code.
For newly detected conditions, the hpo_label and hpo_code columns are blank (ready for you or a curator/tool to fill in).

What you do:
Fill in the missing hpo_label and hpo_code (either manually or with an ontology search tool).
After updating, you can use this as your new master lookup file for future runs.


`condition_lookup.tsv`
Purpose:
This is your “master” lookup table used by your pipeline/script.

What’s inside:
All previously curated conditions and their HPO labels/codes.
This file should always be complete (no blanks for curated conditions).

How it’s used:
The script merges the long-format data with this file to annotate every present condition with its label/code.
When new conditions are detected (not found in this file), they are added (with blanks) to the next condition_lookup_to_fill.tsv.


### Workflow
- Run melt_and_annotate_conditions.py over raw Conditions file. 
Transform wide to long format with one row per participant per condition.

- Run your annotation tool over condition_lookup_to_fill.tsv
This tool fills in (or updates) the hpo_label and hpo_code for any blank/missing rows.

- Save the filled/curated file as condition_lookup.tsv
This is now your master, up-to-date lookup table.

- Rerun your melt_and_annotate_conditions.py script
The script reads both:
The original condition data (conditions.tsv)
The now-complete condition_lookup.tsv
The script merges these, annotating every row in the melted long-format table with the latest hpo_label and hpo_code.

Result:
The new conditions_long_annotated.tsv now contains all participant-condition pairs, each with up-to-date HPO info.