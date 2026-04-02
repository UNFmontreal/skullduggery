from __future__ import annotations

import logging
from pathlib import Path
from shutil import copyfile

import bids
import datalad.api
import nibabel as nb
import nitransforms as nt
import numpy as np

from .align import registration_antspy
from .mask import generate_deface_ear_mask
from .reports import build_defacemask_stem, strip_image_suffix, validate_nireports, write_deface_report
from .template import get_template
from .utils import get_age_and_unit


def deface_workflow(layout, args) -> bool:
    logging.root.setLevel(logging.getLevelName(args.debug_level.upper()))

    if args.deface_sensitive and not args.datalad:
        raise RuntimeError("--deface-sensitive requires --datalad to read git-annex metadata")

    dataset_root = Path(args.bids_path).expanduser().resolve()
    report_dir = Path(args.report_dir).expanduser().resolve() if args.report_dir else None
    if report_dir is not None:
        validate_nireports()

    dlad_ds = None
    annex_repo = None
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

    new_files: list[str] = []
    modified_files: list[str] = []

    default_tpl, _ = get_template()
    default_tpl_defacemask = generate_deface_ear_mask(nb.load(default_tpl))

    deface_ref_images = layout.get(**filters)
    if not deface_ref_images:
        logging.error("no reference image found with condition %s", filters)
        return False

    for ref_image in deface_ref_images:
        subject = ref_image.entities["subject"]
        session = ref_image.entities.get("session")
        age = get_age_and_unit(layout, subject, session)

        tpl_path, reg_to_default_tpl = get_template(
            template_name=args.template,
            bids_filters=args.ref_bids_filters,
            age=age,
        )
        logging.info("loading template image: %s", tpl_path)
        tpl_to_default_tpl = [nt.load(str(reg_to_default_tpl))] if reg_to_default_tpl else []

        if dlad_ds is not None:
            dlad_ds.get(ref_image.relpath)

        matrix_path = _matrix_output_path(ref_image.path, ref_image.entities["suffix"], args.template)
        if matrix_path.exists():
            logging.info("reusing existing registration matrix: %s", matrix_path)
        else:
            logging.info("running registration of reference series: %s", ref_image.relpath)
            ref_reg = registration_antspy(str(tpl_path), ref_image.path)
            copyfile(ref_reg["fwdtransforms"][0], matrix_path)
            new_files.append(str(matrix_path))

        ref_to_tpl_tx = nt.linear.load(str(matrix_path))
        series_to_deface = _dedupe_series(
            [
                image
                for bids_filter in args.other_bids_filters
                for image in layout.get(
                    extension=["nii", "nii.gz"],
                    subject=subject,
                    session=session,
                    **bids_filter,
                )
            ]
        )

        for serie in series_to_deface:
            if args.deface_sensitive:
                metadata = next(annex_repo.get_metadata(serie.path))[1]
                if metadata.get("distribution-restrictions") is None:
                    logging.info(
                        "skip %s as there are no distribution restrictions metadata set",
                        serie.relpath,
                    )
                    continue

            logging.info("defacing %s", serie.relpath)
            if dlad_ds is not None:
                dlad_ds.get(serie.path)
                annex_repo.unlock([serie.path])

            original_serie = serie.get_image()
            serie2ref_reg = registration_antspy(
                ref_image.path,
                serie.path,
                transform="Rigid",
                initial_transform="Identity",
            )
            serie2ref_tx = nt.linear.load(serie2ref_reg["fwdtransforms"][0])

            series2tpl = nt.manip.TransformChain(tpl_to_default_tpl + [ref_to_tpl_tx, serie2ref_tx])
            tpl2series = nt.linear.Affine(np.linalg.inv(series2tpl.asaffine().matrix))
            warped_mask = nt.resampling.apply(
                tpl2series,
                default_tpl_defacemask,
                reference=original_serie,
                order=0,
                output_dtype=np.uint8,
            )

            warped_mask_path = _mask_output_path(serie.path, serie.entities["suffix"])
            if args.save_all_masks or serie.path == ref_image.path:
                if warped_mask_path.exists():
                    logging.warning("%s already exists: will not overwrite", warped_mask_path)
                else:
                    warped_mask.to_filename(warped_mask_path)
                    new_files.append(str(warped_mask_path))

            masked_serie = nb.Nifti1Image(
                np.asanyarray(original_serie.dataobj) * np.asanyarray(warped_mask.dataobj),
                original_serie.affine,
                original_serie.header,
            )
            masked_serie.to_filename(serie.path)
            modified_files.append(serie.path)

            if report_dir is not None:
                report_paths = write_deface_report(
                    original_image=original_serie,
                    mask_image=warped_mask,
                    report_dir=report_dir,
                    image_relpath=serie.relpath,
                    source_suffix=serie.entities["suffix"],
                )
                new_files.extend([str(report_paths.html), str(report_paths.mosaic_svg)])

    if dlad_ds is not None and modified_files:
        saveable_new_files = [path for path in new_files if _is_within_dataset(path, dataset_root)]
        logging.info("saving file changes in datalad")
        dlad_ds.save(
            modified_files + saveable_new_files,
            message="__deface__ %d series/images and update distribution-restrictions" % len(modified_files),
        )
        logging.info("saving metadata changes in datalad")
        annex_repo.set_metadata(modified_files, remove={"distribution-restrictions": "sensitive"})

    return True


def _dedupe_series(series) -> list:
    unique_series = []
    seen_paths = set()
    for image in series:
        if image.path in seen_paths:
            continue
        seen_paths.add(image.path)
        unique_series.append(image)
    return unique_series


def _matrix_output_path(image_path: str, suffix: str, template_name: str) -> Path:
    source_path = Path(image_path)
    stem = strip_image_suffix(source_path)
    return source_path.with_name(f"{stem}_from-{suffix}_to-{template_name}_xfm.mat")


def _mask_output_path(image_path: str, suffix: str) -> Path:
    source_path = Path(image_path)
    stem = build_defacemask_stem(source_path, source_suffix=suffix)
    extension = "".join(source_path.suffixes)
    return source_path.with_name(f"{stem}{extension}")


def _is_within_dataset(path: str | Path, dataset_root: Path) -> bool:
    return Path(path).expanduser().resolve().is_relative_to(dataset_root)
