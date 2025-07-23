"""Test flatten_dict."""

import json
import unittest
from types import SimpleNamespace

from dm_bip.format_converter.updated_flatten_to_tsv import *


class TestFlattenDict(unittest.TestCase):
    """Test the flatten_dict function."""

    def test_flatten_nested_dict(self):
        """Test flattening a nested dictionary with default separator."""
        input_data = {"a": 1, "b": {"c": 2, "d": {"e": 3}}, "f": [4, 5]}

        expected_output = {"a": 1, "b__c": 2, "b__d__e": 3, "f": [4, 5]}

        result = flatten_dict(input_data)

        self.assertEqual(result, expected_output)


class TestExplodeRows(unittest.TestCase):
    """Test the explode_rows function."""

    def test_explode_no_lists(self):
        """Test exploding rows with no lists."""
        records = [{"a": 1, "b": 2}]
        result = explode_rows(records, list_keys=["b"])
        self.assertEqual(result, records)

    def test_explode_single_list(self):
        """Test exploding a single list key."""
        records = [{"a": 1, "b": [2, 3]}]
        expected = [{"a": 1, "b": 2}, {"a": 1, "b": 3}]
        result = explode_rows(records, list_keys=["b"])
        self.assertEqual(result, expected)

    def test_explode_multiple_lists(self):
        """Test exploding multiple list keys."""
        records = [{"a": 1, "b": [2, 3], "c": [4, 5]}]
        expected = [
            {"a": 1, "b": 2, "c": 4},
            {"a": 1, "b": 2, "c": 5},
            {"a": 1, "b": 3, "c": 4},
            {"a": 1, "b": 3, "c": 5},
        ]
        result = explode_rows(records, list_keys=["b", "c"])
        self.assertEqual(result, expected)

    def test_explode_with_dict_in_list(self):
        """Test exploding a list that contains dictionaries."""
        records = [{"a": 1, "b": [{"x": 10}, {"x": 20}]}]
        expected = [
            {"a": 1, "b": json.dumps({"x": 10}, separators=(",", ":"))},
            {"a": 1, "b": json.dumps({"x": 20}, separators=(",", ":"))},
        ]
        result = explode_rows(records, list_keys=["b"])
        self.assertEqual(result, expected)

    def test_exclude_list_keys_not_in_record(self):
        """Test exploding with a list key that is not in the record."""
        records = [{"a": 1, "b": 2}]
        result = explode_rows(records, list_keys=["c"])  # 'c' not in record
        self.assertEqual(result, records)


class TestJoinLists(unittest.TestCase):
    """Test the join_lists function."""

    def test_join_lists_no_lists(self):
        """Test joining lists when no keys are lists."""
        records = [{"a": "1", "b": 2}]
        result = join_lists(records, ["a", "b"])
        self.assertEqual(result, records)

    def test_join_lists_simple(self):
        """Test joining a simple list."""
        records = [{"a": [1, 2, 3]}]
        expected = [{"a": "1,2,3"}]
        result = join_lists(records, ["a"])
        self.assertEqual(result, expected)

    def test_join_lists_with_dicts(self):
        """Test joining lists that contain dictionaries."""
        records = [{"a": [{"x": 1}, {"y": 2}]}]
        expected_jsons = [json.dumps({"x": 1}, separators=(",", ":")), json.dumps({"y": 2}, separators=(",", ":"))]
        expected = [{"a": ",".join(expected_jsons)}]
        result = join_lists(records, ["a"])
        self.assertEqual(result, expected)

    def test_join_lists_mixed_keys(self):
        """Test joining lists with mixed key types."""
        records = [{"a": [1, 2], "b": [3, 4], "c": "no change"}]
        expected = [{"a": "1,2", "b": "3,4", "c": "no change"}]
        result = join_lists(records, ["a", "b"])
        self.assertEqual(result, expected)

    def test_join_lists_custom_separator(self):
        """Test joining lists with a custom separator."""
        records = [{"a": [1, 2, 3]}]
        expected = [{"a": "1|2|3"}]
        result = join_lists(records, ["a"], join_str="|")
        self.assertEqual(result, expected)


class DummySlot:
    """Dummy class to simulate a slot in the schema."""

    def __init__(self, name, range_, inlined=False, multivalued=False):
        self.name = name
        self.range = range_
        self.inlined = inlined
        self.multivalued = multivalued


class DummySchemaView:
    """Dummy schema view for testing."""

    def __init__(self):
        # Map class name -> list of slot names
        self.class_slots_map = {"TestClass": ["scalar1", "ref1", "inlined_ref", "multivalued_ref", "external_ref"]}
        # Map slot name -> DummySlot object
        self.slots = {
            "scalar1": DummySlot("scalar1", "string"),
            "ref1": DummySlot("ref1", "OtherClass", inlined=False, multivalued=False),
            "inlined_ref": DummySlot("inlined_ref", "OtherClass", inlined=True),
            "multivalued_ref": DummySlot("multivalued_ref", "OtherClass", inlined=False, multivalued=True),
            "external_ref": DummySlot("external_ref", "ExternalClass", inlined=False),
        }
        # Set of all classes
        self._all_classes = {"TestClass", "OtherClass", "ExternalClass"}

    def class_slots(self, class_name, attributes=True):
        """Return slots for a given class."""
        return self.class_slots_map.get(class_name, [])

    def get_slot(self, slot_name):
        """Return a slot by name."""
        return self.slots.get(slot_name)

    def all_classes(self):
        """Return all classes in the schema."""
        return self._all_classes

    def get_class(self, class_name):
        """Return a class by name."""
        # Return an object with .name attribute for get_slot_order()
        if class_name in self.class_slots_map:
            return SimpleNamespace(name=class_name)
        return None


class TestGetSlotOrder(unittest.TestCase):
    """Test the get_slot_order function."""

    def setUp(self):
        """Set up a dummy schema view for testing."""
        self.sv = DummySchemaView()

    def test_get_slot_order_existing_class(self):
        """Test getting slot order for an existing class."""
        expected_order = ["scalar1", "ref1", "inlined_ref", "multivalued_ref", "external_ref"]
        order = get_slot_order(self.sv, "TestClass")
        self.assertEqual(order, expected_order)

    def test_get_slot_order_missing_class(self):
        """Test getting slot order for a class that does not exist."""
        with self.assertRaises(ValueError):
            get_slot_order(self.sv, "NonexistentClass")


if __name__ == "__main__":
    unittest.main()
