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


def nifti_to_ants(nib_image):
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

    ants_img = ants.core.ants_image_io.from_numpy(
        data=nib_image.get_fdata(), origin=origin.tolist(), spacing=spacing.tolist(), direction=direction
    )

    return ants_img

def ants_to_nibabel(ants_img):

    aff = np.eye(4)
    aff[:3,3] = ants_img.origin
    aff[:3,:3] = ants_img.direction * ants_img.spacing

    return nb.Nifti1Image(ants_img.numpy(), affine=aff)

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
        outprefix=moving.rstrip('.nii.gz')+'_reg',
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
