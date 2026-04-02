from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from pathlib import Path
from shutil import copyfile

import bids
import datalad.api
import nibabel as nb
import numpy as np
import nitransforms as nt
from datalad.support.annexrepo import AnnexRepo

from .align import *
from .mask import generate_deface_ear_mask
from .template import get_template
from .utils import output_debug_images, get_age_and_unit


def deface_workflow(layout, args):

    logging.basicConfig(level=logging.getLevelName(args.debug_level.upper()))

    if args.datalad:
        dlad_ds = datalad.api.Dataset(args.bids_path)
        annex_repo = dlad_ds.repo

    subject_list = args.participant_label if args.participant_label else bids.layout.Query.ANY
    session_list = args.session_label if args.session_label else bids.layout.Query.ANY
    filters = {
        "subject": subject_list,
        "session": session_list,
        "extension": ["nii", "nii.gz"],
        **args.ref_bids_filters,
    }

    new_files, modified_files = [], []

    # generate deface mask in default template space (MNI)
    default_tpl, _ = get_template()
    default_tpl_nb = nb.load(default_tpl)
    default_tpl_defacemask = generate_deface_ear_mask(default_tpl_nb)
    # save it as file for ANTS
    _, tpl_mask_filename = tempfile.mkstemp(suffix=".nii.gz", prefix="tpl_mask")
    default_tpl_defacemask.to_filename(tpl_mask_filename)

    # lookup reference images
    deface_ref_images = layout.get(**filters)
    if not len(deface_ref_images):
        logging.error(f"no reference image found with condition {filters}")
        return

    for ref_image in deface_ref_images:
        subject = ref_image.entities["subject"]
        session = ref_image.entities.get("session")

        # get age to get the right template if cohorts
        age = get_age_and_unit(layout, subject, session)

        # get template for that reference image
        tpl_path, reg_to_default_tpl = get_template(
            template_name=args.template,
            bids_filters=args.ref_bids_filters,
            age=age)
        logging.info("loading template image: %s", tpl_path)
        tpl_to_default_tpl = [nt.load(reg_to_default_tpl)] if reg_to_default_tpl else []

        if args.datalad:
            dlad_ds.get(ref_image.relpath)

        matrix_path = ref_image.path.replace(
            "_{}{}".format(ref_image.entities["suffix"], ref_image.entities["extension"]),
            f"_from-{ref_image.entities["suffix"]}_to-{args.template}_xfm.mat"
        )



        if os.path.exists(matrix_path):
            logging.info("reusing existing registration matrix")
            ref2tpl_affine = AffineMap(np.loadtxt(matrix_path))
        else:
            # registration from ref series to template
            logging.info(f"running registration of reference serie: {ref_image.relpath}")
            reg = registration_antspy(str(tpl_path), ref_image.path)
            copyfile(reg['fwdtransforms'][0], matrix_path)
            ref_to_tpl_tx = nt.linear.load(matrix_path)
            new_files.append(matrix_path)


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
            if args.deface_sensitive:
                if next(annex_repo.get_metadata(serie.path))[1].get("distribution-restrictions") is None:
                    logging.info(f"skip {serie.relpath} as there are no distribution restrictions metadata set.")
                    continue
            logging.info(f"defacing {serie.relpath}")

            if args.datalad:
                dlad_ds.get(serie.path)
                # unlock before making any change to avoid unwanted save
                annex_repo.unlock([serie.path for serie in series_to_deface])
            serie_nb = serie.get_image()



            serie2ref_reg = registration_antspy(
                ref_image.path,
                serie.path,
                transform="Rigid",
                initial_transform='Identity'
            )
            serie2ref_tx = nt.linear.load(serie2ref_reg['fwdtransforms'][0])
            print(serie2ref_tx)

            series2tpl = nt.manip.TransformChain(tpl_to_default_tpl + [ref_to_tpl_tx, serie2ref_tx])
            tpl2series = nt.linear.Affine(np.linalg.inv(series2tpl.asaffine().matrix))
            warped_mask = nt.resampling.apply(
                tpl2series,
                default_tpl_defacemask,
                reference=serie_nb,
                order=0,
                output_dtype=np.uint8
            )


            warped_mask_path = Path(serie.path.replace(
                "_%s" % serie.entities["suffix"],
                f"_space-{serie.entities["suffix"]}_desc-deface_mask",
            ))
            if args.save_all_masks or serie == ref_image:
                if os.path.exists(warped_mask_path):
                    logging.warning(f"{warped_mask_path} already exists : will not overwrite, clean before rerun")
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
        dlad_ds.save(
            modified_files + new_files,
            message="__deface__ %d series/images and update distribution-restrictions" % len(modified_files),
        )
        logging.info("saving metadata changes in datalad")
        annex_repo.set_metadata(modified_files, remove={"distribution-restrictions": "sensitive"})
