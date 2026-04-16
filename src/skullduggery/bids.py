"""BIDS-related utilities for filtering and configuration.

This module provides helper functions for working with BIDS (Brain Imaging Data Structure)
layouts using pyBIDS, including filtering utilities for query wildcards.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from bids.layout import Query


def _filter_pybids_any(dct):
    """Convert wildcard strings in dictionary to pyBIDS Query.ANY.

    Transforms dictionary values that are "*" strings into pyBIDS Query.ANY
    objects for flexible filtering in BIDS layout queries.

    Args:
        dct: Dictionary potentially containing "*" string values.

    Returns:
        dict: New dictionary with "*" values replaced by Query.ANY.
    """
    return {k: Query.ANY if v == "*" else v for k, v in dct.items()}


def _bids_filter(json_str):
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
