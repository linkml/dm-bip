from dataclasses import astuple
from pathlib import Path
from tempfile import NamedTemporaryFile

from simple_clean.replace_values import Replacement, Replacer


def create_replacer(replacements: list[Replacement]):
    file = NamedTemporaryFile("w")
    file.write("filename,column_name,original_value,replacement_value\n")
    for replacement in replacements:
        file.write(",".join(astuple(replacement)) + "\n")
    file.seek(0)
    replacer = Replacer.from_file(Path(file.name))
    return replacer


def test_replacement_lookup():
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
