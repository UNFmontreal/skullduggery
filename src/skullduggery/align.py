"""Image registration using ANTs.

This module provides functionality for registering moving images to reference
images using ANTs (Advanced Normalization Tools) through the antspy Python wrapper.
"""

from __future__ import annotations

from pathlib import Path

import ants
import ants.core.ants_image_io
import nibabel as nb
import numpy as np
from nibabel.spatialimages import SpatialImage


def first_spatial_volume(image: SpatialImage) -> SpatialImage:
    """Return a 3D image, using the first volume when a 4D image is provided."""
    if len(image.shape) == 3:
        return image
    if len(image.shape) != 4:
        raise ValueError(f"Expected a 3D or 4D image, got shape {image.shape}")

    header = image.header.copy()
    data = np.asanyarray(image.dataobj)[..., 0]
    header.set_data_shape(data.shape)
    return nb.Nifti1Image(data, image.affine, header)


def _ants_dimension(image) -> int:
    dimension = getattr(image, "dimension", None)
    if dimension is not None:
        return int(dimension)
    return len(image.shape)


def _first_ants_volume(image):
    """Return a 3D ANTs image for registration."""
    dimension = _ants_dimension(image)
    if dimension == 3:
        return image
    if dimension == 4:
        return ants.slice_image(image, axis=3, idx=0, collapse_strategy=1)
    raise ValueError(f"Expected a 3D or 4D image for registration, got {dimension}D")


def registration_images(ref_ants, moving_ants):
    """Verify ANTs image dimensions and choose a valid 3D moving image when needed."""
    ref_dimension = _ants_dimension(ref_ants)
    moving_dimension = _ants_dimension(moving_ants)

    if ref_dimension == moving_dimension == 3:
        return ref_ants, moving_ants
    if ref_dimension == moving_dimension == 4:
        return _first_ants_volume(ref_ants), _first_ants_volume(moving_ants)
    if ref_dimension == 3 and moving_dimension == 4:
        return ref_ants, _first_ants_volume(moving_ants)
    if ref_dimension == 4 and moving_dimension == 3:
        return _first_ants_volume(ref_ants), moving_ants

    raise ValueError(
        "Fixed and moving image dimensions are not compatible for registration: "
        f"{ref_dimension}D fixed, {moving_dimension}D moving"
    )


def registration_antspy(
    ref: str | Path,
    moving: str | Path,
    ref_mask: str | Path | None = None,
    transform: str = "Rigid",
    initial_transform: str | None = None,
    verbose: bool = False,
) -> dict:
    """Register a moving image to a reference image using ANTs.

    Performs image registration using ANTs with specified transformation type.
    MI (Mutual Information) is used as the similarity metric.

    Args:
        ref: Path or image object for the reference (fixed) image.
        moving: Path or image object for the moving image to be registered.
        ref_mask: Optional path to reference image mask for masking registration.
        transform: Type of transformation. Defaults to "Rigid".
            Common options: "Rigid", "Affine", "TRSAA", "SyN".
        initial_transform: Optional initial transformation to use.
            If None, registration starts from identity.
        verbose: Whether to print registration progress. Defaults to False.

    Returns:
        dict: Registration result containing:
            - 'fwdtransforms': List of forward transformation files
            - 'invtransforms': List of inverse transformation files
            - Other ANTs registration outputs
    """
    ref_ants = ants.image_read(str(ref))
    moving_ants = ants.image_read(str(moving))
    ref_ants, moving_ants = registration_images(ref_ants, moving_ants)
    ref_mask_ants = ants.image_read(str(ref_mask)) if ref_mask else None

    # coud use legacy function in ants but dev advice against:
    #     use_legacy_histogram_matching : boolean
    #     if True, use the original histogram matching in ANTs. This is not recommended, but is available for backwards
    #     compatibilty with earlier versions, where it was always turned on. The default is False. A better implementation of
    #     histogram matching is available in the ants.histogram_match_image2 function.

    moving_for_registration = ants.histogram_match_image2(
        moving_ants,
        ref_ants,
        reference_mask=ref_mask_ants,
    )

    if initial_transform is None:
        initial_transform = ants.affine_initializer(
            ref_ants,
            moving_for_registration,
        )

    reg = ants.registration(
        ref_ants,
        moving_for_registration,
        mask=ref_mask_ants,
        mask_all_stages=ref_mask is not None,
        type_of_transform=transform,
        initial_transform=initial_transform,
        aff_metric="MI",
        grad_step=0.1,
        verbose=verbose,
    )
    return reg


def output_debug(
    ref: str | Path,
    moving: str | Path,
    tx: str | Path | list[str],
    out_path: str | Path,
) -> None:
    """Apply registered transformation and save warped image.

    Applies the registration transformation to the moving image and saves
    the result to the specified output path. Used for debugging and visualization.

    Args:
        ref: Path to reference (fixed) image.
        moving: Path to moving image to be warped.
        tx: Path(s) to transformation file(s). Can be a single file or list of files.
        out_path: Output path for the warped image in NIfTI format.
    """
    ref_ants = ants.image_read(str(ref))
    moving_ants = ants.image_read(str(moving))
    warped = ants.apply_transforms(ref_ants, moving_ants, tx)
    ants.image_write(warped, str(out_path))
