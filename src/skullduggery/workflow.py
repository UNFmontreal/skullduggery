from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from shutil import copyfile

import bids
import datalad.api
import nibabel as nb
import nitransforms as nt
import numpy as np

from .align import registration_antspy
from .mask import generate_deface_ear_mask
from .report import generate_deface_mosaic_report, generate_figure_path, generate_report
from .template import get_template
from .utils import get_age_and_unit, group_series


def deface_workflow(layout, args):

    logging.basicConfig(level=logging.getLevelName(args.debug_level.upper()))

    report_dir = layout._root / (args.report_dir or Path(".skullduggery"))

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
        if age is None and args.default_age is not None:
            logging.warning(
                "using fallback age %s:%s for sub-%s",
                args.default_age[0],
                args.default_age[1],
                subject,
            )
            age = args.default_age

        # get template for that reference image
        tpl_path, reg_to_default_tpl = get_template(
            template_name=args.template, bids_filters=args.ref_bids_filters, age=age
        )
        logging.info("loading template image: %s", tpl_path)
        tpl_to_default_tpl = [nt.load(reg_to_default_tpl)] if reg_to_default_tpl else []

        if args.datalad:
            dlad_ds.get(ref_image.relpath)

        matrix_path = ref_image.path.replace(
            "_{}{}".format(ref_image.entities["suffix"], ref_image.entities["extension"]),
            f"_from-{ref_image.entities['suffix']}_to-{args.template}_xfm.mat",
        )

        if os.path.exists(matrix_path):
            logging.info("reusing existing registration matrix: %s", matrix_path)
        else:
            # registration from ref series to template
            logging.info("running registration of reference serie: %s", ref_image.relpath)
            reg = registration_antspy(str(tpl_path), ref_image.path)
            copyfile(reg["fwdtransforms"][0], matrix_path)
            new_files.append(matrix_path)
        ref_to_tpl_tx = nt.linear.load(matrix_path)

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

        series_to_deface_groups = group_series(series_to_deface)

        for _group_entities, grouped_series in series_to_deface_groups:
            grouped_series = list(grouped_series)

            serie_groupref = [
                s
                for s in grouped_series
                if s.entities.get("part") in ["mag", None] and s.entities.get("echo") in ["1", None]
            ][0]
            if args.deface_sensitive:
                if next(annex_repo.get_metadata(serie_groupref.path))[1].get("distribution-restrictions") is None:
                    logging.info(
                        "skip %s as there are no distribution restrictions metadata set.", serie_groupref.relpath
                    )
                    continue
            logging.info("defacing %s", serie_groupref.relpath)

            if args.datalad:
                dlad_ds.get([gs.path for gs in grouped_series])
                # unlock before making any change to avoid unwanted save
                annex_repo.unlock([gs.path for gs in grouped_series])
            serie_groupref_nb = serie_groupref.get_image()

            serie2ref_reg = registration_antspy(
                ref_image.path, serie_groupref.path, transform="Rigid", initial_transform="Identity"
            )
            serie2ref_tx = nt.linear.load(serie2ref_reg["fwdtransforms"][0])

            series2tpl = nt.manip.TransformChain(tpl_to_default_tpl + [ref_to_tpl_tx, serie2ref_tx])
            tpl2series = nt.linear.Affine(np.linalg.inv(series2tpl.asaffine().matrix))
            warped_mask = nt.resampling.apply(
                tpl2series, default_tpl_defacemask, reference=serie_groupref_nb, order=0, output_dtype=np.uint8
            )

            if args.save_all_masks or serie_groupref == ref_image:
                warped_mask_path = Path(
                    serie_groupref.path.replace(
                        "_%s" % serie_groupref.entities["suffix"],
                        f"_space-{serie_groupref.entities['suffix']}_desc-deface_mask",
                    )
                )
                if os.path.exists(warped_mask_path):
                    logging.warning(f"{warped_mask_path} already exists : will not overwrite, clean before rerun")
                else:
                    warped_mask.to_filename(warped_mask_path)
                    new_files.append(warped_mask_path)

            for serie in grouped_series:
                serie_nb = serie.get_image()
                masked_serie = nb.Nifti1Image(
                    np.asanyarray(serie_nb.dataobj) * np.asanyarray(warped_mask.dataobj),
                    serie_nb.affine,
                    serie_nb.header,
                )
                if serie == serie_groupref:
                    # keep for report later
                    masked_serie_report = masked_serie
                masked_serie.to_filename(serie.path)
                modified_files.append(serie.path)

            mask_fig_path = generate_figure_path(
                layout,
                report_dir,
                serie_groupref,
                desc="mask",
            )
            logging.info("generating deface mosaic report: %s", mask_fig_path)
            generate_deface_mosaic_report(
                masked_serie_report,
                warped_mask,
                mask_fig_path,
            )
            new_files.append(mask_fig_path)

        report_path = generate_report(report_dir, subject=subject, session=session)
        new_files.append(report_path)

    if args.datalad and len(modified_files):
        logging.info("saving files changes in datalad")
        dlad_ds.save(
            modified_files + new_files,
            message="__deface__ %d series/images and update distribution-restrictions" % len(modified_files),
        )
        logging.info("saving metadata changes in datalad")
        annex_repo.set_metadata(modified_files, remove={"distribution-restrictions": "sensitive"})
