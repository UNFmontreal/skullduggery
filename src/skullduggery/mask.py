"""Defacing mask generation from template images.

This module generates defacing masks that remove identifiable facial features
while preserving brain tissue, using template-based hard-coded anatomical markers.
"""

from __future__ import annotations

import logging

import nibabel as nb
from nibabel.processing import resample_from_to
from nibabel.spatialimages import SpatialImage
import nitransforms as nt
import numpy as np

from .align import registration_antspy, spatial_volume

logger = logging.getLogger(__name__)


def _mask_for_image(mask: SpatialImage, image: SpatialImage) -> SpatialImage:
    """Return mask data sampled onto the target image grid.

    Args:
        mask: 3D or 4D binary mask image.
        image: Target image whose spatial grid should receive the mask.

    Returns:
        ``mask`` unchanged when it already matches ``image``. Otherwise,
        a nearest-neighbor 3D mask sampled onto the target spatial grid.
    """
    if (
        len(mask.shape) == 4
        and len(image.shape) == 4
        and mask.shape == image.shape
        and np.allclose(mask.affine, image.affine)
    ):
        return mask
    image_shape = image.shape[:3] if len(image.shape) == 4 else image.shape
    if mask.shape == image_shape and np.allclose(mask.affine, image.affine):
        return mask
    return resample_from_to(mask, (image_shape, image.affine), order=0)


def _volume_count(image: SpatialImage) -> int:
    """Return the number of spatial volumes in a 3D or 4D image.

    Args:
        image: Nibabel image to inspect.

    Returns:
        ``1`` for a 3D image, or the fourth-dimension length for a 4D image.

    Raises:
        ValueError: If ``image`` is not 3D or 4D.
    """
    if len(image.shape) == 3:
        return 1
    if len(image.shape) == 4:
        return image.shape[3]
    raise ValueError(f"Expected a 3D or 4D image, got shape {image.shape}")


def _stack_like_reference(
    volumes: list[SpatialImage],
    reference: SpatialImage,
    dtype: np.dtype | type | None = None,
) -> SpatialImage:
    """Stack 3D volumes into a 4D image when the reference is 4D.

    Args:
        volumes: Per-volume 3D images already sampled on the reference grid.
        reference: Image whose shape, affine, and header should define the
            returned image. A 3D reference returns the first input volume.
        dtype: Optional dtype to use for the stacked data and output header.

    Returns:
        A 3D image when ``reference`` is 3D, otherwise a 4D image with one
        input volume per fourth-dimension frame.
    """
    if len(reference.shape) == 3:
        return volumes[0]

    data = np.stack([np.asanyarray(volume.dataobj) for volume in volumes], axis=-1)
    if dtype is not None:
        data = data.astype(dtype)
    header = reference.header.copy()
    header.set_data_shape(data.shape)
    if dtype is not None:
        header.set_data_dtype(dtype)
    return nb.Nifti1Image(data, reference.affine, header)


def build_series_deface_mask(
    ref_image,
    ref_image_nb: SpatialImage,
    serie,
    serie_nb: SpatialImage,
    ref_to_tpl_tx: nt.base.TransformBase,
    ref_deface_mask: SpatialImage,
    tpl_nb: SpatialImage,
    verbose: bool = False,
) -> tuple[SpatialImage, SpatialImage, str]:
    """Build native-space deface masks and report references for one series.

    Each 4D volume is registered independently to the participant reference
    image. The participant reference-space deface mask is then resampled onto
    that volume's native grid.

    Args:
        ref_image: PyBIDS file for the participant reference image.
        ref_image_nb: Loaded participant reference image.
        serie: PyBIDS file for the target series being defaced.
        serie_nb: Loaded target series image. May be 3D or 4D.
        ref_to_tpl_tx: Linear transform between the participant reference and
            selected template, used for reference report rendering.
        ref_deface_mask: Deface mask already sampled in participant reference
            image space.
        tpl_nb: Loaded selected template image for QA report rendering.
        verbose: Whether ANTs registration should emit verbose output.

    Returns:
        Tuple ``(serie_mask, registered_ref, desc)`` where ``serie_mask`` is
        sampled on the target series grid, ``registered_ref`` is a 3D/4D QA
        reference image sampled on the same grid, and ``desc`` is the figure
        description label.
    """
    volume_masks = []
    registered_refs = []
    volume_total = _volume_count(serie_nb)

    for volume_index in range(volume_total):
        if volume_total > 1:
            logger.info(
                "registering volume %d/%d of %s to reference",
                volume_index + 1,
                volume_total,
                serie.relpath,
            )

        volume_reference = spatial_volume(serie_nb, volume_index)

        if serie.path == ref_image.path:
            series_to_ref_tx = nt.linear.Affine()
        else:
            serie2ref_reg = registration_antspy(
                ref_image.path,
                serie.path,
                transform="Rigid",
                initial_transform="Identity",
                verbose=verbose,
                moving_volume_index=volume_index,
            )
            serie2ref_tx = nt.linear.load(serie2ref_reg["fwdtransforms"][0])
            series_to_ref_tx = nt.linear.Affine(np.linalg.inv(serie2ref_tx.matrix))

        volume_mask = nt.resampling.apply(
            series_to_ref_tx,
            ref_deface_mask,
            reference=volume_reference,
            order=0,
            output_dtype=np.uint8,
        )
        volume_masks.append(volume_mask)

        if serie == ref_image:
            logger.debug("generating registered template image")
            tpl_to_ref_tx = nt.linear.Affine(np.linalg.inv(ref_to_tpl_tx.matrix))
            registered_ref = nt.resampling.apply(tpl_to_ref_tx, tpl_nb, reference=volume_reference)
            groupref_desc = "registration"
        else:
            logger.debug("generating registered reference image")
            registered_ref = nt.resampling.apply(
                series_to_ref_tx,
                spatial_volume(ref_image_nb),
                reference=volume_reference,
            )
            registered_ref = mask_nifti(registered_ref, volume_mask)
            groupref_desc = "mask"
        registered_refs.append(registered_ref)

    serie_mask = _stack_like_reference(volume_masks, serie_nb, dtype=np.uint8)
    registered_ref = _stack_like_reference(registered_refs, serie_nb)
    return serie_mask, registered_ref, groupref_desc


def generate_deface_ear_mask(
    mni: nb.spatialimages.SpatialImage,
    resolution: int = 1,
) -> nb.Nifti1Image:
    """Generate a defacing mask to remove face and ears from neuroimages.

    Creates a defacing mask on the fly from a template image using hard-coded
    anatomical markers. The mask is extended beyond the template to include
    the full face and accommodate images with larger fields of view (e.g.,
    cervical spine acquisitions).

    Args:
        mni: nibabel image object of the template (typically MNI space).
        resolution: Resolution scaling factor. Defaults to 1 (full resolution).
            Use >1 for lower resolution processing.

    Returns:
        nibabel.Nifti1Image: Binary defacing mask with:
            - 0 where tissue should be removed (face, ears, edges)
            - 1 where tissue should be preserved (brain region)
    """

    deface_ear_mask = np.ones(np.asarray(mni.shape) * (1, 1, 2), dtype=np.uint8)
    affine_ext = mni.affine.copy()
    affine_ext[2, -1] -= mni.shape[-1]

    above_eye_marker = np.asarray([218, 236]) // resolution
    jaw_marker = np.asarray([140, 180]) // resolution
    ear_marker = np.asarray([21, 160]) // resolution
    ear_marker2 = np.asarray([7, 260]) // resolution
    ear_y_marker = np.asarray([70, 140]) // resolution

    # remove face
    deface_ear_mask[:, jaw_marker[0] :, : jaw_marker[1]] = 0
    z_span = above_eye_marker[1] - jaw_marker[1]
    for z in range(jaw_marker[1], above_eye_marker[1] + 1):
        t = (z - jaw_marker[1]) / z_span
        y = round(jaw_marker[0] + (above_eye_marker[0] - jaw_marker[0]) * (1 - (1 - t) * (1 - t)))
        # curve vending up
        # y = round(jaw_marker[0] + (above_eye_marker[0] - jaw_marker[0]) * (t * t))
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
    return nb.Nifti1Image(deface_ear_mask, affine_ext)


def mask_nifti(input, mask):
    """Apply a 3D or 4D mask to a NIfTI-like image.

    Args:
        input: Image to deface. May be 3D or 4D.
        mask: Binary mask sampled on the input image grid. A 3D mask is
            broadcast across 4D input volumes; a 4D mask is applied
            volume-by-volume.

    Returns:
        NIfTI image with masked data and the input affine/header.
    """
    input_data = np.asanyarray(input.dataobj)
    mask_data = np.asanyarray(mask.dataobj)
    while mask_data.ndim < input_data.ndim:
        mask_data = mask_data[..., np.newaxis]
    return nb.Nifti1Image(
        input_data * mask_data,
        input.affine,
        input.header,
    )
