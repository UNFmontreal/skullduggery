from __future__ import annotations

import typing as ty


def get_age_and_unit(layout, subject, session=None):
    participants_tsv = layout.get(suffix="participants", extension=".tsv")[0]
    participants_df = participants_tsv.get_df()
    session_df_mask = participants_df["participant_id"] == f"sub-{subject}"
    if session:
        session_df_mask = session_df_mask & participants_df["session_id"] == f"ses-{session}"
    participant_age = participants_df.loc[session_df_mask, "age"].values[0]
    age_unit = _get_age_units(participants_tsv.get_metadata())
    return (participant_age, age_unit)


### from nibabies

SUPPORTED_AGE_UNITS = (
    "weeks",
    "months",
    "years",
)


def _get_age_units(data: dict) -> ty.Literal["weeks", "months", "years", False]:

    units = data.get("age", {}).get("Units", "")
    if not isinstance(units, str):
        # Multiple units consfuse us
        return False

    if units.lower() in SUPPORTED_AGE_UNITS:
        return units.lower()
    return False
