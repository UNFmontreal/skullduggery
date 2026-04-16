from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import bids
import nireports.assembler.report
from nibabel.spatialimages import SpatialImage
from nireports.assembler import data as nr_data
from nireports.assembler.report import Report
from nireports.interfaces.reporting.base import compose_view
from nireports.reportlets.mosaic import plot_segs

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


def generate_figure_path(layout: bids.BIDSLayout, report_dir: Path, series: bids.layout.BIDSFile, desc: str) -> Path:
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


def generate_report(output_dir, **entities):
    robj = Report(
        output_dir,
        "TODO: make UUID",
        bootstrap_file=resources.files("skullduggery.data").joinpath("bootstrap-defacing.yml"),
        **entities,
    )
    robj.generate_report()
    return robj.out_filename.absolute()
