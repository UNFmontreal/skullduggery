"""Defacing mask generation from template images.

This module generates defacing masks that remove identifiable facial features
while preserving brain tissue, using template-based hard-coded anatomical markers.
"""

from __future__ import annotations

import nibabel as nb
import numpy as np
from scipy import ndimage


def generate_deface_ear_mask(
    mni,
    resolution=1,
    jaw_offset=0,
    ear_offset=0,
    above_eye_offset=0,
    dilate=0,
):
    """Generate a defacing mask to remove face and ears from neuroimages.

    Creates a defacing mask on the fly from a template image using hard-coded
    anatomical markers. The mask is extended beyond the template to include
    the full face and accommodate images with larger fields of view (e.g.,
    cervical spine acquisitions).

    Args:
        mni: nibabel image object of the template (typically MNI space).
        resolution: Resolution scaling factor. Defaults to 1 (full resolution).
            Use >1 for lower resolution processing.
        jaw_offset: Shift jaw marker in voxels (positive = anterior/superior).
            Defaults to 0.
        ear_offset: Shift ear markers in voxels (positive = anterior/superior).
            Defaults to 0.
        above_eye_offset: Shift above-eye marker in voxels (positive = superior).
            Defaults to 0.
        dilate: Expand/contract mask by N voxels (positive = expand, negative = contract).
            Uses binary dilation/erosion. Defaults to 0 (no change).

    Returns:
        nibabel.Nifti1Image: Binary defacing mask with:
            - 0 where tissue should be removed (face, ears, edges)
            - 1 where tissue should be preserved (brain region)
    """

    deface_ear_mask = np.ones(np.asarray(mni.shape) * (1, 1, 2), dtype=np.uint8)
    affine_ext = mni.affine.copy()
    affine_ext[2, -1] -= mni.shape[-1]

    above_eye_marker = np.asarray([218, 240]) // resolution + np.array([0, above_eye_offset])
    jaw_marker = np.asarray([130, 182]) // resolution + np.array([jaw_offset, jaw_offset])
    ear_marker = np.asarray([26, 160]) // resolution + np.array([ear_offset, ear_offset])
    ear_marker2 = np.asarray([12, 260]) // resolution + np.array([ear_offset, ear_offset])
    ear_y_marker = np.asarray([70, 140]) // resolution

    # remove face
    deface_ear_mask[:, jaw_marker[0] :, : jaw_marker[1]] = 0
    y_coords = np.round(np.linspace(jaw_marker[0], above_eye_marker[0], above_eye_marker[1] - jaw_marker[1])).astype(
        np.int32
    )
    for z, y in zip(range(jaw_marker[1], above_eye_marker[1]), y_coords):
        deface_ear_mask[:, y:, z] = 0

    # remove ears
    deface_ear_mask[: ear_marker[0], :, : ear_marker[1]] = 0
    deface_ear_mask[-ear_marker[0] :, :, : ear_marker[1]] = 0
    x_coords = np.round(np.linspace(ear_marker[0], ear_marker2[0], ear_marker2[1] - ear_marker[1])).astype(np.int32)
    for z, x in zip(range(ear_marker[1], ear_marker2[1]), x_coords):
        deface_ear_mask[:x, ear_y_marker[0] : ear_y_marker[1], z] = 0
        deface_ear_mask[-x:, ear_y_marker[0] : ear_y_marker[1], z] = 0

    # remove data on the image size where the body doesn't extend
    deface_ear_mask[-1] = 0
    deface_ear_mask[0] = 0
    deface_ear_mask[:, 0, :] = 0
    deface_ear_mask[:, -1, :] = 0
    deface_ear_mask[:, :, -1] = 0
    deface_ear_mask[:, :, : mni.shape[2]] = deface_ear_mask[:, :, mni.shape[2], np.newaxis]
    
    # Apply dilation/erosion if requested
    if dilate > 0:
        # Expand the mask (make defaced region larger)
        deface_ear_mask = ndimage.binary_dilation(deface_ear_mask, iterations=dilate).astype(np.uint8)
    elif dilate < 0:
        # Contract the mask (make defaced region smaller)
        deface_ear_mask = ndimage.binary_erosion(deface_ear_mask, iterations=-dilate).astype(np.uint8)
    
    return nb.Nifti1Image(deface_ear_mask, affine_ext)
