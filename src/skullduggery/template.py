import templateflow.api as tplflow
from typing import Dict, Any

def get_template(template_name: str, ref_bids_filters: Dict[str, Any]) -> str:
    # get appropriate contrast image from template name
    # and bids filters for the reference image
    suffix = ref_bids_filters["suffix"]

    tpl = tplflow.get(
        template_name,
        suffix = suffix,
        resolution = 1,
    )
    mask = tplflow.get(
        template_name,
        desc='brain',
        suffix='mask',
        resolution = 1,
    )
    # TODO: write fallback to get approximately matching contrasts
    # or suggest alternative templates with existing contrast
    # eg. it would be ok to use adult template for defacing infants, doesn't require precision
    # see https://www.templateflow.org/python-client/0.7.1/api/templateflow.api.html#templateflow.api.templates
    # for query mechanisms.

    if len(tpl) == 0:
        raise RuntimeError(f"failed to get contrast {suffix} from template:{template_name}")
    return tpl[0] if isinstance(tpl, list) else tpl, mask
