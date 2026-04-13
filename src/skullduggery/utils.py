from __future__ import annotations

import logging
from typing import Literal, cast

import nibabel as nb


def output_debug_images(ref, moving, affine):
    moving_nb = moving.get_image()
    moving_suffix = moving.entities["suffix"]
    moving_reg_path = moving.path.replace(f"_{moving_suffix}", f"_space-MNIlinreg_{moving_suffix}")
    moving_reg = affine.transform(
        moving_nb.get_fdata(),
        image_grid2world=moving_nb.affine,
        sampling_grid_shape=ref.shape,
        sampling_grid2world=ref.affine,
    )
    logging.info(f"writing reference serie linearly warped to MNI template: {moving_reg_path}")
    nb.Nifti1Image(moving_reg, ref.affine).to_filename(moving_reg_path)

    ref_inv_path = moving.path.replace(f"_{moving_suffix}", f"_mod-{moving_suffix}_MNIlinreg")
    ref_inv = affine.transform_inverse(
        ref.get_fdata(),
        image_grid2world=ref.affine,
        sampling_grid_shape=moving_nb.shape,
        sampling_grid2world=moving_nb.affine,
    )
    logging.info(f"writing MNI template image linearly warped to the reference serie: {ref_inv_path}")
    nb.Nifti1Image(ref_inv, moving_nb.affine).to_filename(ref_inv_path)


def get_age_and_unit(layout, subject, session=None):
    participants_tsv = layout.get(suffix='participants', extension='.tsv')[0]
    participants_df = participants_tsv.get_df()
    participant_mask = participants_df['participant_id'] == f"sub-{subject}"
    if session and 'session_id' in participants_df.columns:
        participant_mask = participant_mask & (participants_df['session_id'] == f"ses-{session}")

    if 'age' not in participants_df.columns:
        logging.warning('participants.tsv does not contain an age column')
        return None

    matching_rows = participants_df.loc[participant_mask, 'age']
    if matching_rows.empty:
        logging.warning('no participant age found for sub-%s', subject)
        return None

    participant_age = float(matching_rows.iloc[0])
    age_unit = _get_age_units(participants_tsv.get_metadata())
    if not age_unit:
        logging.warning('participants.tsv metadata does not define supported age units')
        return None

    return participant_age, age_unit

### from nibabies

SUPPORTED_AGE_UNITS = (
    'weeks',
    'months',
    'years',
)

AgeUnit = Literal['weeks', 'months', 'years']

def _get_age_units(data: dict) -> AgeUnit | bool:

    units = data.get('age', {}).get('Units', '')
    if not isinstance(units, str):
        # Multiple units consfuse us
        return False

    normalized_units = units.lower()
    if normalized_units in SUPPORTED_AGE_UNITS:
        return cast(AgeUnit, normalized_units)
    return False
