from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import templateflow.api as tplflow

DEFAULT_TEMPLATE = "MNI152NLin6Asym"


def get_template(
    template_name: str = DEFAULT_TEMPLATE,
    bids_filters: dict[str, Any] = {"suffix": "T1w"},
    age: tuple[float, str] | None = None,
    resolution=1,
) -> tuple[Path, Path]:
    # get appropriate contrast image from template name
    # and bids filters for the reference image
    suffix = bids_filters["suffix"]
    cohort = None
    tpl_metas = tplflow.get_metadata(template_name)
    if tpl_metas.get("cohort"):
        if not age:
            raise RuntimeError("age is required for templates with cohorts")
        for cohort, cohort_metas in tpl_metas.get("cohort").items():
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
