"""Module to join two dataframes and add a column from one dataframe to the other dataframe."""

from pathlib import Path
from typing import Annotated, Optional

import pandas as pd
import typer


def main(
        left_path: Annotated[
            Path,
            typer.Option(
                "-i", "--left_path", exists=True,
                help="Path to the input TSV file to use as \'left\' dataframe in the merge."),
        ] = ...,
        right_path: Annotated[
            Path,
            typer.Option(
                "-i", "--right_path", exists=True,
                help="Path to the input TSV file to use as \'right\' dataframe in the merge."),
        ] = ...,
        output_file: Optional[str] = typer.Option(None, "--output_file",
                                                  help="Path to save the melted TSV."),
        new_column: str = typer.Option(..., "--new_column",
                                       help="Name of the new column to add to the left file"),
        source_column: str = typer.Option(..., "--source_column",
                                          help="Column in the right file to copy into the new column"),
        left_id: str = typer.Option("id", "--left_id", help="Join key in the left file (default: id)"),
        right_id: str = typer.Option("id", "--right_id", help="Join key in the right file (default: id)"),
        filter_column: str = typer.Option(None, "--filter_column",
                                          help="Keep only rows where filter_column == filter_value (optional)"),
        filter_value: str = typer.Option(None, "--filter_value",
                                         help="Keep only rows where ffilter_column == filter_value (optional)"),
        separator: str = typer.Option("\t", "--separator", help="Field separator (default: tab)")
):
    """Merge a column from one file into another file using a left join."""
    left_df = pd.read_csv(left_path, sep=separator, dtype=str)
    right_df = pd.read_csv(right_path, sep=separator, dtype=str)

    # Optional filter on the right dataframe
    if filter_column and filter_value is not None:
        right_df = right_df[right_df[filter_column] == str(filter_value)]

    # Keep only the join id + source_column, rename to the new column name
    right_min = (
        right_df[[right_id, source_column]]
        .dropna(subset=[source_column])
        .drop_duplicates(subset=[right_id], keep="first")
        .rename(columns={source_column: new_column})
    )

    # Merge dataframes
    merged_df = left_df.merge(
        right_min, how="left", left_on=left_id, right_on=right_id
    )

    # If the id column names differ, drop the extra one
    if left_id != right_id and right_id in merged_df.columns:
        merged_df = merged_df.drop(columns=[right_id])

    if output_file:
          merged_df.to_csv(output_file, sep=separator, index=False)
          typer.echo(f"Saved melted data to: {output_file}")
    else:
        typer.echo(merged_df.to_string(index=False))


if __name__ == "__main__":
    typer.run(main)
