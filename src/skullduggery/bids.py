"""BIDS-related utilities for filtering and configuration.

This module provides helper functions for working with BIDS (Brain Imaging Data Structure)
layouts using pyBIDS, including filtering utilities for query wildcards.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
from pathlib import Path
from typing import Tuple

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


def _load_bidsignore(bids_root: pathlib.Path, mode: str = "python") -> Tuple:
    """Load .bidsignore file from a BIDS dataset, returns list of regexps"""
    bids_ignore_path = bids_root / ".bidsignore"
    if bids_ignore_path.exists():
        bids_ignores = bids_ignore_path.read_text().splitlines()
        if mode == "python":
            import fnmatch
            import re

            return tuple(
                [
                    re.compile(fnmatch.translate(bi))
                    for bi in bids_ignores
                    if len(bi) and bi.strip()[0] != "#"
                ]
            )
        elif mode == "bash":
            return tuple(
                [f"m/{bi}/" for bi in bids_ignores if len(bi) and bi.strip()[0] != "#"]
            )
    return tuple()


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
        ignore=_load_bidsignore(args.bids_path),
    )

    return bids.BIDSLayout(
        os.path.abspath(args.bids_path),
        validate=not args.no_strict_bids_validation,
        indexer=indexer,
    )
