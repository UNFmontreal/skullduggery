from __future__ import annotations

from pathlib import Path

from skullduggery.reports import build_report_paths, strip_image_suffix


def test_strip_image_suffix_handles_nifti_extensions():
    assert strip_image_suffix("sub-01_T1w.nii.gz") == "sub-01_T1w"
    assert strip_image_suffix("sub-01_T1w.nii") == "sub-01_T1w"


def test_build_report_paths_preserves_bids_hierarchy(tmp_path: Path):
    report_paths = build_report_paths(
        tmp_path,
        "sub-01/ses-02/anat/sub-01_ses-02_T1w.nii.gz",
    )

    assert report_paths.html == (tmp_path / "sub-01_ses-02_T1w.html")
    assert report_paths.mosaic_svg == (
        tmp_path
        / "figures"
        / "sub-01"
        / "ses-02"
        / "anat"
        / "sub-01_ses-02_T1w_desc-deface_mosaic.svg"
    )
    assert report_paths.mosaic_svg.name == "sub-01_ses-02_T1w_desc-deface_mosaic.svg"
