from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from bids.layout import Query

from skullduggery.bids import _bids_filter, _bidsignore_patterns, _filter_pybids_any, create_bids_layout


def test_filter_pybids_any():
    """Test conversion of wildcard strings to Query.ANY."""
    input_dict = {"suffix": "T1w", "session": "*", "subject": "01", "run": "*"}

    expected = {"suffix": "T1w", "session": Query.ANY, "subject": "01", "run": Query.ANY}

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


def test_bidsignore_patterns_inline_json():
    """Test parsing inline JSON bidsignore patterns."""
    result = _bidsignore_patterns('["sourcedata/**", " ", "derivatives/**"]')

    assert len(result) == 2
    assert result[0].match("sourcedata/sub-01/anat/file.nii.gz")
    assert result[1].match("derivatives/report.html")


def test_bidsignore_patterns_from_file(tmp_path):
    """Test parsing bidsignore patterns from a JSON file."""
    json_file = tmp_path / "bidsignore.json"
    json_file.write_text('["sub-*/ses-*/tmp/**"]')

    result = _bidsignore_patterns(str(json_file))

    assert len(result) == 1
    assert result[0].match("sub-01/ses-02/tmp/image.nii.gz")


def test_bidsignore_patterns_rejects_non_array_json():
    """Test bidsignore patterns must be provided as a JSON array."""
    with pytest.raises(argparse.ArgumentTypeError, match="JSON array of strings"):
        _bidsignore_patterns('{"ignore": ["sourcedata/**"]}')


def test_bidsignore_patterns_rejects_non_string_items():
    """Test bidsignore patterns must only contain strings."""
    with pytest.raises(argparse.ArgumentTypeError, match="JSON array of strings"):
        _bidsignore_patterns('["sourcedata/**", 1]')


def test_create_bids_layout_uses_empty_ignore_by_default(monkeypatch, tmp_path):
    """Test layout creation does not implicitly read .bidsignore."""
    captured = {}

    def fake_indexer(*, ignore):
        captured["ignore"] = ignore
        return "indexer"

    def fake_layout(root, validate, indexer):
        captured["root"] = root
        captured["validate"] = validate
        captured["indexer"] = indexer
        return "layout"

    def fail_read_text(self):
        raise AssertionError(f"unexpected file read: {self}")

    monkeypatch.setattr("skullduggery.bids.bids.BIDSLayoutIndexer", fake_indexer)
    monkeypatch.setattr("skullduggery.bids.bids.BIDSLayout", fake_layout)
    monkeypatch.setattr(Path, "read_text", fail_read_text)

    args = argparse.Namespace(
        bids_path=str(tmp_path),
        bidsignore_patterns=tuple(),
        no_strict_bids_validation=False,
    )

    result = create_bids_layout(args)

    assert result == "layout"
    assert captured["ignore"] == tuple()
    assert captured["root"] == str(tmp_path.resolve())
    assert captured["validate"] is True
    assert captured["indexer"] == "indexer"


def test_create_bids_layout_passes_bidsignore_patterns(monkeypatch, tmp_path):
    """Test layout creation forwards parsed bidsignore patterns to pyBIDS."""
    captured = {}

    def fake_indexer(*, ignore):
        captured["ignore"] = ignore
        return "indexer"

    def fake_layout(root, validate, indexer):
        captured["root"] = root
        captured["validate"] = validate
        captured["indexer"] = indexer
        return "layout"

    monkeypatch.setattr("skullduggery.bids.bids.BIDSLayoutIndexer", fake_indexer)
    monkeypatch.setattr("skullduggery.bids.bids.BIDSLayout", fake_layout)

    patterns = _bidsignore_patterns('["sourcedata/**"]')
    args = argparse.Namespace(
        bids_path=str(tmp_path),
        bidsignore_patterns=patterns,
        no_strict_bids_validation=True,
    )

    result = create_bids_layout(args)

    assert result == "layout"
    assert captured["ignore"] == patterns
    assert captured["ignore"][0].match("sourcedata/sub-01/anat/file.nii.gz")
    assert captured["validate"] is False
