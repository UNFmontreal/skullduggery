from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from skullduggery.utils import _get_age_units, get_age_and_unit


def test_get_age_units():
    """Test age unit extraction and normalization from metadata."""
    # Valid units - should be normalized to lowercase
    assert _get_age_units({"age": {"Units": "weeks"}}) == "weeks"
    assert _get_age_units({"age": {"Units": "YEARS"}}) == "years"
    assert _get_age_units({"age": {"Units": "Months"}}) == "months"

    # Invalid units - should return False
    assert _get_age_units({"age": {"Units": "days"}}) is False
    assert _get_age_units({"age": {}}) is False
    assert _get_age_units({}) is False

    # Multiple units (should return False for ambiguity)
    assert _get_age_units({"age": {"Units": ["years", "months"]}}) is False


def test_get_age_and_unit_no_session(mocker):
    """Test age and unit extraction for participant without session info."""
    mock_layout = MagicMock()
    mock_participants_tsv = MagicMock()

    df = pd.DataFrame({"participant_id": ["sub-01", "sub-02"], "age": [25.5, 30.0]})

    mock_participants_tsv.get_df.return_value = df
    mock_participants_tsv.get_metadata.return_value = {"age": {"Units": "years"}}

    mock_layout.get.return_value = [mock_participants_tsv]

    age, unit = get_age_and_unit(mock_layout, subject="01")

    assert age == 25.5, "Expected age 25.5 for sub-01"
    assert unit == "years", "Expected unit years"


def test_get_age_and_unit_with_session(mocker):
    """Test age and unit extraction with session filtering."""
    mock_layout = MagicMock()
    mock_participants_tsv = MagicMock()

    df = pd.DataFrame(
        {
            "participant_id": ["sub-01", "sub-01"],
            "session_id": ["ses-1", "ses-2"],
            "age": [12.0, 18.0],
        }
    )

    mock_participants_tsv.get_df.return_value = df
    mock_participants_tsv.get_metadata.return_value = {"age": {"Units": "months"}}

    mock_layout.get.return_value = [mock_participants_tsv]

    age, unit = get_age_and_unit(mock_layout, subject="01", session="2")

    assert age == 18.0, "Expected age 18.0 for sub-01 ses-2"
    assert unit == "months", "Expected unit months"
