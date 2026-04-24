"""Template selection and retrieval utilities.

This module provides functions for retrieving templates from TemplateFlow,
including support for age-specific cohorts and template transformations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import templateflow.api as tplflow

DEFAULT_TEMPLATE = "MNI152NLin6Asym"
PEDIATRIC_TEMPLATE = "MNIInfant"


def convert_age(age_value: float, from_unit: str, to_unit: str) -> float:
    """Convert age between different time units.

    Converts age values between weeks, months, and years with standard conversions.

    Args:
        age_value: Numeric age value to convert.
        from_unit: Source unit - one of "weeks", "months", "years".
        to_unit: Target unit - one of "weeks", "months", "years".

    Returns:
        float: Age converted to target unit.

    Raises:
        ValueError: If units are invalid or not supported.
    """
    valid_units = ("weeks", "months", "years")
    if from_unit not in valid_units or to_unit not in valid_units:
        raise ValueError(f"Unsupported units. Must be one of {valid_units}")

    if from_unit == to_unit:
        return age_value

    # Convert to weeks first as base unit
    if from_unit == "weeks":
        weeks = age_value
    elif from_unit == "months":
        weeks = age_value * (52.1429 / 12)  # weeks per month average
    else:  # from_unit == "years"
        weeks = age_value * 52.1429  # weeks per year average

    # Convert from weeks to target unit
    if to_unit == "weeks":
        return weeks
    elif to_unit == "months":
        return weeks * (12 / 52.1429)
    else:  # to_unit == "years"
        return weeks / 52.1429


def select_template_by_age(age: tuple[float, str] | None) -> str:
    """Automatically select an appropriate template based on participant age.

    Determines whether to use a pediatric or adult template based on the
    participant's age. This function implements a simple heuristic for
    automatic template selection when no explicit template is specified.

    Args:
        age: Tuple of (age_value, age_unit) where age_unit is one of
            ("weeks", "months", "years"), or None.

    Returns:
        str: Template name - either PEDIATRIC_TEMPLATE (MNIInfant) for young
            participants or DEFAULT_TEMPLATE (MNI152NLin6Asym) for others.

    Logic:
        - Uses MNIInfant if age is in weeks or months
        - Uses MNIInfant if age is less than 2 years
        - Uses MNI152NLin6Asym (adult template) otherwise
    """
    if age is None:
        return DEFAULT_TEMPLATE

    age_value, age_unit = age

    # Use pediatric template for ages in weeks or months
    if age_unit in ("weeks", "months"):
        return PEDIATRIC_TEMPLATE

    # Use pediatric template for ages < 2 years
    if age_unit == "years" and age_value < 2:
        return PEDIATRIC_TEMPLATE

    # Default to adult template
    return DEFAULT_TEMPLATE


def get_template(
    template_name: str = DEFAULT_TEMPLATE,
    bids_filters: dict[str, Any] = {"suffix": "T1w"},
    age: tuple[float, str] | None = None,
    resolution=1,
) -> tuple[Path, Path]:
    """Retrieve template and transformation files from TemplateFlow.

    Fetches the specified template and optional transform to default template,
    with automatic cohort selection for age-stratified templates.

    Args:
        template_name: TemplateFlow template name. Defaults to MNI152NLin6Asym.
        bids_filters: BIDS entity filters for template selection.
            Defaults to {"suffix": "T1w"}.
        age: Tuple of (age_value, age_unit) for cohort selection.
            Required if template has cohorts. Units must match template definition.
        resolution: Template resolution in mm. Defaults to 1.

    Returns:
        tuple: (template_path, transform_to_default_path) where:
            - template_path: Path to selected template image
            - transform_to_default_path: Path to transform to DEFAULT_TEMPLATE,
              or None if template is already the default

    Raises:
        RuntimeError: If age is required but not provided, template/suffix
            not found, or age does not match any cohort.
    """
    # get appropriate contrast image from template name
    # and bids filters for the reference image
    suffix = bids_filters["suffix"]
    cohort = None
    tpl_metas = tplflow.get_metadata(template_name)
    if tpl_metas.get("cohort"):
        if not age:
            raise RuntimeError("age is required for templates with cohorts")
        
        age_value, age_unit = age
        for _cohort, cohort_metas in tpl_metas.get("cohort").items():
            cohort_units = cohort_metas["units"]
            # Convert age to the units expected by this cohort
            converted_age = convert_age(age_value, age_unit, cohort_units)
            if cohort_metas["age"][0] <= converted_age < cohort_metas["age"][1]:
                cohort = _cohort
                break
        
        if cohort is None:
            raise RuntimeError(f"template {template_name} is not appropriate for age {age}")

    tpl = tplflow.get(
        template_name,
        suffix=suffix,
        resolution=resolution,
        cohort=cohort,
    )

    reg_to_default = (
        tplflow.get(
            template_name,
            suffix="xfm",
            cohort=cohort,
            **{"from": DEFAULT_TEMPLATE},  # from is a python reserved keyword
        )
        if template_name != DEFAULT_TEMPLATE
        else None
    )

    # TODO: write fallback to get approximately matching contrasts
    # or suggest alternative templates with existing contrast
    # eg. it would be ok to use adult template for defacing infants, doesn't require precision
    # see https://www.templateflow.org/python-client/0.7.1/api/templateflow.api.html#templateflow.api.templates
    # for query mechanisms.

    if isinstance(tpl, list) and len(tpl) == 0:
        raise RuntimeError(f"failed to get contrast {suffix} from template:{template_name}")
    if tpl is None:
        raise RuntimeError(f"failed to get contrast {suffix} from template:{template_name}")
    if isinstance(reg_to_default, list) and len(reg_to_default) == 0:
        raise RuntimeError(f"failed to get transform to default template from template:{template_name}")
    return tpl[0] if isinstance(tpl, list) else tpl, reg_to_default
