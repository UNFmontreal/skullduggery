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
from deepbrain import Extractor
from dipy.align.imaffine import (AffineMap, AffineRegistration,
                                 MutualInformationMetric, VerbosityLevels,
                                 transform_centers_of_mass)
from dipy.align.transforms import (AffineTransform3D,
                                   RigidIsoScalingTransform3D,
                                   RigidScalingTransform3D, RigidTransform3D)

PYBIDS_CACHE_PATH = ".pybids_cache"
MNI_PATH = "../../global/templates/MNI152_T1_1mm.nii.gz"
MNI_MASK_PATH = "../../global/templates/MNI152_T1_1mm_brain.nii.gz"



def registration(ref, moving, ref_mask=None, moving_mask=None):
    ref_mask_data, mov_mask_data = None, None
    ref_data = ref.get_fdata()
    if ref_mask:
        ref_mask_data = (ref_mask.get_fdata() > 0.5).astype(np.int32)
    mov_data = moving.get_fdata()
    if moving_mask:
        mov_mask_data = (moving_mask.get_fdata() > 0.5).astype(np.int32)

    metric = MutualInformationMetric(nbins=32, sampling_proportion=None)
    transform = RigidTransform3D()
    affreg = AffineRegistration(
        metric=metric, level_iters=[10000, 1000, 0], factors=[6, 4, 2], sigmas=[4, 2, 0]
    )
    rigid = affreg.optimize(
        ref_data,
        mov_data,
        transform,
        None,
        ref.affine,
        moving.affine,
        starting_affine="mass",
        static_mask=ref_mask_data,
        moving_mask=mov_mask_data,
    )

    affreg = AffineRegistration(
        metric=metric, level_iters=[10000, 1000, 0], factors=[4, 2, 2], sigmas=[4, 2, 0]
    )
    transform = RigidScalingTransform3D()
    # transform = AffineTransform3D()
    return affreg.optimize(
        ref_data,
        mov_data,
        transform,
        None,
        ref.affine,
        moving.affine,
        starting_affine=rigid.affine,
        static_mask=ref_mask_data,
        moving_mask=mov_mask_data,
    )



def warp_mask(tpl_mask, target, affine):
    matrix = np.linalg.inv(tpl_mask.affine).dot(affine.affine_inv.dot(target.affine))
    warped_mask = scipy.ndimage.affine_transform(
        np.asanyarray(tpl_mask.dataobj).astype(np.int32),
        matrix,
        output_shape=target.shape,
        mode="nearest",
    )
    return nb.Nifti1Image(warped_mask, target.affine)
