"""Image registration using ANTs.

This module provides functionality for registering moving images to reference
images using ANTs (Advanced Normalization Tools) through the antspy Python wrapper.
"""

from __future__ import annotations

from pathlib import Path

import ants
import ants.core.ants_image_io


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
    ref_mask_ants = ants.image_read(str(ref_mask)) if ref_mask else None

    if initial_transform is None:
        initial_transform = ants.affine_initializer(
            ref_ants,
            moving_ants,
        )

    reg = ants.registration(
        ref_ants,
        moving_ants,
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
    the result to the specified output path.

    Args:
        ref: Path to reference (fixed) image.
        moving: Path to moving image to be warped.
        tx: Path(s) to transformation file(s). Can be a single file or list.
        out_path: Output path for the warped image.
    """
    ref_ants = ants.image_read(str(ref))
    moving_ants = ants.image_read(str(moving))
    warped = ants.apply_transforms(ref_ants, moving_ants, tx)
    ants.image_write(warped, str(out_path))
