from __future__ import annotations

import numpy as np

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
