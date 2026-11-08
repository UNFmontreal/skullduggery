from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from skullduggery import align
from skullduggery.align import (
    first_spatial_volume,
    output_debug,
    registration_antspy,
    registration_images,
    spatial_volume,
)


def _nifti4d(shape=(4, 5, 6, 3)):
    import nibabel as nb

    data = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
    return nb.Nifti1Image(data, np.eye(4))


def test_spatial_volume_3d_returns_same_image():
    import nibabel as nb

    img = nb.Nifti1Image(np.zeros((4, 5, 6), dtype=np.float32), np.eye(4))
    assert spatial_volume(img) is img


def test_spatial_volume_extracts_requested_4d_volume():
    img = _nifti4d()
    vol = spatial_volume(img, volume_index=2)
    assert vol.shape == (4, 5, 6)
    np.testing.assert_array_equal(vol.get_fdata(), img.get_fdata()[..., 2])


def test_spatial_volume_rejects_2d_image():
    import nibabel as nb

    img = nb.Nifti1Image(np.zeros((4, 5), dtype=np.float32), np.eye(4))
    with pytest.raises(ValueError, match="3D or 4D"):
        spatial_volume(img)


@pytest.mark.parametrize("index", [-1, 3])
def test_spatial_volume_index_out_of_range(index):
    with pytest.raises(IndexError):
        spatial_volume(_nifti4d(), volume_index=index)


def test_first_spatial_volume_returns_first_frame():
    img = _nifti4d()
    np.testing.assert_array_equal(first_spatial_volume(img).get_fdata(), img.get_fdata()[..., 0])


def test_ants_dimension_prefers_dimension_attribute():
    assert align._ants_dimension(SimpleNamespace(dimension=4, shape=(1, 1, 1))) == 4


def test_ants_dimension_falls_back_to_shape():
    assert align._ants_dimension(SimpleNamespace(shape=(2, 2, 2))) == 3


def test_ants_volume_3d_passthrough():
    image = SimpleNamespace(dimension=3)
    assert align._ants_volume(image) is image


def test_ants_volume_4d_slices_requested_index(mocker):
    image = SimpleNamespace(dimension=4)
    slice_mock = mocker.patch.object(align.ants, "slice_image", return_value="sliced")
    assert align._ants_volume(image, volume_index=2) == "sliced"
    slice_mock.assert_called_once_with(image, axis=3, idx=2, collapse_strategy=1)


def test_ants_volume_rejects_other_dimensions():
    with pytest.raises(ValueError, match="3D or 4D"):
        align._ants_volume(SimpleNamespace(dimension=2))


def test_registration_images_both_3d():
    ref, moving = SimpleNamespace(dimension=3), SimpleNamespace(dimension=3)
    assert registration_images(ref, moving) == (ref, moving)


def test_registration_images_both_4d_selects_volumes(mocker):
    mocker.patch.object(align, "_ants_volume", side_effect=lambda img, idx: (img.name, idx))
    ref = SimpleNamespace(dimension=4, name="ref")
    moving = SimpleNamespace(dimension=4, name="moving")
    assert registration_images(ref, moving, ref_volume_index=1, moving_volume_index=2) == (
        ("ref", 1),
        ("moving", 2),
    )


def test_registration_images_3d_fixed_4d_moving(mocker):
    mocker.patch.object(align, "_ants_volume", side_effect=lambda img, idx: ("vol", idx))
    ref = SimpleNamespace(dimension=3)
    moving = SimpleNamespace(dimension=4)
    assert registration_images(ref, moving, moving_volume_index=4) == (ref, ("vol", 4))


def test_registration_images_4d_fixed_3d_moving(mocker):
    mocker.patch.object(align, "_ants_volume", side_effect=lambda img, idx: ("vol", idx))
    ref = SimpleNamespace(dimension=4)
    moving = SimpleNamespace(dimension=3)
    assert registration_images(ref, moving, ref_volume_index=5) == (("vol", 5), moving)


def test_registration_images_incompatible_dimensions():
    with pytest.raises(ValueError, match="not compatible"):
        registration_images(SimpleNamespace(dimension=2), SimpleNamespace(dimension=3))


def test_registration_antspy_runs_with_default_initialisation(mocker, tmp_path):
    ref_img = SimpleNamespace(dimension=3, name="ref")
    moving_img = SimpleNamespace(dimension=3, name="moving")
    mocker.patch.object(align.ants, "image_read", side_effect=[ref_img, moving_img])
    hist = mocker.patch.object(align.ants, "histogram_match_image2", return_value="matched")
    init = mocker.patch.object(align.ants, "affine_initializer", return_value="init_tx")
    reg = mocker.patch.object(align.ants, "registration", return_value={"fwdtransforms": ["f.mat"]})

    result = registration_antspy("ref.nii", "moving.nii", transform="Rigid", verbose=True)

    assert result == {"fwdtransforms": ["f.mat"]}
    hist.assert_called_once()
    init.assert_called_once_with(ref_img, "matched")
    reg.assert_called_once()
    kwargs = reg.call_args.kwargs
    assert reg.call_args.args == (ref_img, "matched")
    assert kwargs["type_of_transform"] == "Rigid"
    assert kwargs["initial_transform"] == "init_tx"
    assert kwargs["mask"] is None
    assert kwargs["mask_all_stages"] is False
    assert kwargs["verbose"] is True


def test_registration_antspy_uses_mask_and_given_initial_transform(mocker):
    ref_img = SimpleNamespace(dimension=3)
    moving_img = SimpleNamespace(dimension=3)
    mask_img = object()
    mocker.patch.object(align.ants, "image_read", side_effect=[ref_img, moving_img, mask_img])
    mocker.patch.object(align.ants, "histogram_match_image2", return_value="matched")
    init = mocker.patch.object(align.ants, "affine_initializer")
    reg = mocker.patch.object(align.ants, "registration", return_value={})

    registration_antspy("ref.nii", "moving.nii", ref_mask="mask.nii", initial_transform="given")

    init.assert_not_called()
    kwargs = reg.call_args.kwargs
    assert kwargs["initial_transform"] == "given"
    assert kwargs["mask"] is mask_img
    assert kwargs["mask_all_stages"] is True


def test_output_debug_applies_transform_and_writes(mocker, tmp_path):
    ref_img, moving_img = object(), object()
    mocker.patch.object(align.ants, "image_read", side_effect=[ref_img, moving_img])
    apply = mocker.patch.object(align.ants, "apply_transforms", return_value="warped")
    write = mocker.patch.object(align.ants, "image_write")

    out = tmp_path / "warped.nii.gz"
    output_debug("ref.nii", "moving.nii", ["tx.mat"], out)

    apply.assert_called_once_with(ref_img, moving_img, ["tx.mat"])
    write.assert_called_once_with("warped", str(out))
