from __future__ import annotations

import itertools
import logging
from typing import Literal, cast


def get_age_and_unit(layout, subject, session=None):
    participants_tsv = layout.get(suffix="participants", extension=".tsv")[0]
    participants_df = participants_tsv.get_df()
    participant_mask = participants_df["participant_id"] == f"sub-{subject}"
    if session and "session_id" in participants_df.columns:
        participant_mask = participant_mask & (participants_df["session_id"] == f"ses-{session}")

    if "age" not in participants_df.columns:
        logging.warning("participants.tsv does not contain an age column")
        return None

    matching_rows = participants_df.loc[participant_mask, "age"]
    if matching_rows.empty:
        logging.warning("no participant age found for sub-%s", subject)
        return None

    participant_age = float(matching_rows.iloc[0])
    age_unit = _get_age_units(participants_tsv.get_metadata())
    if not age_unit:
        logging.warning("participants.tsv metadata does not define supported age units")
        return None

    return participant_age, age_unit


### from nibabies

SUPPORTED_AGE_UNITS = (
    "weeks",
    "months",
    "years",
)

AgeUnit = Literal["weeks", "months", "years"]


def _get_age_units(data: dict) -> AgeUnit | bool:

    units = data.get("age", {}).get("Units", "")
    if not isinstance(units, str):
        # Multiple units consfuse us
        return False

    normalized_units = units.lower()
    if normalized_units in SUPPORTED_AGE_UNITS:
        return cast(AgeUnit, normalized_units)
    return False


GROUPED_ENTITIES = ["part", "echo", "reconstruction"]


def group_series(series):
    return itertools.groupby(
        series, lambda x: {k: v for k, v in x.get_entities(metadata=False).items() if k not in GROUPED_ENTITIES}
    )
