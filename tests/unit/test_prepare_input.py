"""Tests for the prepare_input data cleaner."""

from dm_bip.cleaners.prepare_input import clean_dbgap_content, get_required_phts


class TestGetRequiredPhts:
    """Tests for get_required_phts function."""

    def test_extracts_pht_ids_from_yaml_files(self, tmp_path):
        """Extracts pht IDs from YAML files in a directory."""
        yaml1 = tmp_path / "mapping1.yaml"
        yaml1.write_text("source_table: pht001234\nother_key: value\n")

        yaml2 = tmp_path / "mapping2.yaml"
        yaml2.write_text("tables:\n  - pht005678\n  - pht009999\n")

        result = get_required_phts(tmp_path)

        assert result == {"pht001234", "pht005678", "pht009999"}

    def test_returns_empty_set_for_no_pht_ids(self, tmp_path):
        """Returns empty set when YAML files contain no pht IDs."""
        yaml1 = tmp_path / "mapping.yaml"
        yaml1.write_text("key: value\nother: stuff\n")

        result = get_required_phts(tmp_path)

        assert result == set()

    def test_returns_none_for_nonexistent_directory(self):
        """Returns None when mapping directory doesn't exist."""
        result = get_required_phts("/nonexistent/path")

        assert result is None

    def test_returns_none_for_file_instead_of_directory(self, tmp_path):
        """Returns None when path is a file, not a directory."""
        file_path = tmp_path / "file.yaml"
        file_path.write_text("pht001234")

        result = get_required_phts(file_path)

        assert result is None

    def test_ignores_non_yaml_files(self, tmp_path):
        """Only processes .yaml files, ignores others."""
        yaml_file = tmp_path / "mapping.yaml"
        yaml_file.write_text("table: pht001234\n")

        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("pht999999\n")

        result = get_required_phts(tmp_path)

        assert result == {"pht001234"}
        assert "pht999999" not in result

    def test_handles_duplicate_pht_ids(self, tmp_path):
        """Returns unique set when same pht ID appears multiple times."""
        yaml1 = tmp_path / "mapping1.yaml"
        yaml1.write_text("table: pht001234\nbackup: pht001234\n")

        yaml2 = tmp_path / "mapping2.yaml"
        yaml2.write_text("source: pht001234\n")

        result = get_required_phts(tmp_path)

        assert result == {"pht001234"}


class TestCleanDbgapContent:
    """Tests for clean_dbgap_content function."""

    def test_transforms_header_line(self):
        """Converts ## header line to proper TSV header."""
        lines = ["## dbGaP_Subject_ID\tcol1\tcol2\n"]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == ["dbGaP_Subject_ID\tcol1\tcol2\n"]

    def test_cleans_phv_accessions_in_header(self):
        """Strips version info from phv accessions in header."""
        lines = ["## dbGaP_Subject_ID\tphv00123456.v1.p1.c1\tphv00789012.v2\n"]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == ["dbGaP_Subject_ID\tphv00123456\tphv00789012\n"]

    def test_skips_comment_lines(self):
        """Skips lines starting with # (except ## header)."""
        lines = [
            "# This is a comment\n",
            "# Another comment\n",
            "## dbGaP_Subject_ID\tcol1\n",
            "# More comments after header\n",
            "123\tvalue1\n",
        ]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == ["dbGaP_Subject_ID\tcol1\n", "123\tvalue1\n"]

    def test_skips_duplicate_header_line(self):
        """Skips the names line that follows the ## line."""
        lines = [
            "## dbGaP_Subject_ID\tcol1\n",
            "dbGaP_Subject_ID\tcol1\n",  # Duplicate header to skip
            "123\tvalue1\n",
        ]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == ["dbGaP_Subject_ID\tcol1\n", "123\tvalue1\n"]

    def test_skips_intentionally_blank_lines(self):
        """Skips lines containing 'Intentionally Blank'."""
        lines = [
            "## dbGaP_Subject_ID\tcol1\n",
            "123\tvalue1\n",
            "456\tIntentionally Blank\n",
            "789\tvalue3\n",
        ]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == [
            "dbGaP_Subject_ID\tcol1\n",
            "123\tvalue1\n",
            "789\tvalue3\n",
        ]

    def test_skips_empty_lines(self):
        """Skips empty or whitespace-only lines."""
        lines = [
            "## dbGaP_Subject_ID\tcol1\n",
            "123\tvalue1\n",
            "\n",
            "   \n",
            "456\tvalue2\n",
        ]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == [
            "dbGaP_Subject_ID\tcol1\n",
            "123\tvalue1\n",
            "456\tvalue2\n",
        ]

    def test_passes_through_data_rows(self):
        """Data rows are yielded unchanged."""
        lines = [
            "## dbGaP_Subject_ID\tcol1\tcol2\n",
            "123\tfoo\tbar\n",
            "456\tbaz\tqux\n",
        ]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == [
            "dbGaP_Subject_ID\tcol1\tcol2\n",
            "123\tfoo\tbar\n",
            "456\tbaz\tqux\n",
        ]

    def test_handles_file_with_no_header(self):
        """Handles edge case of file with no ## header line."""
        lines = [
            "# comment only\n",
            "123\tvalue\n",
        ]

        result = list(clean_dbgap_content(iter(lines)))

        assert result == ["123\tvalue\n"]
