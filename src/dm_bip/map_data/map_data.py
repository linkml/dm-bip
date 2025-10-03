import json
import os
import subprocess
import time
from pathlib import Path
from flatten_dict import flatten
from flatten_dict.reducers import make_reducer
import yaml

from linkml.validator.loaders import TsvLoader
from linkml_map.transformer.object_transformer import ObjectTransformer
from linkml_runtime import SchemaView
from more_itertools import chunked

class DataLoader:
    def __init__(self, base_path):
        self.base_path = base_path

    def __getitem__(self, pht_id):
        file_path = os.path.join(self.base_path, f"{pht_id}.tsv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No TSV file found for {pht_id} at {file_path}")
        return TsvLoader(os.path.join(self.base_path, f"{pht_id}.tsv")).iter_instances()

    def __contains__(self, pht_id):
        return os.path.exists(os.path.join(self.base_path, f"{pht_id}.tsv"))
    
def get_spec_files(directory, search_string):
    """
    Find YAML files in the directory that contain the search_string.
    Returns a sorted list of matching file paths.
    """
    directory = Path(directory)

    result = subprocess.run(
        ["grep", "-rl", search_string, str(directory)], stdout=subprocess.PIPE, text=True, check=False
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    file_paths = [Path(p.strip()) for p in result.stdout.strip().split("\n") if p.strip().endswith((".yaml", ".yml"))]
    return sorted(file_paths, key=lambda p: p.stem)

def multi_spec_transform(data_loader, spec_files, source_schema, target_schema):
    for file in spec_files:
        print(f"{file.stem}", end="", flush=True)
        try:
            with open(file) as f:
                specs = yaml.safe_load(f)
            for block in specs:
                derivation = block["class_derivations"]
                print(".", end="", flush=True)
                for _, class_spec in derivation.items():
                    pht_id = class_spec["populated_from"]
                    rows = data_loader[pht_id]

                    transformer = ObjectTransformer(unrestricted_eval=True)
                    transformer.source_schemaview = SchemaView(source_schema)
                    transformer.target_schemaview = SchemaView(target_schema)
                    transformer.create_transformer_specification(block)

                    for row in rows:
                        mapped = transformer.map_object(row, source_type=pht_id)
                        yield mapped
            print("")
        except Exception as e:
            print(f"\n⚠️  Error processing {file}: {e.__class__.__name__} - {e}")
            print(block)
            import traceback

            traceback.print_exc()
            raise

def json_stream(chunks, key_name):
    for i, chunk in enumerate(chunks):
        js = json.dumps({key_name: chunk}, ensure_ascii=False)
        yield js if i == 0 else ",".join(js.splitlines()[1:-1])

def jsonl_stream(chunks):
    for chunk in chunks:
        yield "".join(json.dumps(obj, ensure_ascii=False) + "\n" for obj in chunk)

def yaml_stream(chunks, key_name):
    for i, chunk in enumerate(chunks):
        yaml_str = yaml.dump({key_name: chunk}, default_flow_style=False)
        yield yaml_str if i == 0 else "\n".join(yaml_str.splitlines()[1:]) + "\n"

def tsv_stream(chunks, key_name=None, sep="\t", reducer_str="__"):
    initial_headers = []
    headers = []

    sep = "\t"
    reducer = make_reducer(reducer_str)
    for chunk in chunks:
        for obj in chunk:
            flat = flatten(obj, reducer=reducer)

            for k in flat.keys():
                if k not in headers:
                    headers.append(k)

            if len(initial_headers) == 0:
                yield sep.join(headers) + "\n"
                initial_headers = headers

            row = sep.join(str(flat.get(h, "")) for h in headers)
            yield row + "\n"

    if headers != initial_headers:
        tsv_stream.headers = headers

def rewrite_header_and_pad(chunks, final_header, sep="\t"):
    header_count = len(final_header)
    header_line = sep.join(final_header) + "\n"

    def pad_lines(chunk):
        out_lines = []
        for line in chunk:
            fields = line.rstrip("\n").split(sep)
            if len(fields) < header_count:
                fields.extend([""] * (header_count - len(fields)))
            out_lines.append(sep.join(fields) + "\n")
        return out_lines

    first_chunk = next(chunks, None)
    yield header_line + "".join(pad_lines(first_chunk[1:]))

    for chunk in chunks:
        yield "".join(pad_lines(chunk))

# source_sv = SchemaView("/sbgenomics/project-files/COPDGene/COPDGene_HMB_Schema.yaml")
# source_sv = SchemaView("/sbgenomics/workspace/output/Schema_FHS_v31_c1/schema-automator-data/Schema_FHS_v31_c1.yaml")
# source_sv = SchemaView("/sbgenomics/workspace/output/CHS/Schema_CHS_v7_c1/Schema_CHS_v7_c1.yaml")
# source_sv = SchemaView("/sbgenomics/workspace/output/HCHS_SOL_cleaned/Schema_HCHS_SOL_v1_c1.yaml")
# source_sv = SchemaView("/sbgenomics/workspace/output/MESA/Schema_MESA_v13_c1/Schema_MESA_v13_c1.yaml")
# source_sv = SchemaView("/sbgenomics/workspace/output/WHI/Schema_WHI_v12_c1/Schema_WHI_v12_c1.yaml")
# source_sv = SchemaView("/sbgenomics/workspace/output/ARIC/Schema_ARIC_v8_c1/Schema_ARIC_v8_c1.yaml")
# source_sv = SchemaView("/sbgenomics/workspace/output/JHS/Schema_JHS_v7_c1/Schema_JHS_v7_c1.yaml")
source_sv = SchemaView("/sbgenomics/workspace/output/CARDIA/Schema_CARDIA_v3_c1/Schema_CARDIA_v3_c1.yaml")
source_schema = source_sv.schema

target_sv = SchemaView("/sbgenomics/workspace/NHLBI-BDC-DMC-HM/src/bdchm/schema/bdchm.yaml")
target_schema = target_sv.schema

# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/COPDGene-ingest/"
# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/FHS-ingest/"
# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/CHS-ingest/"
# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/HCHS-ingest/"
# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/MESA-ingest/"
# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/WHI-ingest/"
# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/ARIC-ingest/"
# var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/JHS-ingest/"
var_dir = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/CARDIA-ingest/"

output_base = "/sbgenomics/output-files/TSV_output"
study_top_dir = "JHS_cleaned"
study_dir = "JHS-v7-c1"
data_version = "JHS-v7-c1"
consent_label = "HMB-IRB-NPU"

os.makedirs(f"{output_base}/{study_dir}/", exist_ok=True)
# output_type = "json"
# output_type = "jsonl"
output_type = "tsv"
# output_type = "yaml"

stream_map = {"json": json_stream, "jsonl": jsonl_stream, "tsv": tsv_stream, "yaml": yaml_stream}
stream_func = stream_map[output_type]

data_loader = DataLoader("/sbgenomics/workspace/output/" + study_top_dir + "/" + data_version + "/")

entities = [
    "Condition",
    "Demography",
    "DrugExposure",
    "MeasurementObservation",
    "Observation",
    "Participant",
    "Person",
    "Procedure",
    "ResearchStudy",
    "SdohObservation",
]

start = time.perf_counter()
for entity in entities:
    spec_files = get_spec_files(var_dir, f"^    {entity}:")
    if spec_files:
        print(f"Starting {entity}")
    else:
        print(f"Skipping {entity} (no spec files)")
        continue

    output_path = f"{output_base}/{study_dir}/{data_version}-{entity}-{consent_label}-data.{output_type}"

    subset = spec_files

    iterable = multi_spec_transform(data_loader, subset, source_schema, target_schema)
    chunk_size = 1000
    chunks = chunked(iterable, chunk_size)

    key_name = entity.lower() + "s"
    with open(output_path, "w") as f:
        for chunk in stream_func(chunks, key_name):
            f.write(chunk)

    if hasattr(stream_func, "headers"):
        print(f"Rewriting {entity} (headers changed)")
        tmp_path = output_path + ".tmp"
        with open(output_path, "r") as src, open(tmp_path, "w") as dst:
            chunks = chunked(src, chunk_size)
            dst.writelines(rewrite_header_and_pad(chunks, stream_func.headers))
        os.replace(tmp_path, output_path)

    print(f"{entity} Complete")

end = time.perf_counter()
print(f"Time: {end - start:.2f} seconds")