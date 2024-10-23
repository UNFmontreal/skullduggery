import os
import json
import bids
import argparse
from pathlib import Path
import logging
import nibabel as nb
import numpy as np
import scipy.ndimage
import datalad.api
from datalad.support.annexrepo import AnnexRepo
from .external.synthstrip import synthstrip_wf
from .mask import generate_deface_ear_mask
from .align import registration
from .utils import output_debug_images

def workflow(layout, args):

    logging.basicConfig(level=logging.getLevelName(args.debug_level.upper()))

    pybids_cache_path = os.path.join(args.bids_path, PYBIDS_CACHE_PATH)

    if args.datalad:
        annex_repo = AnnexRepo(args.bids_path)

    subject_list = (
        args.participant_label if args.participant_label else bids.layout.Query.ANY
    )
    session_list = args.session_label if args.session_label else bids.layout.Query.ANY
    filters = dict(
        subject=subject_list,
        session=session_list,
        **args.ref_bids_filters,
        extension=['nii','nii.gz'])
    deface_ref_images = layout.get(**filters)

    if not len(deface_ref_images):
        logging.info(f"no reference image found with condition {filters}")
        return

    new_files, modified_files = [], []

    script_dir = os.path.dirname(__file__)

    mni_path = os.path.abspath(os.path.join(script_dir, MNI_PATH))
    mni_mask_path = os.path.abspath(os.path.join(script_dir, MNI_MASK_PATH))
    # if the MNI template image is not available locally
    if not os.path.exists(os.path.realpath(mni_path)):
        datalad.api.get(mni_path, dataset=datalad.api.Dataset(script_dir + "/../../"))
    tmpl_image = nb.load(mni_path)
    tmpl_image_mask = nb.load(mni_mask_path)
    tmpl_defacemask = generate_deface_ear_mask(tmpl_image)
    brain_xtractor = Extractor()

    for ref_image in deface_ref_images:
        subject = ref_image.entities["subject"]
        session = ref_image.entities["session"]

        datalad.api.get(ref_image.path)
        ref_image_nb = ref_image.get_image()

        matrix_path = ref_image.path.replace(
            "_%s%s" % (ref_image.entities["suffix"], ref_image.entities["extension"]),
            "_mod-%s_defacemaskreg.mat" % ref_image.entities["suffix"],
        )

        if os.path.exists(matrix_path):
            logging.info("reusing existing registration matrix")
            ref2tpl_affine = AffineMap(np.loadtxt(matrix_path))
        else:
            logging.info(f"running registration of reference serie: {ref_image.path}")
            """
            brain_mask = (brain_xtractor.run(ref_image_nb.get_fdata()) > 0.99).astype(
                np.uint8
            )
            brain_mask[:] = scipy.ndimage.binary_dilation(
                brain_mask, iterations=4
            )
            brain_mask_nb = nb.Nifti1Image(brain_mask, ref_image_nb.affine)
            """
            brain_mask_nb = None
            ref2tpl_affine = registration(
                tmpl_image, ref_image_nb, tmpl_image_mask, brain_mask_nb
            )
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
                        f"skip {serie.path} as there are no distribution restrictions metadata set."
                    )
                    continue
            logging.info(f"defacing {serie.path}")

            datalad.api.get(serie.path)
            # unlock before making any change to avoid unwanted save
            if args.datalad:
                annex_repo.unlock([serie.path for serie in series_to_deface])

            serie_nb = serie.get_image()
            warped_mask = warp_mask(tmpl_defacemask, serie_nb, ref2tpl_affine)
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
        logging.info("saving files and metadata changes in datalad")
        annex_repo.set_metadata(
            modified_files, remove={"distribution-restrictions": "sensitive"}
        )
        datalad.api.save(
            modified_files + new_files,
            message="deface %d series/images and update distribution-restrictions"
            % len(modified_files),
        )
