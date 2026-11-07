from __future__ import annotations

from pathlib import Path

import bids
import numpy as np
import pytest

from skullduggery import report
from skullduggery.report import (
    _add_plot,
    _fallback_figure_path,
    _format_bids_entity,
    _iter_report_volumes,
    _matching_report_volume,
    _volume_image,
    generate_deface_mosaic_report,
    generate_figure_path,
    generate_report,
)


def _image(shape, value=1.0):
    import nibabel as nb

    return nb.Nifti1Image(np.full(shape, value, dtype=np.float32), np.eye(4))


def test_volume_image_3d_passthrough():
    img = _image((4, 4, 4))
    assert _volume_image(img, 0) is img


def test_volume_image_extracts_4d_frame():
    img = _image((4, 4, 4, 3), value=0)
    img.dataobj[..., 1] = 7
    vol = _volume_image(img, 1)
    assert vol.shape == (4, 4, 4)
    assert float(np.asanyarray(vol.dataobj).max()) == 7.0


def test_volume_image_rejects_2d():
    with pytest.raises(ValueError, match="3D or 4D"):
        _volume_image(_image((4, 4)), 0)


def test_iter_report_volumes_3d_yields_none_index():
    img = _image((4, 4, 4))
    assert list(_iter_report_volumes(img)) == [(None, img)]


def test_iter_report_volumes_4d_yields_each_frame():
    indices = [index for index, _ in _iter_report_volumes(_image((4, 4, 4, 3)))]
    assert indices == [0, 1, 2]


def test_iter_report_volumes_rejects_2d():
    with pytest.raises(ValueError):
        list(_iter_report_volumes(_image((4, 4))))


def test_matching_report_volume_reuses_3d_image():
    img = _image((4, 4, 4))
    assert _matching_report_volume(img, 2) is img


def test_matching_report_volume_uses_first_frame_for_3d_primary():
    img = _image((4, 4, 4, 2))
    assert _matching_report_volume(img, None).shape == (4, 4, 4)


def test_matching_report_volume_clamps_index_for_shorter_series():
    img = _image((4, 4, 4, 2))
    assert _matching_report_volume(img, 5).shape == (4, 4, 4)


def test_add_plot_extends_for_sequences_and_appends_strings():
    svgs = ["a"]
    _add_plot(svgs, ["b", "c"])
    _add_plot(svgs, "d")
    assert svgs == ["a", "b", "c", "d"]


@pytest.mark.parametrize(
    "name, value, expected",
    [
        ("subject", "01", "sub-01"),
        ("subject", "sub-01", "sub-01"),
        ("session", "pre", "ses-pre"),
        ("session", "ses-pre", "ses-pre"),
        ("acquisition", "mp2rage", "acq-mp2rage"),
        ("desc", "desc-mask", "desc-mask"),
        ("desc", "mask", "desc-mask"),
        ("run", None, None),
    ],
)
def test_format_bids_entity(name, value, expected):
    assert _format_bids_entity(name, value) == expected


def test_fallback_figure_path_builds_bids_like_name():
    entities = {"subject": "01", "session": "pre", "acquisition": "mp2rage", "suffix": "T1w", "desc": "mask"}
    assert (
        _fallback_figure_path(entities)
        == Path("sub-01") / "ses-pre" / "figures" / "sub-01_ses-pre_acq-mp2rage_desc-mask_T1w.svg"
    )


def test_fallback_figure_path_without_session():
    path = _fallback_figure_path({"subject": "01", "suffix": "T1w", "desc": "registration"})
    assert path == Path("sub-01") / "figures" / "sub-01_desc-registration_T1w.svg"


def test_fallback_figure_path_requires_suffix():
    with pytest.raises(RuntimeError, match="suffix"):
        _fallback_figure_path({"subject": "01", "desc": "mask"})


def test_generate_figure_path_under_report_dir(bids_dataset, tmp_path, monkeypatch):
    monkeypatch.setattr(report, "default_path_patterns", None)
    layout = bids.BIDSLayout(bids_dataset, validate=False)
    series = layout.get(subject="01", suffix="T1w", extension="nii.gz")[0]

    path = generate_figure_path(layout, series, desc="mask", report_dir=tmp_path / "reports")

    assert path.is_relative_to(tmp_path / "reports")
    assert path.suffix == ".svg"
    assert "desc-mask" in path.name
    assert "sub-01" in path.name


def test_generate_figure_path_defaults_to_dataset_root(bids_dataset, monkeypatch):
    monkeypatch.setattr(report, "default_path_patterns", None)
    layout = bids.BIDSLayout(bids_dataset, validate=False)
    series = layout.get(subject="01", suffix="T1w", extension="nii.gz")[0]

    path = generate_figure_path(layout, series, desc="registration")

    assert path.is_relative_to(bids_dataset)


def test_generate_deface_mosaic_report_writes_svg(tmp_path):
    masked = _image((16, 16, 16), value=100.0)
    mask = _image((16, 16, 16), value=1.0)
    reference = _image((16, 16, 16), value=50.0)
    out = tmp_path / "figures" / "mosaic.svg"

    generate_deface_mosaic_report(masked, mask, out, registered_tmpl=reference)

    assert "<svg" in out.read_text()


def test_generate_deface_mosaic_report_without_reference(tmp_path):
    masked = _image((16, 16, 16, 2), value=100.0)
    mask = _image((16, 16, 16), value=1.0)
    out = tmp_path / "mosaic.svg"

    generate_deface_mosaic_report(masked, mask, out)

    assert out.exists()


def test_generate_report_delegates_to_nireports(mocker, tmp_path):
    robj = mocker.patch.object(report, "Report")
    robj.return_value.out_filename = Path("report.html")

    result = generate_report(tmp_path, subject="01", session="pre")

    robj.return_value.generate_report.assert_called_once()
    assert robj.call_args.args[0] == tmp_path
    assert robj.call_args.kwargs["subject"] == "01"
    assert result == Path("report.html").absolute()
