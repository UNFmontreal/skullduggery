"""Main defacing workflow for neuroimaging datasets.

This module orchestrates the complete defacing pipeline, including template
selection, registration, mask warping, and report generation for BIDS datasets.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from shutil import copyfile
from importlib import resources

import bids
import nibabel as nb
import nitransforms as nt
import numpy as np

from .align import spatial_volume, registration_antspy
from .mask import build_series_deface_mask, mask_nifti
from .report import generate_deface_mosaic_report, generate_figure_path, generate_report
from .template import get_template, select_template_by_age
from .utils import get_age_and_unit, group_series, filters_query

logger = logging.getLogger(__name__)

try:
    import datalad.api
except ImportError:
    datalad = None


def _compose_transform_chain(*transforms: nt.base.TransformBase | None) -> nt.base.TransformBase:
    """Compose transforms without mutating reusable TransformChain instances.

    Args:
        transforms: Transform objects or transform chains in application
            order. ``None`` values are ignored.

    Returns:
        A single transform when one usable transform is provided, otherwise
        a new ``TransformChain`` containing the flattened transforms.

    Raises:
        ValueError: If all provided transforms are ``None``.
    """
    chain_transforms = []
    for transform in transforms:
        if transform is None:
            continue
        if isinstance(transform, nt.manip.TransformChain):
            chain_transforms.extend(transform.transforms)
        else:
            chain_transforms.append(transform)

    if not chain_transforms:
        raise ValueError("at least one transform is required")
    if len(chain_transforms) == 1:
        return chain_transforms[0]
    return nt.manip.TransformChain(chain_transforms)


def deface_workflow(layout: bids.BIDSLayout, args: argparse.Namespace) -> bool:
    """Execute the complete defacing workflow on a BIDS dataset.

    Orchestrates registration-based defacing for all specified anatomical images:
    1. Loads or generates reference images and defacing masks
    2. Registers each participant's reference image to template
    3. Warps template-space defacing mask to native space
    4. Applies mask to all relevant anatomical series
    5. Generates QA reports
    6. Optionally commits changes to DataLad

    Args:
        layout: PyBIDS BIDSLayout object for the dataset.
        args: Parsed command-line arguments containing:
            - participant_label: Participant(s) to deface
            - session_label: Session(s) to process
            - template: Template name for registration
            - default_age: Fallback age for missing data
            - ref_bids_filters: Filters for selecting reference images
            - other_bids_filters: Filters for images to deface
            - save_all_masks: Whether to save all masks or just reference
            - datalad: Whether to use DataLad for saving
            - deface_sensitive: Only deface images marked as sensitive
            - report_dir: Directory for saving reports
            - debug_level: Logging level

    Returns:
        bool: True if workflow completed successfully, False otherwise.

    Side effects:
        - Modifies anatomical images in place (applies defacing mask)
        - Creates transformation matrix files
        - Creates mask files (if save_all_masks or for reference)
        - Generates SVG visualizations
        - Creates HTML reports
        - Commits to DataLad if enabled
    """

    report_dir = layout._root / (args.report_dir or Path(".skullduggery"))

    if args.datalad or args.deface_sensitive:
        if datalad is None:
            raise ImportError(
                "datalad is required for --datalad or --deface-sensitive flag. "
                "Install it with: pip install skullduggery[datalad]"
            )
        dlad_ds = datalad.api.Dataset(args.bids_path)
        annex_repo = dlad_ds.repo

    new_files, modified_files = [], []

    # generate deface mask in default template space (MNI)
    default_tpl, _, _ = get_template()
    default_tpl_nb = nb.load(default_tpl)
    #default_tpl_defacemask = generate_deface_ear_mask(default_tpl_nb)
    default_deface_mask_path = resources.files("skullduggery.data").joinpath(
        "tpl-MNI152NLin6Asym_desc-deface_mask.nii.gz"
    )
    default_tpl_defacemask = nb.load(default_deface_mask_path)

    # lookup reference images
    deface_ref_images = filters_query(layout, args.participant_label, args.session_label, [args.ref_bids_filters])
    if not len(deface_ref_images):
        logger.error(f"no reference image found with condition {filters}")
        return False
    logger.debug(f"found {len(deface_ref_images)} reference images")

    processed_series_paths = set()

    for ref_image in deface_ref_images:
        if ref_image.path in processed_series_paths:
            logger.info("skip %s because it has already been defaced in this run", ref_image.relpath)
            continue

        subject = ref_image.entities["subject"]
        session = ref_image.entities.get("session")

        # get age to get the right template if cohorts
        age = get_age_and_unit(layout, subject, session)
        if age is None and args.default_age is not None:
            logger.warning(
                "using fallback age %s:%s for sub-%s",
                args.default_age[0],
                args.default_age[1],
                subject,
            )
            age = args.default_age

        # auto-select template based on age if not explicitly specified
        template_name = args.template
        if template_name is None:
            template_name = select_template_by_age(age)

        if args.template is None and age is not None:
            logging.info(
                "auto-selected template %s for sub-%s (age: %s %s)",
                template_name,
                subject,
                age[0],
                age[1],
            )

        # get template for that reference image
        tpl_path, tpl_mask, default_tpl_to_tpl = get_template(template_name, args.ref_bids_filters, age=age)
        logger.debug("loading template image: %s , mask:%s", tpl_path, tpl_mask)
        tpl_nb = nb.load(tpl_path)
        default_tpl_to_tpl_tx = (
            nt.manip.TransformChain.from_filename(default_tpl_to_tpl, fmt="itk") if default_tpl_to_tpl else None
        )

        if args.datalad:
            dlad_ds.get(ref_image.relpath)
        ref_image_nb = ref_image.get_image()

        matrix_path = ref_image.path.replace(
            "_{}{}".format(ref_image.entities["suffix"], ref_image.entities["extension"]),
            f"_from-{ref_image.entities['suffix']}_to-{template_name}_xfm.mat",
        )

        if os.path.exists(matrix_path):
            logger.info("reusing existing registration matrix: %s", matrix_path)
        else:
            # registration from ref series to template
            logger.info("running registration of reference serie: %s", ref_image.relpath)
            reg = registration_antspy(
                tpl_path,
                ref_image.path,
                transform="TRSAA",
                ref_mask=tpl_mask,
                verbose=args.debug_level.upper() == "DEBUG",
            )
            copyfile(reg["fwdtransforms"][0], matrix_path)
            new_files.append(matrix_path)
        ref_to_tpl_tx = nt.linear.load(matrix_path)
        ref_to_tpl_pull_tx = nt.linear.Affine(np.linalg.inv(ref_to_tpl_tx.matrix))
        ref_to_default_tpl_tx = _compose_transform_chain(ref_to_tpl_pull_tx, default_tpl_to_tpl_tx)
        ref_deface_mask = nt.resampling.apply(
            ref_to_default_tpl_tx,
            default_tpl_defacemask,
            reference=spatial_volume(ref_image_nb),
            order=0,
            output_dtype=np.uint8,
        )

        series_to_deface = filters_query(layout, subject, session, args.other_bids_filters)

        for _group_entities, serie_groupref, grouped_series in group_series(series_to_deface, ref_image):
            grouped_series = [serie for serie in grouped_series if serie.path not in processed_series_paths]
            if not grouped_series:
                logger.debug("skip already-defaced series group for %s", ref_image.relpath)
                continue

            if args.deface_sensitive:
                if next(annex_repo.get_metadata(serie_groupref.path))[1].get("distribution-restrictions") is None:
                    logger.info(
                        "skip %s as there are no distribution restrictions metadata set.", serie_groupref.relpath
                    )
                    continue
            logger.info("defacing %s", serie_groupref.relpath)

            if args.datalad:
                group_paths = [gs.path for gs in grouped_series]
                dlad_ds.get(group_paths)
                annex_repo.unlock(group_paths)

            report_inputs = []
            for serie in grouped_series:
                serie_nb = serie.get_image()
                serie_mask, registered_ref, desc = build_series_deface_mask(
                    ref_image,
                    ref_image_nb,
                    serie,
                    serie_nb,
                    ref_to_tpl_tx,
                    ref_deface_mask,
                    tpl_nb,
                    verbose=args.debug_level.upper() == "DEBUG",
                )

                if args.save_all_masks or serie == ref_image:
                    warped_mask_path = Path(
                        serie.path.replace(
                            "_%s" % serie.entities["suffix"],
                            f"_space-{serie.entities['suffix']}_desc-deface_mask",
                        )
                    )
                    if os.path.exists(warped_mask_path):
                        logger.info("overwriting deface mask to match current image: %s", warped_mask_path)
                    else:
                        logger.debug("writing deface mask: %s", warped_mask_path)
                    new_files.append(warped_mask_path)
                    serie_mask.to_filename(warped_mask_path)

                masked_serie = mask_nifti(serie_nb, serie_mask)
                report_input = (serie, serie_mask, masked_serie, registered_ref, desc)
                report_inputs.append(report_input)
                masked_serie.to_filename(serie.path)
                modified_files.append(serie.path)
                processed_series_paths.add(serie.path)

            for serie, serie_mask, masked_serie, registered_ref, desc in report_inputs:
                mask_fig_path = generate_figure_path(
                    layout,
                    serie,
                    desc=desc,
                    report_dir=report_dir,
                )
                logger.info("generating deface mosaic report: %s", mask_fig_path)
                generate_deface_mosaic_report(
                    masked_serie,
                    serie_mask,
                    mask_fig_path,
                    registered_tmpl=registered_ref,
                )
                new_files.append(mask_fig_path)

        report_path = generate_report(report_dir, subject=subject, session=session)
        new_files.append(report_path)

    if args.datalad and len(modified_files):
        logger.info("saving files changes in datalad")
        dlad_ds.save(
            modified_files + new_files,
            message="[deface] 💀 %d series/images and update distribution-restrictions" % len(modified_files),
        )
        logging.info("saving metadata changes in datalad")
    if args.datalad or args.deface_sensitive:
        annex_repo.set_metadata(modified_files, remove={"distribution-restrictions": "sensitive"})

    return True
