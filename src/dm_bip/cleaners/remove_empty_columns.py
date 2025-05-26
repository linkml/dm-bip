"""A data cleaner that removes empty columns from a TSV file."""

import signal
import sys
from pathlib import Path
from typing import Annotated, Optional, TextIO

import pandas as pd
import typer


def remove_empty_columns(input_stream: TextIO, output_stream: TextIO):
    """Clean a TSV file by dropping columns where all values are NaN (as parsed by Pandas)."""
    df = pd.read_csv(input_stream, sep="\t")  # Read TSV
    df.dropna(axis=1, how="all", inplace=True)  # Drop columns where all values are NaN

    try:
        df.to_csv(output_stream, sep="\t", index=False)  # Save back as TSV
    except BrokenPipeError:
        sys.stderr.close()


def main(
    input_file: Annotated[
        Optional[Path],
        typer.Argument(help="Path to the input TSV file. Uses stdin if absent."),
    ] = None,
    output_file: Annotated[
        Optional[Path],
        typer.Option("-o", "--output", help="Path to the output TSV file. Uses stdout if absent."),
    ] = None,
):
    """Clean a TSV file by dropping columns where all values are NaN (as parsed by Pandas)."""
    input_stream: TextIO = input_file.open("r") if input_file is not None else sys.stdin
    output_stream: TextIO = output_file.open("w") if output_file is not None else sys.stdout
    try:
        remove_empty_columns(input_stream, output_stream)
    finally:
        if input_file is not None:
            input_stream.close()
        if output_file is not None:
            output_stream.close()


if __name__ == "__main__":
    # Handle SIGPIPE to prevent broken pipe errors
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    typer.run(main)
