import nibabel as nb
import numpy as np

from skullduggery.mask import generate_deface_ear_mask


def test_generate_deface_ear_mask():
    # Create a dummy image with shape (256, 256, 256)
    shape = (256, 256, 256)
    affine = np.eye(4)
    data = np.ones(shape, dtype=np.uint8)

    dummy_img = nb.Nifti1Image(data, affine)

    mask_img = generate_deface_ear_mask(dummy_img, resolution=1)

    # Check returned shape
    # Based on the function: np.asarray(mni.shape) * (1, 1, 2)
    expected_shape = (256, 256, 512)
    assert mask_img.shape == expected_shape

    # Check modified affine (Z translation translated by -256)
    expected_affine = np.eye(4)
    expected_affine[2, 3] = -256
    np.testing.assert_array_equal(mask_img.affine, expected_affine)

    mask_data = np.asarray(mask_img.dataobj)

    # Assert mask is zeroed out at specific edge bounds that are always 0
    assert mask_data[0, 128, 128] == 0  # X=0 is 0
    assert mask_data[-1, 128, 128] == 0 # X=-1 is 0
    assert mask_data[128, 0, 128] == 0  # Y=0 is 0
    assert mask_data[128, -1, 128] == 0 # Y=-1 is 0
    assert mask_data[128, 128, -1] == 0 # Z=-1 is 0
