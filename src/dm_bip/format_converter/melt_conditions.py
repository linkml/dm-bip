"""Module for melting condition data from wide format to long format."""

from pathlib import Path
from typing import Annotated, Optional, List

import pandas as pd
import typer


def melt_data(df: pd.DataFrame, id_vars: List[str], var_name: str, value_name: str):
    """
    Convert data from wide format to long format.

    Args:
        df (pd.DataFrame): The input DataFrame in wide format.
        id_vars (List[str]): Column(s) to keep fixed (identifier variables).
        var_name (str): Name to use for the 'variable' column.
        value_name (str): Name to use for the 'value' column.

    Returns:
        pd.DataFrame: A new DataFrame in long format.

    """
    value_vars = [c for c in df.columns if c not in id_vars]

    df_long = df.melt(id_vars=id_vars, value_vars=value_vars,
                    var_name=var_name, value_name=value_name)
    df_long = df_long[df_long[value_name] == 1]

    return df_long


def main(
        input_file: Annotated[
            Path,
            typer.Option(
                "-i", "--input_file", exists=True, help="Path to the input TSV file"),
        ] = ...,
        output_file: Optional[str] = typer.Option(None, "--output_file", help="Path to save the melted TSV."),
        id_vars: str = typer.Option(..., "--id_vars", help="Comma-separated list of ID variables."),
        var_name: str = typer.Option(..., "--var_name", help="Name of the new column header for the conditions."),
        #value_name: str = typer.Option(..., "value", help="Name of the value column.")
):
    """Melt long format file to long format."""
    df = pd.read_csv(input_file, sep='\t')

    id_vars = [x.strip() for x in id_vars.split(",")]

    value_name = 'has_condition' # pass on cli if script will be generalized

    melted_df = melt_data(df, id_vars, var_name, value_name)

    if output_file:
        melted_df.to_csv(output_file, sep="\t", index=False)
        typer.echo(f"Saved melted data to: {output_file}")
    else:
        typer.echo(melted_df.to_string(index=False))


if __name__ == "__main__":
    typer.run(main)
