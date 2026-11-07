from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from bids.layout import Query

import argparse

from skullduggery import bids as bids_module
from skullduggery.bids import _bids_filter, _filter_pybids_any, create_bids_layout


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


def test_bids_filter_inline_json_converts_wildcards():
    assert _bids_filter('{"suffix": "*", "datatype": "anat"}') == {"suffix": Query.ANY, "datatype": "anat"}


def test_create_bids_layout_uses_absolute_path_and_strictness(mocker, tmp_path):
    layout_cls = mocker.patch.object(bids_module.bids, "BIDSLayout", return_value=MagicMock())
    args = argparse.Namespace(bids_path=str(tmp_path / "ds"), no_strict_bids_validation=True)

    create_bids_layout(args)

    layout_cls.assert_called_once_with(str(tmp_path / "ds"), validate=False)


def test_create_bids_layout_validates_by_default(mocker, tmp_path):
    layout_cls = mocker.patch.object(bids_module.bids, "BIDSLayout", return_value=MagicMock())
    args = argparse.Namespace(bids_path=str(tmp_path), no_strict_bids_validation=False)

    create_bids_layout(args)

    assert layout_cls.call_args.kwargs == {"validate": True}
