from __future__ import annotations

import ants
import ants.core.ants_image_io


def registration_antspy(
    ref,
    moving,
    transform="Rigid",
    initial_transform=None,
):
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
