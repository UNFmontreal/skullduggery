from __future__ import annotations

from importlib import resources

import nibabel as nb
import numpy as np

from skullduggery.mask import generate_deface_ear_mask


def test_int_generate_deface_ear_mask_matches_shipped_mni_mask():
    """Generate the ear mask on the MNI grid and compare with the shipped deface mask."""
    shipped_path = resources.files("skullduggery.data").joinpath("tpl-MNI152NLin6Asym_desc-deface_mask.nii.gz")
    shipped = nb.load(shipped_path)

    template_shape = (182, 218, 182)
    template_affine = shipped.affine.copy()
    template_affine[2, 3] += template_shape[2]
    template = nb.Nifti1Image(np.ones(template_shape, dtype=np.uint8), template_affine)

    generated = generate_deface_ear_mask(template, resolution=1)

    assert generated.shape == shipped.shape
    np.testing.assert_allclose(generated.affine, shipped.affine)

    generated_data = np.asanyarray(generated.dataobj).astype(bool)
    shipped_data = np.asanyarray(shipped.dataobj).astype(bool)
    dice = 2 * np.logical_and(generated_data, shipped_data).sum() / (generated_data.sum() + shipped_data.sum())
    assert dice > 0.95, f"Generated mask diverges from shipped mask (Dice={dice:.4f})"
