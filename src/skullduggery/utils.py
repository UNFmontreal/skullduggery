"""Utility functions for age handling and BIDS data organization.

This module provides utilities for extracting participant age information from
BIDS datasets, normalizing age units, and grouping imaging series by entities.
"""

from __future__ import annotations

import itertools
import logging
import math
from typing import Iterable, Literal, cast, Generator

import bids

logger = logging.getLogger(__name__)


def get_age_and_unit(
    layout: bids.BIDSLayout,
    subject: str,
    session: str | None = None,
) -> tuple[float, str] | None:
    """Read session-level age when defined, otherwise participant-level age.

    Subject/session labels may include their BIDS prefixes. An age column in the
    sessions table is authoritative: missing, duplicate or invalid ages return None rather
    than borrowing an age from participants.tsv or another visit. Units from the
    selected table's metadata are normalized to weeks, months or years for the
    template-selection code. Participant ages without Units metadata default to
    years, as specified by BIDS. Unsupported units return None, allowing the
    workflow's explicit --default-age fallback.
    """
    subject = subject[4:] if subject.startswith("sub-") else subject
    if session is not None and session.startswith("ses-"):
        session = session[4:]
    tables = layout.get(subject=subject, suffix="sessions", extension=".tsv", scope="raw")
    if len(tables) > 1:
        logger.warning("expected one sessions table for sub-%s; found %d", subject, len(tables))
        return None
    frame = tables[0].get_df() if tables else None
    if frame is not None and "age" in frame.columns:
        if session is None:
            logger.warning("session required to resolve age from sub-%s sessions table", subject)
            return None
        key, identifier = "session_id", f"ses-{session}"
    else:
        tables = layout.get(suffix="participants", extension=".tsv", scope="raw")
        frame = None
        key, identifier = "participant_id", f"sub-{subject}"
    if len(tables) != 1:
        logger.warning("expected one age table for sub-%s; found %d", subject, len(tables))
        return None

    table = tables[0]
    if frame is None:
        frame = table.get_df()
    if key not in frame.columns or "age" not in frame.columns:
        logger.warning("%s does not contain %s and age columns", table.path, key)
        return None
    mask = frame[key] == identifier
    # Retain support for older participant tables that included session IDs.
    if key == "participant_id" and session is not None and "session_id" in frame.columns:
        mask &= frame["session_id"] == f"ses-{session}"
    matches = frame.loc[mask, "age"]
    if len(matches) != 1:
        logger.warning("expected one age for %s in %s; found %d", identifier, table.path, len(matches))
        return None
    try:
        age = float(matches.iloc[0])
    except (TypeError, ValueError):
        age = math.nan
    if not math.isfinite(age) or age < 0:
        logger.warning("invalid or missing age for %s in %s", identifier, table.path)
        return None
    unit = _get_age_units(table.get_metadata(), default="years" if key == "participant_id" else None)
    if not unit:
        logger.warning("%s metadata does not define supported age units", table.path)
        return None
    return age, unit


# from nibabies

SUPPORTED_AGE_UNITS = (
    "weeks",
    "months",
    "years",
)

AgeUnit = Literal["weeks", "months", "years"]


def _get_age_units(data: dict, default: AgeUnit | None = None) -> AgeUnit | bool:
    """Extract age unit from BIDS metadata dictionary.

    Reads the 'age' field from BIDS metadata and validates the Units value.

    Args:
        data: BIDS metadata dictionary, from a participants or sessions TSV sidecar.
        default: Unit to use only when Units is absent (BIDS participant age defaults to years).

    Returns:
        AgeUnit: Normalized age unit ("weeks", "months", or "years"),
            or False if units are missing, not a string, or unsupported.
    """

    age_metadata = data.get("age", {})
    if not isinstance(age_metadata, dict):
        return False
    units = age_metadata.get("Units", default or "")
    if not isinstance(units, str):
        # Multiple units consfuse us
        return False

    normalized_units = units.strip().lower()
    normalized_units = {"week": "weeks", "month": "months", "year": "years"}.get(
        normalized_units, normalized_units
    )
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
