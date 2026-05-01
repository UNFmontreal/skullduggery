"""Utility functions for age handling and BIDS data organization.

This module provides utilities for extracting participant age information from
BIDS datasets, normalizing age units, and grouping imaging series by entities.
"""

from __future__ import annotations

import itertools
import logging
from typing import Iterable, Literal, cast, Generator

import bids

logger = logging.getLogger(__name__)


def get_age_and_unit(
    layout: bids.BIDSLayout,
    subject: str,
    session: str | None = None,
) -> tuple[float, str] | None:
    """Extract participant age and unit from BIDS participants.tsv.

    Queries the BIDS layout for a specific participant's age information,
    including unit validation from the TSV metadata.

    Args:
        layout: PyBIDS BIDSLayout object.
        subject: Participant identifier (without 'sub-' prefix).
        session: Optional session identifier (without 'ses-' prefix).

    Returns:
        tuple: (age_value, age_unit) where age_value is float and
            age_unit is one of SUPPORTED_AGE_UNITS, or None if age not found.

    Logs warnings if:
        - participants.tsv missing 'age' column
        - No matching age found for participant
        - Age units metadata missing or unsupported
    """
    participants_tsv = layout.get(suffix="participants", extension=".tsv")[0]
    participants_df = participants_tsv.get_df()
    participant_mask = participants_df["participant_id"] == f"sub-{subject}"
    if session and "session_id" in participants_df.columns:
        participant_mask = participant_mask & (participants_df["session_id"] == f"ses-{session}")

    if "age" not in participants_df.columns:
        logger.warning("participants.tsv does not contain an age column")
        return None

    matching_rows = participants_df.loc[participant_mask, "age"]
    if matching_rows.empty:
        logger.warning("no participant age found for sub-%s", subject)
        return None

    participant_age = float(matching_rows.iloc[0])
    age_unit = _get_age_units(participants_tsv.get_metadata())
    if not age_unit:
        logger.warning("participants.tsv metadata does not define supported age units")
        return None

    return (participant_age, age_unit)


# from nibabies

SUPPORTED_AGE_UNITS = (
    "weeks",
    "months",
    "years",
)

AgeUnit = Literal["weeks", "months", "years"]


def _get_age_units(data: dict) -> AgeUnit | bool:
    """Extract age unit from BIDS metadata dictionary.

    Reads the 'age' field from BIDS metadata and validates the Units value.

    Args:
        data: BIDS metadata dictionary, typically from participants.tsv metadata.

    Returns:
        AgeUnit: Normalized age unit ("weeks", "months", or "years"),
            or False if units are missing, not a string, or unsupported.
    """

    units = data.get("age", {}).get("Units", "")
    if not isinstance(units, str):
        # Multiple units consfuse us
        return False

    normalized_units = units.lower()
    if normalized_units in SUPPORTED_AGE_UNITS:
        return cast(AgeUnit, normalized_units)
    return False


GROUPED_ENTITIES = ["part", "echo", "reconstruction"]


def filters_query(layout: bids.BIDSLayout, subject: str, session: str | None, bids_filters: list) -> list:
    """Query BIDS layout for series matching multiple filter sets.

    Applies a list of filter dictionaries to the layout and returns all matching
    series. Useful for retrieving multiple complementary sets of images.

    Args:
        layout: PyBIDS BIDSLayout object.
        subject: Participant identifier (without 'sub-' prefix).
        session: Session identifier (without 'ses-' prefix), or None.
        bids_filters: List of filter dictionaries to apply sequentially.

    Returns:
        list: Aggregated list of BIDSFile objects matching any filter,
              with nii.gz and nii extensions.
    """
    series = []
    for filters in bids_filters:
        series.extend(
            layout.get(
                extension=["nii", "nii.gz"],
                subject=subject,
                session=session,
                **filters,
            )
        )
    return series


def group_series(
    series: Iterable, ref_image
) -> Generator[tuple[dict, bids.layout.BIDSFile, list], bids.layout.BIDSFile, list[bids.layout.BIDSFile]]:
    """Group imaging series by BIDS entities, ignoring multi-part entities.

    Groups a collection of imaging series by their BIDS entities, excluding
    entities like 'part', 'echo', and 'reconstruction' that represent variants
    of the same scan. Selects a representative image for each group.

    Args:
        series: Iterable of BIDSFile objects to group.
        ref_image: Reference image to use as group representative if present.

    Returns:
        itertools.groupby: Iterator of (entities_dict, group_ref, series_group) tuples where:
            - entities_dict: Dictionary of BIDS entities for the group
            - group_ref: Selected representative image (preferring magnitude/echo-1)
            - series_group: List of all BIDSFile objects in the group
    """
    group_gen = itertools.groupby(
        series, lambda x: {k: v for k, v in x.get_entities(metadata=False).items() if k not in GROUPED_ENTITIES}
    )
    for _group_entities, grouped_series in group_gen:
        grouped_series = list(grouped_series)

        serie_groupref_candidates = [
            s
            for s in grouped_series
            if s.entities.get("part") in ["mag", None] and s.entities.get("echo") in ["1", None]
        ]

        serie_groupref = ref_image if ref_image in serie_groupref_candidates else serie_groupref_candidates[0]
        yield _group_entities, serie_groupref, grouped_series
