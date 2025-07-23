"""Test flatten_dict."""

import json
from types import SimpleNamespace
import unittest


from dm_bip.format_converter.updated_flatten_to_tsv import flatten_dict

class TestFlattenDict(unittest.TestCase):
    """Test the flatten_dict function."""

    def test_flatten_nested_dict(self):
        """Test flattening a nested dictionary with default separator."""
        input_data = {
            "a": 1,
            "b": {"c": 2, "d": {"e": 3}},
            "f": [4, 5]
        }

        expected_output = {
            "a": 1,
            "b__c": 2,
            "b__d__e": 3,
            "f": [4, 5]
        }

        result = flatten_dict(input_data)

        self.assertEqual(result, expected_output)


from dm_bip.format_converter.updated_flatten_to_tsv import explode_rows

class TestExplodeRows(unittest.TestCase):
    def test_explode_no_lists(self):
        records = [{"a": 1, "b": 2}]
        result = explode_rows(records, list_keys=["b"])
        self.assertEqual(result, records)

    def test_explode_single_list(self):
        records = [{"a": 1, "b": [2, 3]}]
        expected = [{"a": 1, "b": 2}, {"a": 1, "b": 3}]
        result = explode_rows(records, list_keys=["b"])
        self.assertEqual(result, expected)

    def test_explode_multiple_lists(self):
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
        records = [{"a": 1, "b": [{"x": 10}, {"x": 20}]}]
        expected = [
            {"a": 1, "b": json.dumps({"x": 10}, separators=(",", ":"))},
            {"a": 1, "b": json.dumps({"x": 20}, separators=(",", ":"))},
        ]
        result = explode_rows(records, list_keys=["b"])
        self.assertEqual(result, expected)

    def test_exclude_list_keys_not_in_record(self):
        records = [{"a": 1, "b": 2}]
        result = explode_rows(records, list_keys=["c"])  # 'c' not in record
        self.assertEqual(result, records)



from dm_bip.format_converter.updated_flatten_to_tsv import join_lists, get_slot_order

class TestJoinLists(unittest.TestCase):
    def test_join_lists_no_lists(self):
        records = [{"a": "1", "b": 2}]
        result = join_lists(records, ["a", "b"])
        self.assertEqual(result, records)

    def test_join_lists_simple(self):
        records = [{"a": [1, 2, 3]}]
        expected = [{"a": "1,2,3"}]
        result = join_lists(records, ["a"])
        self.assertEqual(result, expected)

    def test_join_lists_with_dicts(self):
        records = [{"a": [{"x": 1}, {"y": 2}]}]
        expected_jsons = [json.dumps({"x": 1}, separators=(",", ":")),
                          json.dumps({"y": 2}, separators=(",", ":"))]
        expected = [{"a": ",".join(expected_jsons)}]
        result = join_lists(records, ["a"])
        self.assertEqual(result, expected)

    def test_join_lists_mixed_keys(self):
        records = [{"a": [1, 2], "b": [3, 4], "c": "no change"}]
        expected = [{"a": "1,2", "b": "3,4", "c": "no change"}]
        result = join_lists(records, ["a", "b"])
        self.assertEqual(result, expected)

    def test_join_lists_custom_separator(self):
        records = [{"a": [1, 2, 3]}]
        expected = [{"a": "1|2|3"}]
        result = join_lists(records, ["a"], join_str="|")
        self.assertEqual(result, expected)


from types import SimpleNamespace

class DummySlot:
    def __init__(self, name, range_, inlined=False, multivalued=False):
        self.name = name
        self.range = range_
        self.inlined = inlined
        self.multivalued = multivalued

class DummySchemaView:
    def __init__(self):
        # Map class name -> list of slot names
        self.class_slots_map = {
            "TestClass": ["scalar1", "ref1", "inlined_ref", "multivalued_ref", "external_ref"]
        }
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
        return self.class_slots_map.get(class_name, [])

    def get_slot(self, slot_name):
        return self.slots.get(slot_name)

    def all_classes(self):
        return self._all_classes

    def get_class(self, class_name):
        # Return an object with .name attribute for get_slot_order()
        if class_name in self.class_slots_map:
            return SimpleNamespace(name=class_name)
        return None


class TestGetSlotOrder(unittest.TestCase):
    def setUp(self):
        self.sv = DummySchemaView()

    def test_get_slot_order_existing_class(self):
        expected_order = ["scalar1", "ref1", "inlined_ref", "multivalued_ref", "external_ref"]
        order = get_slot_order(self.sv, "TestClass")
        self.assertEqual(order, expected_order)

    def test_get_slot_order_missing_class(self):
        with self.assertRaises(ValueError):
            get_slot_order(self.sv, "NonexistentClass")


if __name__ == "__main__":
    unittest.main()
