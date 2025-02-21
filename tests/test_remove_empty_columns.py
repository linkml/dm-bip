"""Test remove_empty_columns script."""

import shutil
import subprocess
import unittest
from pathlib import Path


class TestRemoveEmptyColumnsCLI(unittest.TestCase):
    """Test remove_empty_columns.py script."""

    def run_script(self, script, input_tsv: str) -> str:
        """Run the script with the given input TSV."""
        script_path = Path(script).resolve()  # Ensure absolute path
        python_path = shutil.which("python3")  # Get absolute Python executable path

        if not python_path or not script_path.is_file():
            raise FileNotFoundError(f"Python executable or script not found: {script_path}")

        result = subprocess.run(
            [python_path, str(script_path)],  # Pass script path as a string
            input=input_tsv,
            text=True,
            capture_output=True,
            # check=True,  # Ensures an error is raised on failure
        )
        return result.stdout

    def test_remove_empty_columns(self):
        """Test column removal with remove_empty_columns.py script."""
        input_tsv = "col1\tcol2\tcol3\n1\t\t3\n4\t\t6\n7\t\t9\n"
        expected_output = "col1\tcol3\n1\t3\n4\t6\n7\t9\n"
        script = "simple_clean/remove_empty_columns.py"
        self.assertEqual(self.run_script(script, input_tsv).strip(), expected_output.strip())


if __name__ == "__main__":
    unittest.main()
