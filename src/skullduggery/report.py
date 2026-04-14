import json
import bids
from pathlib import Path
from nireports.assembler.report import Report
import nireports.assembler.report
from nireports.assembler import data as nr_data

from nibabel.spatialimages import SpatialImage

from nireports.interfaces.reporting.base import compose_view
from nireports.reportlets.mosaic import plot_segs

"""
bids_config_path = nr_data.load("nipreps.json")
bids_config = json.loads(bids_config_path.read_bytes())
# append a generic pattern, for suffix not covered by current nireports config (eg. MEGRE)
bids_config["default_path_patterns"].append("sub-{subject}/{datatype<figures>}/sub-{subject}[_ses-{session}][_acq-{acquisition}][_ce-{ceagent}][_rec-{reconstruction}][_run-{run}][_space-{space}][_cohort-{cohort}][_desc-{desc}]_{suffix}{extension<.html|.svg>|.svg}")
"""

default_path_patterns = None


class DefaceReport(Report):
    def __init__(self, subject, session=None):
        super().__init__(subject, session)
        self.subject = subject

    def _load_config(self, config):
        self.sections = [
            {
                "name": "Registration",
                "reportlets": [{"pattern": "**/sub-{subject}_ses-{session}_*desc-reg_*.svg"}],
            },
            {
                "name": "Defacing",
                "reportlets": [{"pattern": "**/sub-{subject}_ses-{session}_*desc-mask_*.svg"}],
            },
        ]


def generate_deface_mosaic_report(masked_image: SpatialImage, warped_mask: SpatialImage, output_path: Path):
    """
    Generates a mosaic illustrating the results of the deface
    registration showing the defaced image against the warped mask.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    compose_view(
        plot_segs(
            image_nii=masked_image,
            seg_niis=[warped_mask],
            # bbox_nii=warped_mask,
            masked=True,
        ),
        fg_svgs=None,
        out_file=output_path,
    )


def generate_figure_path(layout: bids.BIDSLayout, series: bids.layout.BIDSFile, desc: str) -> Path:
    entities = series.get_entities(metadata=False)
    entities["datatype"] = "figures"
    entities["desc"] = desc
    entities["extension"] = ".svg"
    global default_path_patterns
    if not default_path_patterns:
        default_path_patterns = []
        for p in layout.config["bids"].default_path_patterns:
            if "{datatype<anat>|anat}" in p:
                pattern = p.replace("{datatype<anat>|anat}", "{datatype<figures>|figures}")
                pattern = pattern.replace("{extension<.nii|.nii.gz|.json>|.nii.gz}", "{extension<.svg>|.svg}")
                pattern = pattern.replace("_{suffix", "[_desc-{desc}]_{suffix")
                default_path_patterns.append(pattern)

    path = bids.layout.layout.build_path(entities, path_patterns=default_path_patterns)
    if not path:
        raise RuntimeError(f"Cannot generate a figure path for {entities}")
    return layout._root / path
