from __future__ import annotations

import argparse
from unittest.mock import MagicMock

from bids.layout import Query

from skullduggery import bids as bids_module
from skullduggery.bids import _bids_filter, _filter_pybids_any, _load_bidsignore, create_bids_layout


def test_filter_pybids_any():
    """Test conversion of wildcard strings to Query.ANY."""
    input_dict = {"suffix": "T1w", "session": "*", "subject": "01", "run": "*"}

    expected = {
        "suffix": "T1w",
        "session": Query.ANY,
        "subject": "01",
        "run": Query.ANY,
    }

    assert _filter_pybids_any(input_dict) == expected


def test_bids_filter_inline_json():
    """Test parsing inline JSON string with wildcard filtering."""
    json_str = '{"suffix": "T1w", "session": "*"}'

    expected = {"suffix": "T1w", "session": Query.ANY}

    result = _bids_filter(json_str)
    assert result == expected, f"Expected {expected}, got {result}"


def test_bids_filter_from_file(tmp_path):
    """Test parsing BIDS filter from JSON file with wildcard filtering."""
    json_file = tmp_path / "filter.json"
    json_file.write_text('{"suffix": "T2w", "run": "*"}')

    expected = {"suffix": "T2w", "run": Query.ANY}

    result = _bids_filter(str(json_file))
    assert result == expected, f"Expected {expected}, got {result}"


def test_bids_filter_inline_json_converts_wildcards():
    assert _bids_filter('{"suffix": "*", "datatype": "anat"}') == {"suffix": Query.ANY, "datatype": "anat"}


def test_create_bids_layout_uses_absolute_path_and_strictness(mocker, tmp_path):
    layout_cls = mocker.patch.object(bids_module.bids, "BIDSLayout", return_value=MagicMock())
    args = argparse.Namespace(bids_path=str(tmp_path / "ds"), no_strict_bids_validation=True)

    create_bids_layout(args)

    args_, kwargs = layout_cls.call_args
    assert args_ == (str(tmp_path / "ds"),)
    assert kwargs["validate"] is False


def test_create_bids_layout_validates_by_default(mocker, tmp_path):
    layout_cls = mocker.patch.object(bids_module.bids, "BIDSLayout", return_value=MagicMock())
    args = argparse.Namespace(bids_path=str(tmp_path), no_strict_bids_validation=False)

    create_bids_layout(args)

    assert layout_cls.call_args.kwargs["validate"] is True


# ─── _load_bidsignore tests ──────────────────────────────────────────────


class TestLoadBidsIgnore:
    """Tests for .bidsignore loading and pattern compilation."""

    def test_no_bidsignore_returns_empty_tuple(self, tmp_path):
        """When no .bidsignore exists, return an empty tuple."""
        result = _load_bidsignore(tmp_path)
        assert result == ()

    def test_empty_bidsignore_returns_empty_tuple(self, tmp_path):
        """An empty .bidsignore file yields no ignore patterns."""
        (tmp_path / ".bidsignore").write_text("")
        assert _load_bidsignore(tmp_path) == ()

    def test_single_pattern(self, tmp_path):
        """A single glob pattern is compiled to a regex."""
        (tmp_path / ".bidsignore").write_text("**/sub-01/**")
        patterns = _load_bidsignore(tmp_path)

        assert len(patterns) == 1
        import re

        # fnmatch.translate wraps with (?s:...) and adds trailing /
        assert isinstance(patterns[0], type(re.compile("")))

    def test_multiple_patterns(self, tmp_path):
        """Each non-empty, non-comment line becomes one compiled pattern."""
        (tmp_path / ".bidsignore").write_text("**/sub-01/**\n**/sub-02/**\n**/code/**")
        assert len(_load_bidsignore(tmp_path)) == 3

    def test_comments_are_skipped(self, tmp_path):
        """Lines starting with '#' are treated as comments and ignored."""
        (tmp_path / ".bidsignore").write_text("# This is a comment\n**/sub-01/**\n# Another comment")
        patterns = _load_bidsignore(tmp_path)
        assert len(patterns) == 1

    def test_empty_lines_are_skipped(self, tmp_path):
        """Blank lines in .bidsignore are silently skipped."""
        (tmp_path / ".bidsignore").write_text("\n**/sub-01/**\n\n")
        assert len(_load_bidsignore(tmp_path)) == 1

    def test_whitespace_only_lines_are_skipped(self, tmp_path):
        """Lines with only whitespace are skipped."""
        (tmp_path / ".bidsignore").write_text("   \n**/sub-01/**\n  \t  ")
        assert len(_load_bidsignore(tmp_path)) == 1

    def test_mixed_comments_and_blanks(self, tmp_path):
        """A realistic .bidsignore with comments, blanks, and patterns."""
        (tmp_path / ".bidsignore").write_text(
            "# Ignore derivs\n" "**/derivatives/**\n" "\n" "# Ignore intermediate files\n" "**/scratch/**\n"
        )
        assert len(_load_bidsignore(tmp_path)) == 2

    def test_pattern_matches_expected_paths(self, tmp_path):
        """Compiled patterns actually match the intended file paths."""
        (tmp_path / ".bidsignore").write_text("sub-01/**")
        pattern = _load_bidsignore(tmp_path)[0]

        # The fnmatch.translate output is designed to match against full paths
        assert pattern.search("/data/sub-01/anat/file.nii.gz")
        assert not pattern.search("/data/sub-02/anat/file.nii.gz")

    def test_mode_bash_returns_formatted_strings(self, tmp_path):
        """Bash mode returns formatted string patterns instead of compiled regexps."""
        (tmp_path / ".bidsignore").write_text("**/sub-01/**\n**/code/**")
        result = _load_bidsignore(tmp_path, mode="bash")

        assert len(result) == 2
        assert result[0] == "m/**/sub-01/**/"
        assert result[1] == "m/**/code/**/"
        # Not compiled regexps
        import re

        assert not isinstance(result[0], type(re.compile("")))

    def test_mode_bash_skips_comments(self, tmp_path):
        """Bash mode also skips comment and empty lines."""
        (tmp_path / ".bidsignore").write_text("# skip\n**/sub-01/**\n")
        result = _load_bidsignore(tmp_path, mode="bash")
        assert len(result) == 1

    def test_returns_tuple_not_list(self, tmp_path):
        """The function returns a tuple, not a list."""
        (tmp_path / ".bidsignore").write_text("**/sub-01/**")
        result = _load_bidsignore(tmp_path)
        assert isinstance(result, tuple)
