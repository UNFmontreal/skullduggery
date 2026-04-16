from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from skullduggery.template import DEFAULT_TEMPLATE, get_template


def test_get_template_no_cohort(mocker):
    # Mock templateflow.api
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")

    # Mock get_metadata to return empty cohort
    mock_tplflow.get_metadata.return_value = {}

    # Mock get to return dummy file paths
    mock_tpl = Path("/path/to/template.nii.gz")
    mock_reg = Path("/path/to/transform.mat")

    # get is called twice: once for the template, once for the regression
    # When template_name != DEFAULT_TEMPLATE, it gets called twice
    mock_tplflow.get.side_effect = [[mock_tpl], [mock_reg]]

    tpl, reg = get_template(template_name="MNI152NLin2009cAsym")

    assert tpl == mock_tpl
    assert reg == [mock_reg]

    # Verify exact calls to tplflow.get
    mock_tplflow.get.assert_any_call("MNI152NLin2009cAsym", suffix="T1w", resolution=1, cohort=None)


def test_get_template_with_cohort(mocker):
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")

    # Mock get_metadata for pediatric template
    mock_tplflow.get_metadata.return_value = {
        "cohort": {"1": {"units": "months", "age": [0.0, 2.0]}, "2": {"units": "months", "age": [2.0, 8.0]}}
    }

    mock_tpl = Path("/path/to/infant/template.nii.gz")
    mock_tplflow.get.side_effect = [mock_tpl]

    # Because we are passing DEFAULT_TEMPLATE, reg_to_default will be None!
    # Note: wait, "MNIInfant" != DEFAULT_TEMPLATE. So it will call twice.
    mock_tplflow.get.side_effect = [[mock_tpl], []]

    with pytest.raises(RuntimeError, match="is not appropriate for age"):
        get_template(template_name="MNIInfant", age=(1.0, "months"))


def test_get_template_missing_age_for_cohort(mocker):
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mock_tplflow.get_metadata.return_value = {"cohort": {"1": {"units": "months", "age": [0.0, 2.0]}}}

    with pytest.raises(RuntimeError, match="age is required for templates with cohorts"):
        get_template(template_name="MNIInfant")


def test_get_template_no_matching_cohort(mocker):
    mock_tplflow = mocker.patch("skullduggery.template.tplflow")
    mock_tplflow.get_metadata.return_value = {"cohort": {"1": {"units": "years", "age": [10.0, 15.0]}}}

    with pytest.raises(RuntimeError, match="is not appropriate for age"):
        get_template(template_name="MNIPediatric", age=(5.0, "years"))
