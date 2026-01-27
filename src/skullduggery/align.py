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
from dipy.align.imaffine import (AffineMap, AffineRegistration,
                                 MutualInformationMetric, VerbosityLevels,
                                 transform_centers_of_mass)
from dipy.align.transforms import (AffineTransform3D,
                                   RigidIsoScalingTransform3D,
                                   RigidScalingTransform3D, RigidTransform3D)
from dipy.align import affine_registration

import ants

def nifti_to_ants( nib_image ):
    """
    Converts a given Nifti image into an ANTsPy image

    Parameters
    ----------
        img: NiftiImage

    Returns
    -------
        ants_image: ANTsImage
    """
    ndim = nib_image.ndim

    if ndim < 3:
        print("Dimensionality is less than 3.")
        return None

    q_form = nib_image.get_qform()
    spacing = nib_image.header["pixdim"][1 : ndim + 1]

    origin = np.zeros((ndim))
    origin[:3] = q_form[:3, 3]

    direction = np.diag(np.ones(ndim))
    direction[:3, :3] = q_form[:3, :3] / spacing[:3]

    ants_img = ants.from_numpy(
        data = nib_image.get_fdata(),
        origin = origin.tolist(),
        spacing = spacing.tolist(),
        direction = direction )

    return ants_img

def registration_antspy(
    ref, moving,
    transform = "Rigid",
    )
    ref_ants = utils.nifti_to_ants(ref)
    moving_ants = utils.nifti_to_ants(moving)

    reg = ants.registration(
        ref_ants,
        moving_ants,
        type_of_transform=transform,
        aff_metric="MI",
        grad_step=.1,
        verbose=True,
    )

def registration2(
    ref, moving,
    ref_mask=None, moving_mask=None,
    pipeline = ['center_of_mass', "translation", "rigid", "affine"],
    starting_affine=None,
):
    ref_mask_data, moving_mask_data = None, None
    if ref_mask:
        ref_mask_data = (ref_mask.get_fdata() > 0.5).astype(np.int32)
    if moving_mask:
        moving_mask_data = (moving_mask.get_fdata() > 0.5).astype(np.int32)
    transformed, affine = affine_registration(
        moving, ref,
        pipeline = pipeline,
        starting_affine = starting_affine,
        #metric = "MI",
        sigmas = [4,2,1,0],
        level_iters = [1000, 100, 10, 0],
        factors = [5, 3, 2, 1],
        moving_mask = moving_mask_data,
        static_mask = ref_mask_data,
    )
    return AffineMap(affine)


def registration(
    ref, moving,
    ref_mask=None, moving_mask=None,
    rigid=False,
    starting_affine="mass",
):
    ref_mask_data, mov_mask_data = None, None
    ref_data = ref.get_fdata()
    if ref_mask:
        ref_mask_data = (ref_mask.get_fdata() > 0.5).astype(np.int32)
    mov_data = moving.get_fdata()
    if moving_mask:
        mov_mask_data = (moving_mask.get_fdata() > 0.5).astype(np.int32)

    metric = MutualInformationMetric(nbins=32, sampling_proportion=None)
    transform = RigidIsoScalingTransform3D()
    affreg = AffineRegistration(
        metric=metric, level_iters=[1000, 100, 10], factors=[6, 5, 4], sigmas=[6, 4, 2]
    )
    rigid_reg = affreg.optimize(
        ref_data,
        mov_data,
        transform,
        None,
        static_grid2world=ref.affine,
        moving_grid2world=moving.affine,
        starting_affine=starting_affine,
        static_mask=ref_mask_data,
        moving_mask=mov_mask_data,
    )

    if rigid:
        return rigid_reg
    affreg = AffineRegistration(
        metric=metric, level_iters=[10000, 1000, 10], factors=[5, 3, 2], sigmas=[4, 3, 2]
    )
    transform = RigidScalingTransform3D()
    # transform = AffineTransform3D()
    return affreg.optimize(
        ref_data,
        mov_data,
        transform,
        None,
        static_grid2world=ref.affine,
        moving_grid2world=moving.affine,
        starting_affine=rigid_reg.affine,
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
