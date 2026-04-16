"""Template selection and retrieval utilities.

This module provides functions for retrieving templates from TemplateFlow,
including support for age-specific cohorts and template transformations.
"""
import templateflow.api as tplflow
from typing import Dict, Any, Tuple
from pathlib import Path
from typing import Any

import templateflow.api as tplflow

DEFAULT_TEMPLATE = "MNI152NLin6Asym"


def get_template(
    template_name: str = DEFAULT_TEMPLATE,
    bids_filters: dict[str, Any] = {"suffix": "T1w"},
    age: tuple[float, str] | None = None,
    resolution=1,
) -> Tuple[Path, Path]:
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
        for _cohort, cohort_metas in tpl_metas.get("cohort").items():
            if age[1] == cohort_metas["units"]:
                if cohort_metas["age"][0] <= age[0] < cohort_metas["age"][1]:
                    break
        else:
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

    if len(tpl) == 0:
        raise RuntimeError(f"failed to get contrast {suffix} from template:{template_name}")
    if isinstance(reg_to_default, list) and len(reg_to_default) == 0:
        raise RuntimeError(f"failed to get transform to default template from template:{template_name}")
    return tpl[0] if isinstance(tpl, list) else tpl, reg_to_default
