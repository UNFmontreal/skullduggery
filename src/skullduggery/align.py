"""Image registration using ANTs.

This module provides functionality for registering moving images to reference
images using ANTs (Advanced Normalization Tools) through the antspy Python wrapper.
"""

from __future__ import annotations

import ants
import ants.core.ants_image_io


def registration_antspy(
    ref,
    moving,
    transform="Rigid",
    initial_transform=None,
):
    """Register a moving image to a reference image using ANTs.

    Performs image registration using ANTs with specified transformation type.
    MI (Mutual Information) is used as the similarity metric.

    Args:
        ref: Path or image object for the reference (fixed) image.
        moving: Path or image object for the moving image to be registered.
        transform: Type of transformation. Defaults to "Rigid".
            Common options: "Rigid", "Affine", "SyN".
        initial_transform: Optional initial transformation to use.
            If None, registration starts from identity.

    Returns:
        dict: Registration result containing:
            - 'fwdtransforms': List of forward transformation files
            - 'invtransforms': List of inverse transformation files
            - Other ANTs registration outputs
    """
    ref_ants = ants.image_read(ref)
    moving_ants = ants.image_read(moving)

    reg = ants.registration(
        ref_ants,
        moving_ants,
        type_of_transform=transform,
        initial_transform=initial_transform,
        aff_metric="MI",
        grad_step=0.1,
        # verbose=True,
    )
    return reg
