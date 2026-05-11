"""Report generation for defacing workflow results.

This module provides functionality to generate HTML reports and visualizations
of defacing results, including mosaic plots showing the application of defacing
masks to anatomical images.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

import bids
import nibabel as nb
import nireports.assembler.report
from nibabel.spatialimages import SpatialImage
from nireports.assembler import data as nr_data
from nireports.assembler.report import Report
from nireports.reportlets.utils import compose_view
from nireports.reportlets.mosaic import plot_segs

default_path_patterns = None

FALLBACK_FIGURE_ENTITY_ORDER = (
    "subject",
    "session",
    "task",
    "acquisition",
    "ceagent",
    "reconstruction",
    "direction",
    "run",
    "echo",
    "flip",
    "inversion",
    "mt",
    "part",
    "space",
    "desc",
)

FALLBACK_FIGURE_ENTITY_PREFIXES = {
    "subject": "sub",
    "session": "ses",
    "task": "task",
    "acquisition": "acq",
    "ceagent": "ce",
    "reconstruction": "rec",
    "direction": "dir",
    "run": "run",
    "echo": "echo",
    "flip": "flip",
    "inversion": "inv",
    "mt": "mt",
    "part": "part",
    "space": "space",
    "desc": "desc",
}


def _volume_image(image: SpatialImage, volume_index: int) -> SpatialImage:
    """Return one spatial volume from a 3D or 4D image."""
    if len(image.shape) == 3:
        return image
    if len(image.shape) != 4:
        raise ValueError(f"Expected a 3D or 4D image for reporting, got shape {image.shape}")

    header = image.header.copy()
    data = image.dataobj[..., volume_index]
    header.set_data_shape(image.shape[:3])
    return nb.Nifti1Image(data, image.affine, header)


def _iter_report_volumes(image: SpatialImage):
    """Yield the 3D volumes that should be shown in the defacing report."""
    if len(image.shape) == 3:
        yield None, image
        return
    if len(image.shape) != 4:
        raise ValueError(f"Expected a 3D or 4D image for reporting, got shape {image.shape}")

    for volume_index in range(image.shape[3]):
        yield volume_index, _volume_image(image, volume_index)


def _matching_report_volume(image: SpatialImage, volume_index: int | None) -> SpatialImage:
    """Return the corresponding 3D report volume, reusing 3D images for every view."""
    if len(image.shape) == 3:
        return image
    if volume_index is None:
        return _volume_image(image, 0)
    return _volume_image(image, min(volume_index, image.shape[3] - 1))


def _add_plot(svgs: list[str], plot_output) -> None:
    if isinstance(plot_output, (list, tuple)):
        svgs.extend(plot_output)
    else:
        svgs.append(plot_output)


def _format_bids_entity(name: str, value: Any) -> str | None:
    if value is None:
        return None
    prefix = FALLBACK_FIGURE_ENTITY_PREFIXES[name]
    if name == "desc" and str(value).startswith("desc-"):
        return str(value)
    if name == "subject" and str(value).startswith("sub-"):
        return str(value)
    if name == "session" and str(value).startswith("ses-"):
        return str(value)
    return f"{prefix}-{value}"


def _fallback_figure_path(entities: dict[str, Any]) -> Path:
    suffix = entities.get("suffix")
    if not suffix:
        raise RuntimeError(f"Cannot generate a figure path without a suffix: {entities}")

    filename_parts = []
    for entity in FALLBACK_FIGURE_ENTITY_ORDER:
        entity_part = _format_bids_entity(entity, entities.get(entity))
        if entity_part:
            filename_parts.append(entity_part)
    filename_parts.append(str(suffix))

    path_parts = []
    subject = _format_bids_entity("subject", entities.get("subject"))
    session = _format_bids_entity("session", entities.get("session"))
    if subject:
        path_parts.append(subject)
    if session:
        path_parts.append(session)
    path_parts.append("figures")

    return Path(*path_parts) / ("_".join(filename_parts) + ".svg")


def generate_deface_mosaic_report(
    masked_image: SpatialImage,
    warped_mask: SpatialImage,
    output_path: Path,
    registered_tmpl: SpatialImage | None = None,
) -> None:
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

    bg_svgs = []
    fg_svgs = []
    for volume_index, masked_volume in _iter_report_volumes(masked_image):
        volume_label = "" if volume_index is None else f" volume {volume_index + 1}"
        mask_volume = _matching_report_volume(warped_mask, volume_index)
        if registered_tmpl:
            registered_volume = _matching_report_volume(registered_tmpl, volume_index)
            _add_plot(
                bg_svgs,
                plot_segs(
                    image_nii=registered_volume,
                    seg_niis=[mask_volume],
                    bbox_nii=masked_volume,
                    masked=True,
                    title=f"reference{volume_label}",
                ),
            )
        _add_plot(
            fg_svgs,
            plot_segs(
                image_nii=masked_volume,
                seg_niis=[mask_volume],
                bbox_nii=masked_volume,
                masked=True,
                title=f"defaced{volume_label}",
            ),
        )

    compose_view(
        bg_svgs=bg_svgs,
        fg_svgs=fg_svgs,
        out_file=output_path,
    )


def generate_figure_path(
    layout: bids.BIDSLayout,
    series: bids.layout.BIDSFile,
    desc: str,
    report_dir: Path | None = None,
) -> Path:
    """Generate BIDS-compliant path for a figure file.

    Constructs a BIDS-formatted path for saving figures (SVGs) derived from
    anatomical series, using the same entity structure as the source image.

    Args:
        layout: PyBIDS layout of the dataset.
        series: BIDSFile object of the source anatomical series.
        desc: Description label for the figure (e.g., "mask", "reg").
        report_dir: Optional directory root for figures. If provided, figures
            are placed under this directory instead of the dataset root.

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
        path = _fallback_figure_path(entities)
    root = Path(report_dir) if report_dir else layout._root
    return root / path


def generate_report(
    output_dir: str | Path,
    run_uuid: str | None = None,
    **entities: Any,
) -> Path:
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
        run_uuid,
        bootstrap_file=resources.files("skullduggery.data").joinpath("bootstrap-defacing.yml"),
        **entities,
    )
    robj.generate_report()
    return robj.out_filename.absolute()
