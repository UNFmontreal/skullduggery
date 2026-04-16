from __future__ import annotations

from pathlib import Path

import pytest

from skullduggery.template import get_template


def test_get_template_no_cohort(mocker):
    """Test template retrieval without age-based cohorts."""
    # Mock templateflow.api
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")

    # Mock get_metadata to return empty cohort
    mock_tplflow.get_metadata.return_value = {}

    # Mock get to return dummy file paths
    mock_tpl = Path("/path/to/template.nii.gz")
    mock_reg = Path("/path/to/transform.mat")

    # get is called twice: once for the template, once for the transform
    # When template_name != DEFAULT_TEMPLATE, it gets called twice
    mock_tplflow.get.side_effect = [[mock_tpl], [mock_reg]]

    tpl, reg = get_template(template_name="MNI152NLin2009cAsym")

    assert tpl == mock_tpl
    assert reg == [mock_reg]

    # Verify exact calls to tplflow.get
    mock_tplflow.get.assert_any_call("MNI152NLin2009cAsym", suffix="T1w", resolution=1, cohort=None)


def test_get_template_with_cohort(mocker):
    """Test template retrieval with age-based cohort selection."""
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")

    # Mock get_metadata for pediatric template with cohorts
    mock_tplflow.get_metadata.return_value = {
        "cohort": {"0-2mo": {"units": "months", "age": [0.0, 2.0]}, "2-8mo": {"units": "months", "age": [2.0, 8.0]}}
    }

    mock_tpl = Path("/path/to/infant/template.nii.gz")
    mock_reg = Path("/path/to/infant_to_default.mat")

    # Template is called twice: once for template image, once for transform
    mock_tplflow.get.side_effect = [[mock_tpl], [mock_reg]]

    # Should succeed with age 1.0 months which matches the 0-2mo cohort
    tpl, reg = get_template(template_name="MNIInfant", age=(1.0, "months"))

    assert tpl == mock_tpl
    assert reg == [mock_reg]


def test_get_template_missing_age_for_cohort(mocker):
    """Test error when age is required but not provided."""
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mock_tplflow.get_metadata.return_value = {"cohort": {"1": {"units": "months", "age": [0.0, 2.0]}}}

    with pytest.raises(RuntimeError, match="age is required for templates with cohorts"):
        get_template(template_name="MNIInfant")


def test_get_template_no_matching_cohort(mocker):
    """Test error when age doesn't match any available cohort."""
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mock_tplflow.get_metadata.return_value = {"cohort": {"1": {"units": "years", "age": [10.0, 15.0]}}}

    with pytest.raises(RuntimeError, match="is not appropriate for age"):
        get_template(template_name="MNIPediatric", age=(5.0, "years"))


def test_get_template_unit_mismatch(mocker):
    """Test error when age unit doesn't match cohort unit."""
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mock_tplflow.get_metadata.return_value = {"cohort": {"1": {"units": "years", "age": [5.0, 10.0]}}}

    with pytest.raises(RuntimeError, match="is not appropriate for age"):
        get_template(template_name="MNIPediatric", age=(60.0, "months"))
