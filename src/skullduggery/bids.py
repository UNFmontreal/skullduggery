"""BIDS-related utilities for filtering and configuration.

This module provides helper functions for working with BIDS (Brain Imaging Data Structure)
layouts using pyBIDS, including filtering utilities for query wildcards.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
from pathlib import Path

import bids
from bids.layout import Query


def _filter_pybids_any(dct: dict) -> dict:
    """Convert wildcard strings in dictionary to pyBIDS Query.ANY.

    Transforms dictionary values that are "*" strings into pyBIDS Query.ANY
    objects for flexible filtering in BIDS layout queries.

    Args:
        dct: Dictionary potentially containing "*" string values.

    Returns:
        dict: New dictionary with "*" values replaced by Query.ANY.
    """
    return {k: Query.ANY if v == "*" else v for k, v in dct.items()}


def _bids_filter(json_str: str) -> dict | list:
    """Parse BIDS filter JSON from string or file path.

    Loads JSON configuration for BIDS filtering, with support for both
    inline JSON strings and file paths. Converts wildcard strings to Query.ANY.

    Args:
        json_str: JSON string or path to JSON file containing BIDS filters.

    Returns:
        dict or list: Parsed JSON filter configuration with wildcards
        converted to Query.ANY objects.

    Raises:
        json.JSONDecodeError: If JSON parsing fails.
    """
    if os.path.exists(os.path.abspath(json_str)):
        json_str = Path(json_str).read_text()
    return json.loads(json_str, object_hook=_filter_pybids_any)


def _bidsignore_patterns(value: str) -> tuple[re.Pattern[str], ...]:
    """Parse BIDS ignore patterns from inline JSON or a JSON file path."""
    if os.path.exists(os.path.abspath(value)):
        value = Path(value).read_text()

    try:
        patterns = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError("bidsignore patterns must be valid JSON") from exc

    if not isinstance(patterns, list):
        raise argparse.ArgumentTypeError("bidsignore patterns must be a JSON array of strings")

    compiled_patterns = []
    for pattern in patterns:
        if not isinstance(pattern, str):
            raise argparse.ArgumentTypeError("bidsignore patterns must be a JSON array of strings")

        pattern = pattern.strip()
        if pattern:
            compiled_patterns.append(re.compile(fnmatch.translate(pattern)))

    return tuple(compiled_patterns)


def create_bids_layout(args: argparse.Namespace) -> bids.BIDSLayout:
    """Create the BIDS layout with the requested validation strictness.

    Args:
        args: Parsed CLI arguments with ``bids_path`` and
            ``no_strict_bids_validation`` attributes.

    Returns:
        PyBIDS layout rooted at ``args.bids_path``. Validation is disabled
        when ``--no-strict-bids-validation`` was requested.
    """
    indexer = bids.BIDSLayoutIndexer(
        ignore=args.bidsignore_patterns,
    )

    return bids.BIDSLayout(
        os.path.abspath(args.bids_path),
        validate=not args.no_strict_bids_validation,
        indexer=indexer,
    )
