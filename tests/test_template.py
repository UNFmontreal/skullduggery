from __future__ import annotations

from pathlib import Path

import pytest

from skullduggery.template import convert_age, get_template, select_template_by_age


def test_get_template_no_cohort(mocker):
    """Test template retrieval without age-based cohorts."""
    # Mock templateflow.api
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")

    # Mock get_metadata to return empty cohort
    mock_tplflow.get_metadata.return_value = {}

    # Mock get to return dummy file paths
    mock_tpl = Path("/path/to/template.nii.gz")
    mock_mask = Path("/path/to/template_mask.nii.gz")
    mock_reg = Path("/path/to/transform.mat")

    # get is called three times for non-default templates:
    # 1. for template image, 2. for mask, 3. for transform to default
    mock_tplflow.get.side_effect = [mock_tpl, mock_mask, mock_reg]

    tpl, mask, reg = get_template(template_name="MNI152NLin2009cAsym")

    assert tpl == mock_tpl
    assert mask == mock_mask
    assert reg == mock_reg

    # Verify exact calls to tplflow.get
    assert mock_tplflow.get.call_count == 3


def test_get_template_with_cohort(mocker):
    """Test template retrieval with age-based cohort selection."""
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mocker.patch("skullduggery.template.convert_age", return_value=1.0)

    # Mock get_metadata for pediatric template with cohorts
    mock_tplflow.get_metadata.return_value = {
        "cohort": {"0-2mo": {"units": "months", "age": [0.0, 2.0]}, "2-8mo": {"units": "months", "age": [2.0, 8.0]}}
    }

    mock_tpl = Path("/path/to/infant/template.nii.gz")
    mock_mask = Path("/path/to/infant/mask.nii.gz")
    mock_reg = Path("/path/to/infant_to_default.mat")

    # Template with cohort: get is called 3 times (tpl, mask, transform)
    mock_tplflow.get.side_effect = [mock_tpl, mock_mask, mock_reg]

    # Should succeed with age 1.0 months which matches the 0-2mo cohort
    tpl, mask, reg = get_template(template_name="MNIInfant", age=(1.0, "months"))

    assert tpl == mock_tpl
    assert mask == mock_mask
    assert reg == mock_reg


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
    """Test that age unit conversion works correctly with cohort matching."""
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mocker.patch("skullduggery.template.convert_age", return_value=5.0)

    # Mock get_metadata with cohort expecting years
    mock_tplflow.get_metadata.return_value = {"cohort": {"1": {"units": "years", "age": [5.0, 10.0]}}}

    mock_tpl = Path("/path/to/template.nii.gz")
    mock_mask = Path("/path/to/mask.nii.gz")
    mock_reg = Path("/path/to/transform.mat")

    mock_tplflow.get.side_effect = [mock_tpl, mock_mask, mock_reg]

    # Age in months (60 = 5 years) should convert and match [5.0, 10.0] range
    tpl, mask, reg = get_template(template_name="MNIPediatric", age=(60.0, "months"))

    assert tpl == mock_tpl
    assert mask == mock_mask
    assert reg == mock_reg


def test_get_template_age_out_of_range(mocker):
    """Test error when converted age is out of cohort range."""
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mocker.patch("skullduggery.template.convert_age", return_value=15.0)

    mock_tplflow.get_metadata.return_value = {"cohort": {"1": {"units": "years", "age": [5.0, 10.0]}}}

    # Converted age 15.0 is outside [5.0, 10.0] range
    with pytest.raises(RuntimeError, match="is not appropriate for age"):
        get_template(template_name="MNIPediatric", age=(180.0, "months"))


def test_convert_age():
    """Test age unit conversion between weeks, months, and years."""
    # Test conversions to weeks
    assert convert_age(2.0, "weeks", "weeks") == 2.0
    assert abs(convert_age(1.0, "months", "weeks") - 4.34) < 0.1
    assert abs(convert_age(1.0, "years", "weeks") - 52.14) < 0.1

    # Test conversions to months
    assert abs(convert_age(8.68, "weeks", "months") - 2.0) < 0.1
    assert convert_age(3.0, "months", "months") == 3.0
    assert abs(convert_age(1.0, "years", "months") - 12.0) < 0.1

    # Test conversions to years
    assert abs(convert_age(52.14, "weeks", "years") - 1.0) < 0.1
    assert abs(convert_age(24.0, "months", "years") - 2.0) < 0.1
    assert convert_age(5.0, "years", "years") == 5.0


def test_convert_age_invalid_unit():
    """Test error handling for invalid units in age conversion."""
    with pytest.raises(ValueError, match="Unsupported units"):
        convert_age(5.0, "days", "years")

    with pytest.raises(ValueError, match="Unsupported units"):
        convert_age(5.0, "years", "days")


def test_select_template_by_age():
    """Test automatic template selection based on participant age."""
    from skullduggery.template import DEFAULT_TEMPLATE, PEDIATRIC_TEMPLATE

    # No age - should default to adult template
    assert select_template_by_age(None) == DEFAULT_TEMPLATE

    # Age in weeks - should use pediatric template
    assert select_template_by_age((8.0, "weeks")) == PEDIATRIC_TEMPLATE

    # Age in months - should use pediatric template
    assert select_template_by_age((12.0, "months")) == PEDIATRIC_TEMPLATE

    # Age < 2 years - should use pediatric template
    assert select_template_by_age((1.5, "years")) == PEDIATRIC_TEMPLATE

    # Age >= 2 years - should use adult template
    assert select_template_by_age((2.0, "years")) == DEFAULT_TEMPLATE
    assert select_template_by_age((5.0, "years")) == DEFAULT_TEMPLATE
