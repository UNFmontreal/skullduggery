from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import bids
import datalad.api
import nibabel as nb
import numpy as np
import scipy.ndimage
import scipy.ndimage.morphology
from datalad.support.annexrepo import AnnexRepo

import ants, ants.core.ants_image_io

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
        #verbose=True,
    )
    return reg

def warp_mask_antspy(
    fixed,
    moving,
    transforms
):
    ants.apply_transforms( fixed=fixed, moving=moving, transformlist=mytx['fwdtransforms'] )

def warp_mask(tpl_mask, target, affine):
    matrix = np.linalg.inv(tpl_mask.affine).dot(affine.affine_inv.dot(target.affine))
    warped_mask = scipy.ndimage.affine_transform(
        np.asanyarray(tpl_mask.dataobj).astype(np.int32),
        matrix,
        output_shape=target.shape,
        mode="nearest",
    )
    return nb.Nifti1Image(warped_mask, target.affine)
