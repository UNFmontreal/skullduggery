from __future__ import annotations

import json
import os
from pathlib import Path

import bids


def _filter_pybids_any(dct):
    return {k: bids.layout.Query.ANY if v == "*" else v for k, v in dct.items()}


def _bids_filter(json_str):
    if os.path.exists(os.path.abspath(json_str)):
        json_str = Path(json_str).read_text()
    return json.loads(json_str, object_hook=_filter_pybids_any)
