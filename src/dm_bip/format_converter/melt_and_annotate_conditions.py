import pandas as pd

# --- Read data and lookup ---
df = pd.read_csv("../../data/BrainPower-STUDY/raw_data/TSV/HealthConditions.tsv", sep='\t')
try:
    lookup = pd.read_csv("condition_lookup.tsv", sep='\t')
except FileNotFoundError:
    lookup = pd.DataFrame(columns=["condition_name", "hpo_label", "hpo_code"])

# --- Melt data to long format ---
id_vars = ['id', 'timepoint']
value_vars = [c for c in df.columns if c not in id_vars]
df_long = df.melt(id_vars=id_vars, value_vars=value_vars,
                  var_name='condition_name', value_name='has_condition')
df_long = df_long[df_long['has_condition'] == 1]

# --- Normalize condition names for comparison ---
lookup['condition_name'] = lookup['condition_name'].astype(str).str.strip().str.lower()
df_long['condition_name'] = df_long['condition_name'].astype(str).str.strip().str.lower()

# --- Find new (unmapped) condition names ---
known_conditions = set(lookup['condition_name'])
all_conditions = set(df_long['condition_name'])
new_conditions = all_conditions - known_conditions

# --- Add new ones with blanks for future curation ---
if new_conditions:
    new_rows = pd.DataFrame({'condition_name': list(new_conditions),
                             'hpo_label': ['']*len(new_conditions),
                             'hpo_code': ['']*len(new_conditions)})
    lookup = pd.concat([lookup, new_rows], ignore_index=True)
    lookup = lookup.sort_values('condition_name')
    lookup.to_csv("condition_lookup_to_fill.tsv", sep='\t', index=False)
    print(f"Found {len(new_conditions)} new conditions. Please fill in 'condition_lookup_to_fill.tsv'.")

# --- Merge as usual, using current mapping ---
df_annot = df_long.merge(lookup, on='condition_name', how='left')

df_annot.to_csv("conditions_long_annotated.tsv", sep='\t', index=False)
