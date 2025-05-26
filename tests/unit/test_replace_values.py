"""Tests for the Replacer data cleaner."""

import csv
from dataclasses import astuple
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from dm_bip.cleaners.replace_values import Replacement, Replacer


def create_replacer(replacements: list[Replacement]):
    """Create a replacer class with some replacements without loading a file."""
    file = NamedTemporaryFile("w")
    file.write("filename,column_name,original_value,replacement_value\n")
    for replacement in replacements:
        file.write(",".join(astuple(replacement)) + "\n")
    file.seek(0)
    replacer = Replacer.from_file(Path(file.name))
    return replacer


def test_replacement_lookup():
    """Ensure replacer replaces marked values, and leaves unmarked values alone."""
    replacements: list[Replacement] = [
        Replacement("a.txt", "name", "BADNAME", "goodname"),
        Replacement("a.txt", "name", "BADNAME2", "goodname2"),
        Replacement("b.txt", "label", "BADLABEL", "goodlabel"),
    ]
    replacer = create_replacer(replacements)

    assert replacer.table == {
        "a.txt": {"name": {"BADNAME": "goodname", "BADNAME2": "goodname2"}},
        "b.txt": {"label": {"BADLABEL": "goodlabel"}},
    }

    assert replacer.lookup("a.txt", "name", "BADNAME") == "goodname"
    assert replacer.lookup("a.txt", "name", "BADNAME2") == "goodname2"
    assert replacer.lookup("a.txt", "a", "b") == "b"
    assert replacer.lookup("b.txt", "label", "BADLABEL") == "goodlabel"
    assert replacer.lookup("c.txt", "a", "b") == "b"


def test_replace_csv():
    """Ensure replacing data in a file works."""
    csv_file = NamedTemporaryFile("wt", newline="")
    writer = csv.DictWriter(csv_file, ["id", "name", "label"], delimiter="\t")

    writer.writeheader()
    writer.writerow({"id": "1", "name": "BADNAME", "label": "BADLABEL"})

    csv_file.seek(0)
    csv_path = Path(csv_file.name)

    replacer = create_replacer(
        [
            Replacement(csv_path.name, "name", "BADNAME", "goodname"),
            Replacement(csv_path.name, "label", "BADLABEL", "goodlabel"),
        ]
    )

    output = StringIO()

    replacer.process_csv(csv_path, output)

    expected = """id\tname\tlabel
1\tgoodname\tgoodlabel
"""

    assert output.getvalue() == expected
