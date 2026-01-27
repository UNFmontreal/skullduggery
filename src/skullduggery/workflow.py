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
from datalad.support.annexrepo import AnnexRepo

from .align import *
from .mask import generate_deface_ear_mask, synthstrip_mask
from .template import get_template
from .utils import output_debug_images


def deface_workflow(layout, args):

    logging.basicConfig(level=logging.getLevelName(args.debug_level.upper()))

    if args.datalad:
        dlad_ds = datalad.api.Dataset(args.bids_path)
        annex_repo = dlad_ds.repo

    subject_list = (
        args.participant_label if args.participant_label else bids.layout.Query.ANY
    )
    session_list = args.session_label if args.session_label else bids.layout.Query.ANY
    filters = {
        'subject': subject_list,
        'session': session_list,
        'extension': ['nii','nii.gz'],
        **args.ref_bids_filters,
    }
    deface_ref_images = layout.get(**filters)

    if not len(deface_ref_images):
        logging.info(f"no reference image found with condition {filters}")
        return

    new_files, modified_files = [], []

    script_dir = os.path.dirname(__file__)

    resolution = 1
    tpl_path, mask_path = get_template(args.atlas, args.ref_bids_filters, resolution=resolution)
    logging.info("loading template image: %s and mask: %s", tpl_path, mask_path)
    tmpl_image = nb.load(tpl_path)
    tmpl_image_mask = nb.load(mask_path)
    tmpl_defacemask = generate_deface_ear_mask(tmpl_image, resolution=resolution)

    for ref_image in deface_ref_images:
        subject = ref_image.entities["subject"]
        session = ref_image.entities["session"]

        datalad.api.get(ref_image.path)
        ref_image_nb = ref_image.get_image()

        matrix_path = ref_image.path.replace(
            "_{}{}".format(ref_image.entities["suffix"], ref_image.entities["extension"]),
            "_mod-%s_defacemaskreg.mat" % ref_image.entities["suffix"],
        )

        logging.info("mask reference image")
        brain_mask = list(synthstrip_mask(ref_image.path, ""))

        brain_mask_nb = nb.Nifti1Image(brain_mask[0][1].astype(np.uint8), ref_image_nb.affine)
        brain_mask_entities = { **ref_image.entities, "suffix": "brainmask", "mod": ref_image.entities['suffix'] }
        brain_mask_path = layout.build_path(
            brain_mask_entities,
            ["sub-{subject}[/ses-{session}]/{datatype<anat>|anat}/sub-{subject}[_ses-{session}][_task-{task}][_acq-{acquisition}][_ce-{ceagent}][_rec-{reconstruction}][_run-{run}][_mod-{modality}]_{suffix<brainmask>}{extension<.nii|.nii.gz|.json>|.nii.gz}"],
            validate=False,
        )
        logging.info("saving brain mask as %s", brain_mask_path)
        brain_mask_nb.to_filename(brain_mask_path)

        if os.path.exists(matrix_path):
            logging.info("reusing existing registration matrix")
            ref2tpl_affine = AffineMap(np.loadtxt(matrix_path))
        else:
            logging.info(f"running registration of reference serie: {ref_image.relpath}")

#            ref2tpl_affine = registration2(
#                tmpl_image, ref_image_nb, tmpl_image_mask, brain_mask_nb
#            )
            ref2tpl_affine = registration_antspy()
            np.savetxt(matrix_path, ref2tpl_affine.affine)
            new_files.append(matrix_path)

        if args.debug_images:
            output_debug_images(tmpl_image, ref_image, ref2tpl_affine)

        series_to_deface = []
        for filters in args.other_bids_filters:
            series_to_deface.extend(
                layout.get(
                    extension=["nii", "nii.gz"],
                    subject=subject,
                    session=session,
                    **filters,
                )
            )


        for serie in series_to_deface:
            if args.datalad:
                if (
                    next(annex_repo.get_metadata(serie.path))[1].get(
                        "distribution-restrictions"
                    )
                    is None
                ):
                    logging.info(
                        f"skip {serie.relpath} as there are no distribution restrictions metadata set."
                    )
                    continue
            logging.info(f"defacing {serie.relpath}")

            if args.datalad:
                datalad.api.get(serie.path)
                # unlock before making any change to avoid unwanted save
                annex_repo.unlock([serie.path for serie in series_to_deface])

            serie_nb = serie.get_image()

            # assume no repositioning of the participant to start registration
            #starting_affine = np.linalg.inv(serie_nb.affine).dot(ref_image_nb.affine)
            serie2ref_affine = registration2(
                ref_image_nb, serie_nb, brain_mask_nb, None, pipeline = ["translation", "rigid"],
            )
            print(serie2ref_affine)
            serie2tpl_affine = AffineMap(
                serie2ref_affine.affine.dot(ref2tpl_affine.affine),
            )
            warped_mask = warp_mask(tmpl_defacemask, serie_nb, serie2tpl_affine)
            if serie == ref_image:
                cropped_brain = brain_mask_nb.get_fdata()[warped_mask.get_fdata()<.5]
                nvox_cropped_brain = cropped_brain.sum()
                if nvox_cropped_brain:
                    logger.error("defacing mask is cropping %d voxels of the synthstrip brain mask", nvox_cropped_brain)

            if args.save_all_masks or serie == ref_image:
                warped_mask_path = serie.path.replace(
                    "_%s" % serie.entities["suffix"],
                    "_mod-%s_defacemask" % serie.entities["suffix"],
                )
                if os.path.exists(warped_mask_path):
                    logging.warning(
                        f"{warped_mask_path} already exists : will not overwrite, clean before rerun"
                    )
                else:
                    warped_mask.to_filename(warped_mask_path)
                    new_files.append(warped_mask_path)

            masked_serie = nb.Nifti1Image(
                np.asanyarray(serie_nb.dataobj) * np.asanyarray(warped_mask.dataobj),
                serie_nb.affine,
                serie_nb.header,
            )
            masked_serie.to_filename(serie.path)
            modified_files.append(serie.path)

    if args.datalad and len(modified_files):
        logging.info("saving files changes in datalad")
        datalad.api.save(
            modified_files + new_files,
            message="deface %d series/images and update distribution-restrictions"
            % len(modified_files),
        )
        logging.info("saving metadata changes in datalad")
        annex_repo.set_metadata(
            modified_files, remove={"distribution-restrictions": "sensitive"}
        )
