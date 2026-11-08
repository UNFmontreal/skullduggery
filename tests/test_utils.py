from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from bids import BIDSLayout

import pandas as pd
import pytest

from skullduggery.utils import _get_age_units, filters_query, get_age_and_unit, group_series


def test_get_age_units():
    """Test age unit extraction and normalization from metadata."""
    # Valid units - should be normalized to lowercase
    assert _get_age_units({"age": {"Units": "weeks"}}) == "weeks"
    assert _get_age_units({"age": {"Units": "YEARS"}}) == "years"
    assert _get_age_units({"age": {"Units": "Months"}}) == "months"
    assert _get_age_units({"age": {"Units": "year"}}) == "years"
    assert _get_age_units({"age": {"Units": "month"}}) == "months"
    assert _get_age_units({"age": {"Units": " Week "}}) == "weeks"
    assert _get_age_units({"age": None}) is False

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

    mock_layout.get.side_effect = [[], [mock_participants_tsv]]

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

    mock_layout.get.side_effect = [[], [mock_participants_tsv]]

    age, unit = get_age_and_unit(mock_layout, subject="01", session="2")

    assert age == 18.0, "Expected age 18.0 for sub-01 ses-2"
    assert unit == "months", "Expected unit months"


def test_filters_query(mocker):
    """Test querying BIDS layout with multiple filter sets."""
    mock_layout = MagicMock()

    # Create mock BIDSFile objects
    mock_file1 = MagicMock()
    mock_file1.path = "/path/to/sub-01_T1w.nii.gz"

    mock_file2 = MagicMock()
    mock_file2.path = "/path/to/sub-01_T2w.nii.gz"

    mock_file3 = MagicMock()
    mock_file3.path = "/path/to/sub-01_FLAIR.nii.gz"

    # Mock layout.get to return different files for different filters
    mock_layout.get.side_effect = [[mock_file1, mock_file2], [mock_file3]]

    bids_filters = [
        {"suffix": ["T1w", "T2w"]},
        {"suffix": "FLAIR"},
    ]

    result = filters_query(mock_layout, subject="01", session=None, bids_filters=bids_filters)

    # Should return all files from all filters
    assert len(result) == 3
    assert mock_file1 in result
    assert mock_file2 in result
    assert mock_file3 in result

    # Verify layout.get was called with correct parameters
    assert mock_layout.get.call_count == 2


def test_filters_query_with_session(mocker):
    """Test filters_query with session parameter."""
    mock_layout = MagicMock()

    mock_file = MagicMock()
    mock_file.path = "/path/to/sub-01_ses-01_T1w.nii.gz"

    mock_layout.get.return_value = [mock_file]

    bids_filters = [{"suffix": "T1w"}]

    result = filters_query(mock_layout, subject="01", session="01", bids_filters=bids_filters)

    assert len(result) == 1
    assert mock_file in result

    # Verify session was passed to layout.get
    mock_layout.get.assert_called_once()
    call_kwargs = mock_layout.get.call_args[1]
    assert call_kwargs["session"] == "01"


@pytest.fixture
def session_dataset(tmp_path):
    """New exporter layout, indexed by real PyBIDS rather than mocked queries."""
    (tmp_path / "dataset_description.json").write_text(json.dumps({"Name": "Test", "BIDSVersion": "1.10.0"}))
    (tmp_path / "participants.tsv").write_text("participant_id\tsex\nsub-001\tF\nsub-002\tM\n")
    subject = tmp_path / "sub-001"
    subject.mkdir()
    for session in ("1a", "2a"):
        (subject / f"ses-{session}").mkdir()
    table = subject / "sub-001_sessions.tsv"
    table.write_text("session_id\tage\nses-1a\t1.5\nses-2a\t2.5\n")
    table.with_suffix(".json").write_text(json.dumps({"age": {"Units": "year"}}))
    return tmp_path, table


def test_session_age_with_real_pybids(session_dataset):
    root, _ = session_dataset
    layout = BIDSLayout(root)
    assert get_age_and_unit(layout, "001", "1a") == (1.5, "years")
    assert get_age_and_unit(layout, "sub-001", "ses-2a") == (2.5, "years")
    assert get_age_and_unit(layout, "002", "1a") is None


@pytest.mark.parametrize(
    "case", ["missing", "duplicate", "no_id", "n/a", "nan", "inf", "-1", "invalid", "no_session"]
)
def test_session_table_does_not_fall_back_to_baseline(session_dataset, case):
    root, table = session_dataset
    (root / "participants.tsv").write_text("participant_id\tage\tsex\nsub-001\t99\tF\n")
    (root / "participants.json").write_text(json.dumps({"age": {"Units": "years"}}))
    contents = {
        "missing": "session_id\tage\nses-1a\t1.5\n",
        "duplicate": "session_id\tage\nses-2a\t2.5\nses-2a\t3\n",
        "no_id": "age\n2.5\n",
    }.get(case, f"session_id\tage\nses-2a\t{case}\n")
    table.write_text(contents)
    assert get_age_and_unit(BIDSLayout(root), "001", None if case == "no_session" else "2a") is None


def test_legacy_fallback_and_missing_participants(session_dataset):
    root, table = session_dataset
    table.unlink()
    table.with_suffix(".json").unlink()
    (root / "participants.tsv").write_text("participant_id\tage\nsub-001\t6\n")
    (root / "participants.json").write_text(json.dumps({"age": {"Units": "month"}}))
    assert get_age_and_unit(BIDSLayout(root), "001", "2a") == (6, "months")
    (root / "participants.tsv").unlink()
    assert get_age_and_unit(BIDSLayout(root), "001", "2a") is None


@pytest.mark.parametrize("has_sessions_table", [False, True])
@pytest.mark.parametrize("metadata", [None, {"age": {}}, {"age": {"Units": "month"}}])
def test_participant_age_when_session_age_not_defined(session_dataset, has_sessions_table, metadata):
    root, table = session_dataset
    if has_sessions_table:
        table.write_text("session_id\tacq_time\nses-1a\tn/a\nses-2a\tn/a\n")
        # This sidecar must not determine the units of participant-level age.
        table.with_suffix(".json").write_text(json.dumps({"acq_time": {"Description": "Acquisition time"}}))
    else:
        table.unlink()
        table.with_suffix(".json").unlink()
    (root / "participants.tsv").write_text("participant_id\tage\tsex\nsub-001\t6\tF\nsub-002\t9\tM\n")
    if metadata is not None:
        (root / "participants.json").write_text(json.dumps(metadata))
    layout = BIDSLayout(root)
    unit = "months" if metadata and metadata.get("age", {}).get("Units") else "years"
    for session in (None, "1a", "2a"):
        assert get_age_and_unit(layout, "001", session) == (6, unit)
    assert get_age_and_unit(layout, "002", "1a") == (9, unit)


def _participants_layout(df, units="months"):
    tsv = MagicMock()
    tsv.get_df.return_value = df
    tsv.get_metadata.return_value = {"age": {"Units": units}} if units else {}
    layout = MagicMock()
    layout.get.return_value = [tsv]
    return layout


def test_get_age_and_unit_filters_by_session():
    import pandas as pd

    df = pd.DataFrame(
        {
            "participant_id": ["sub-01", "sub-01"],
            "session_id": ["ses-pre", "ses-post"],
            "age": [3.0, 5.0],
        }
    )
    layout = _participants_layout(df)
    assert get_age_and_unit(layout, "01", "post") == (5.0, "months")


def test_get_age_and_unit_without_age_column_returns_none():
    import pandas as pd

    layout = _participants_layout(pd.DataFrame({"participant_id": ["sub-01"]}))
    assert get_age_and_unit(layout, "01") is None


def test_get_age_and_unit_missing_participant_returns_none():
    import pandas as pd

    layout = _participants_layout(pd.DataFrame({"participant_id": ["sub-02"], "age": [3.0]}))
    assert get_age_and_unit(layout, "01") is None


def test_get_age_and_unit_without_supported_units_returns_none():
    import pandas as pd

    layout = _participants_layout(pd.DataFrame({"participant_id": ["sub-01"], "age": [3.0]}), units="fortnights")
    assert get_age_and_unit(layout, "01") is None


def test_get_age_units_non_string_units_is_rejected():
    assert _get_age_units({"age": {"Units": ["months", "years"]}}) is False


def test_get_age_units_missing_field_is_rejected():
    assert _get_age_units({}) is False


def _entity_file(path, **entities):
    return SimpleNamespace(path=path, entities=entities, get_entities=lambda metadata=False: dict(entities))


def test_group_series_groups_echo_and_part_variants_together():
    mag_echo1 = _entity_file("a_echo-1_part-mag_T1w.nii.gz", subject="01", suffix="T1w", echo="1", part="mag")
    phase_echo1 = _entity_file("a_echo-1_part-phase_T1w.nii.gz", subject="01", suffix="T1w", echo="1", part="phase")
    mag_echo2 = _entity_file("a_echo-2_part-mag_T1w.nii.gz", subject="01", suffix="T1w", echo="2", part="mag")
    other = _entity_file("b_T1w.nii.gz", subject="01", suffix="T2w")

    groups = list(group_series([mag_echo1, phase_echo1, mag_echo2, other], ref_image=other))

    assert len(groups) == 2
    _, groupref, members = groups[0]
    assert groupref is mag_echo1
    assert members == [mag_echo1, phase_echo1, mag_echo2]
    assert groups[1][1] is other


def test_group_series_prefers_reference_image_as_representative():
    first = _entity_file("x_T1w.nii.gz", subject="01", suffix="T1w")
    ref = _entity_file("y_T1w.nii.gz", subject="01", suffix="T1w")
    ((_, groupref, _),) = group_series([first, ref], ref_image=ref)
    assert groupref is ref


def test_filters_query_combines_results_from_each_filter_set():
    layout = MagicMock()
    layout.get.side_effect = [["t1"], ["t2a", "t2b"]]
    result = filters_query(layout, "01", None, [{"suffix": "T1w"}, {"suffix": "T2w"}])
    assert result == ["t1", "t2a", "t2b"]
    assert layout.get.call_args_list[0].kwargs == {
        "extension": ["nii", "nii.gz"],
        "subject": "01",
        "session": None,
        "suffix": "T1w",
    }
