from __future__ import annotations

from types import SimpleNamespace

import nitransforms as nt
import numpy as np
import pytest

from skullduggery.mask import generate_deface_ear_mask


def test_generate_deface_ear_mask(sample_template_image):
    """Test defacing mask generation from template image."""
    dummy_img = sample_template_image

    mask_img = generate_deface_ear_mask(dummy_img, resolution=1)

    # Check returned shape - should be extended in Z dimension
    # Based on the function: np.asarray(mni.shape) * (1, 1, 2)
    expected_shape = (256, 256, 512)
    assert mask_img.shape == expected_shape, f"Expected {expected_shape}, got {mask_img.shape}"

    # Check modified affine (Z translation adjusted by -256)
    expected_affine = np.eye(4)
    expected_affine[2, 3] = -256
    np.testing.assert_array_equal(mask_img.affine, expected_affine, err_msg="Affine transformation mismatch")

    mask_data = np.asarray(mask_img.dataobj)

    # Assert mask is zeroed out at specific edge bounds that are always 0
    assert mask_data[0, 128, 128] == 0, "Mask should be 0 at X=0"
    assert mask_data[-1, 128, 128] == 0, "Mask should be 0 at X=-1"
    assert mask_data[128, 0, 128] == 0, "Mask should be 0 at Y=0"
    assert mask_data[128, -1, 128] == 0, "Mask should be 0 at Y=-1"
    assert mask_data[128, 128, -1] == 0, "Mask should be 0 at Z=-1"

    # Check that the mask is binary (only 0s and 1s)
    unique_values = np.unique(mask_data)
    assert np.all(np.isin(unique_values, [0, 1])), "Mask should only contain 0s and 1s"


def _volume(shape, value=1, dtype=np.uint8):
    import nibabel as nb

    return nb.Nifti1Image(np.full(shape, value, dtype=dtype), np.eye(4))


def test_volume_count_3d_and_4d():
    from skullduggery.mask import _volume_count

    assert _volume_count(_volume((4, 4, 4))) == 1
    assert _volume_count(_volume((4, 4, 4, 3))) == 3


def test_volume_count_rejects_2d():
    from skullduggery.mask import _volume_count

    with pytest.raises(ValueError, match="3D or 4D"):
        _volume_count(_volume((4, 4)))


def test_mask_for_image_returns_matching_mask_unchanged():
    from skullduggery.mask import _mask_for_image

    mask = _volume((4, 4, 4))
    assert _mask_for_image(mask, _volume((4, 4, 4))) is mask


def test_mask_for_image_resamples_onto_other_grid():
    import nibabel as nb

    from skullduggery.mask import _mask_for_image

    mask = _volume((4, 4, 4))
    target = nb.Nifti1Image(np.zeros((6, 6, 6), dtype=np.float32), np.eye(4))
    resampled = _mask_for_image(mask, target)
    assert resampled.shape == (6, 6, 6)


def test_mask_nifti_broadcasts_3d_mask_over_4d_input():
    from skullduggery.mask import mask_nifti

    data = np.ones((3, 3, 3, 2), dtype=np.float32)
    mask_data = np.zeros((3, 3, 3), dtype=np.uint8)
    mask_data[1] = 1
    masked = mask_nifti(_volume((3, 3, 3, 2), value=1, dtype=np.float32), _volume_from(mask_data))

    expected = data * mask_data[..., np.newaxis]
    np.testing.assert_array_equal(np.asanyarray(masked.dataobj), expected)


def _volume_from(data):
    import nibabel as nb

    return nb.Nifti1Image(data, np.eye(4))


def test_mask_nifti_applies_4d_mask_volume_by_volume():
    from skullduggery.mask import mask_nifti

    input_data = np.full((2, 2, 2, 2), 5, dtype=np.float32)
    mask_data = np.zeros((2, 2, 2, 2), dtype=np.uint8)
    mask_data[..., 1] = 1
    masked = mask_nifti(_volume_from(input_data), _volume_from(mask_data))
    np.testing.assert_array_equal(np.asanyarray(masked.dataobj), input_data * mask_data)


def test_stack_like_reference_3d_returns_first_volume():
    from skullduggery.mask import _stack_like_reference

    first = _volume((2, 2, 2))
    assert _stack_like_reference([first, _volume((2, 2, 2))], _volume((2, 2, 2))) is first


def test_stack_like_reference_4d_stacks_volumes_with_dtype():
    from skullduggery.mask import _stack_like_reference

    volumes = [_volume((2, 2, 2), value=v, dtype=np.float32) for v in (1, 2, 3)]
    stacked = _stack_like_reference(volumes, _volume((2, 2, 2, 3)), dtype=np.uint8)
    assert stacked.shape == (2, 2, 2, 3)
    assert stacked.get_data_dtype() == np.uint8
    np.testing.assert_array_equal(np.asanyarray(stacked.dataobj)[0, 0, 0], [1, 2, 3])


def test_build_series_deface_mask_reference_series(mocker):
    import nibabel as nb

    from skullduggery.mask import build_series_deface_mask

    ref_path = "ref.nii.gz"
    ref_image = SimpleNamespace(path=ref_path, relpath=ref_path)
    serie = ref_image
    serie_nb = _volume((4, 4, 4), value=1, dtype=np.float32)
    ref_deface_mask = _volume((4, 4, 4))
    tpl_nb = _volume((4, 4, 4), value=2, dtype=np.float32)
    ref_to_tpl_tx = nt.linear.Affine(np.eye(4))

    serie_mask, registered_ref, desc = build_series_deface_mask(
        ref_image, serie_nb, serie, serie_nb, ref_to_tpl_tx, ref_deface_mask, tpl_nb
    )

    assert desc == "registration"
    assert serie_mask.shape == (4, 4, 4)
    assert registered_ref.shape == (4, 4, 4)
    assert isinstance(serie_mask, nb.Nifti1Image)


def test_build_series_deface_mask_other_series_uses_registration(mocker, tmp_path):
    from skullduggery.mask import build_series_deface_mask

    tx_file = tmp_path / "tx.mat"
    nt.linear.Affine(np.eye(4)).to_filename(tx_file, fmt="itk")
    reg = mocker.patch("skullduggery.mask.registration_antspy", return_value={"fwdtransforms": [str(tx_file)]})

    ref_image = SimpleNamespace(path="ref.nii.gz", relpath="ref.nii.gz")
    serie = SimpleNamespace(path="other.nii.gz", relpath="other.nii.gz")
    ref_nb = _volume((4, 4, 4), value=1, dtype=np.float32)
    serie_nb = _volume((4, 4, 4, 2), value=1, dtype=np.float32)
    tpl_nb = _volume((4, 4, 4), value=2, dtype=np.float32)
    ref_to_tpl_tx = nt.linear.Affine(np.eye(4))

    serie_mask, registered_ref, desc = build_series_deface_mask(
        ref_image,
        ref_nb,
        serie,
        serie_nb,
        ref_to_tpl_tx,
        _volume((4, 4, 4)),
        tpl_nb,
    )

    assert desc == "mask"
    assert reg.call_count == 2
    assert serie_mask.shape == (4, 4, 4, 2)
    assert registered_ref.shape == (4, 4, 4, 2)
