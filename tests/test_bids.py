from __future__ import annotations

import pytest
from bids.layout import Query

from skullduggery.bids import _bids_filter, _filter_pybids_any


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
