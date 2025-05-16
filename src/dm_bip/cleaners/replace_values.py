"""A data cleaner to replace specific instances of values in a CSV file."""

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional, TextIO, TypeVar, cast

import typer

T = TypeVar("T", bound=dict)
LookupTable = dict[str, dict[str, dict[str, str]]]


@dataclass
class Replacement:
    """A value that should be replaced for a value in a column."""

    filename: str
    column_name: str
    original_value: str
    replacement_value: str


def get_or_create_dict(key: str, obj: dict[str, T]) -> T:
    """Retrieve a dict from a dict at a string, or to create it if it does not exist."""
    if key in obj:
        return obj[key]
    val: T = cast(T, {})
    obj[key] = val
    return val


def detect_dialect(csv_fp: TextIO):
    """Detect the dialect of a CSV stream, accepting comma or tab delimeters."""
    dialect = csv.Sniffer().sniff(csv_fp.read(1024), delimiters=",\t")
    csv_fp.seek(0)
    return dialect


class Replacer:
    """
    A class that replace values from a lookup table.

    :param table: The lookup table where replacement values will be found.
    """

    def __init__(self, table: LookupTable):
        """Create a Replacer class."""
        self.table = table

    @classmethod
    def from_file(cls, replacements_file: Path):
        """
        Create a replacer from a CSV table.

        :param replacements_file: A path to a CSV file with the following columns:
            * filename
            * column_name
            * original_value
            * replacement_value
        """
        lookup_table: LookupTable = {}

        with open(replacements_file, "r") as fp:
            dialect = detect_dialect(fp)
            reader = csv.DictReader(fp, dialect=dialect)
            replacements = [Replacement(**row) for row in reader]

        for replacement in replacements:
            column_lookup = get_or_create_dict(replacement.filename, lookup_table)
            value_lookup = get_or_create_dict(replacement.column_name, column_lookup)
            value_lookup[replacement.original_value] = replacement.replacement_value

        return cls(lookup_table)

    def lookup(self, filename: str, column_name: str, value: str):
        """Look up a value in a replacement table."""
        column_lookup = self.table.get(filename, None)
        if column_lookup is None:
            return value

        value_lookup = column_lookup.get(column_name, None)
        if value_lookup is None:
            return value

        return value_lookup.get(value, value)

    def process_csv(self, csv_file: Path, output_fp: TextIO):
        """
        Open a CSV, replace all replaceable values, and write the resulting CSV to a text stream.

        :param csv_file: A path to a CSV file to open.
        :param output_fp: A text stream to which to write the resulting CSV.
        """
        with csv_file.open("r") as in_fp:
            dialect = detect_dialect(in_fp)
            in_fp.seek(0)
            reader = csv.DictReader(in_fp, dialect=dialect)

            field_names = reader.fieldnames

            if field_names is None:
                raise ValueError("Could not detect field names from CSV file.")

            writer = csv.DictWriter(output_fp, field_names, dialect=dialect, lineterminator="\n")
            writer.writeheader()

            for row in reader:
                for k, v in row.items():
                    row[k] = self.lookup(csv_file.name, k, v)
                writer.writerow(row)


def replace_csv_values(
    replacements: Annotated[
        Path,
        typer.Argument(help="Path to the replacement file."),
    ],
    csv_input: Annotated[
        Path,
        typer.Argument(help="Path to the CSV file to perform replacements on."),
    ],
    csv_output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Path to write output"),
    ] = None,
):
    """
    Replace a series of values in a CSV file as defined in a spreadsheet.

    The replacement file must be a CSV and TSV with the following columns, in
    this order:

    -----------------

    \b
    filename            The file which should be targeted for replacement. This must only
                        be the the name of the file, without any leading paths.

    \b
    column_name         The name of the column to target.

    \b
    original_value      The value targeted for replacement.

    \b
    replacement_value   The value with which `original_value` will be replaced.
    """  # noqa: D301
    replacer = Replacer.from_file(replacements)

    if csv_output:
        with csv_output.open("w") as fp:
            replacer.process_csv(csv_input, fp)
    else:
        replacer.process_csv(csv_input, sys.stdout)


if __name__ == "__main__":
    typer.run(replace_csv_values)
