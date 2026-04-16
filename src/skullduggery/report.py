"""Report generation for defacing workflow results.

This module provides functionality to generate HTML reports and visualizations
of defacing results, including mosaic plots showing the application of defacing
masks to anatomical images.
"""
import json
import bids
from pathlib import Path
from nireports.assembler.report import Report
import nireports.assembler.report
from nireports.assembler import data as nr_data

from nibabel.spatialimages import SpatialImage

from nireports.interfaces.reporting.base import compose_view
from nireports.reportlets.mosaic import plot_segs

from importlib import resources

default_path_patterns = None


class DefaceReport(Report):
    """BIDS-compatible report generator for defacing results.

    Extends nireports Report class to generate reports structured around
    registration and defacing results, with automatic section organization.
    """
    def __init__(self, subject, session=None):
        super().__init__(subject, session)
        self.subject = subject

    def _load_config(self, config):
        """Load and configure report sections.

        Sets up report structure with Registration and Defacing sections
        that automatically discover corresponding SVG figures.

        Args:
            config: Configuration object (unused, inherited parameter).
        """
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
    """Generate a mosaic visualization of defacing results.

    Creates a mosaic SVG figure showing the defaced image overlaid with
    the warped defacing mask, useful for quality assurance and reporting.

    Args:
        masked_image: Defaced anatomical image as nibabel SpatialImage.
        warped_mask: Defacing mask in native image space as nibabel SpatialImage.
        output_path: Path where SVG output will be saved.

    Raises:
        OSError: If parent directory cannot be created or file cannot be written.
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
    """Generate BIDS-compliant path for a figure file.

    Constructs a BIDS-formatted path for saving figures (SVGs) derived from
    anatomical series, using the same entity structure as the source image.

    Args:
        layout: PyBIDS layout of the dataset.
        series: BIDSFile object of the source anatomical series.
        desc: Description label for the figure (e.g., "mask", "reg").

    Returns:
        Path: Complete path for the figure file in BIDS structure.

    Raises:
        RuntimeError: If figure path cannot be generated from entity structure.
    """
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
    """Generate final HTML report for defacing results.

    Creates an HTML report using nireports that combines registration and
    defacing visualizations for specified BIDS entities.

    Args:
        output_dir: Directory where report will be generated.
        **entities: BIDS entities for report customization (e.g., subject, session).

    Returns:
        Path: Absolute path to generated HTML report file.
    """
    robj = Report(
        output_dir,
        "TODO: make UUID",
        bootstrap_file=resources.files("skullduggery.data").joinpath("bootstrap-defacing.yml"),
        **entities,
    )
    robj.generate_report()
    return robj.out_filename.absolute()
