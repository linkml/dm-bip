import csv
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

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


class Replacer:
    """
    A class that replace values from a lookup table.

    :param table: The lookup table where replacement values will be found.
    """

    def __init__(self, table: LookupTable):
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
            reader = csv.DictReader(fp)
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

    def iter_dictreader(self, filename: str, reader: csv.DictReader[str]):
        """Wrap a csv.DictReader to replace values as it reads."""
        for row in reader:
            for k, v in row.items():
                row[k] = self.lookup(filename, k, v)
            yield row
