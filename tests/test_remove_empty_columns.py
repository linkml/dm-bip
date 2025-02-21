"""Test remove_empty_columns."""

import io
import unittest

from simple_clean.remove_empty_columns import remove_empty_columns


class TestRemoveEmptyColumns(unittest.TestCase):
    """Test removing empty columns from a TSV file."""

    def setUp(self):
        """Set up sample input data."""
        self.input_data = "col1\tcol2\tcol3\n" "1\t\t3\n" "2\t\t4\n"  # col2 is empty and should be removed

        self.expected_output = "col1\tcol3\n" "1\t3\n" "2\t4\n"

        self.input_file = io.StringIO(self.input_data)
        self.output_file = io.StringIO()

    def test_remove_empty_columns(self):
        """Test that columns with all NaN values are removed."""
        remove_empty_columns(self.input_file, self.output_file)

        # Reset buffer position for reading
        self.output_file.seek(0)
        output_data = self.output_file.read()

        self.assertEqual(output_data.strip(), self.expected_output.strip())


if __name__ == "__main__":
    unittest.main()
