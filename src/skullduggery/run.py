from __future__ import annotations

import argparse
import logging
import os

import bids
import coloredlogs

from .bids import _bids_filter

DEBUG = bool(os.environ.get("DEBUG", False))
coloredlogs.install()
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
    logging.root.setLevel(logging.DEBUG)
    root_handler = logging.root.handlers[0]
    root_handler.setFormatter(
        logging.Formatter("%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s")
    )
else:
    logging.basicConfig(
        format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s", level=logging.INFO
    )
    logging.root.setLevel(logging.INFO)

lgr = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="deface anatomical series by performing an affine registration to a template and warping mask to native space",
    )

    parser.add_argument("bids_path", help="BIDS folder to deface.")
    parser.add_argument(
        "--participant-label",
        action="store",
        nargs="+",
        default=bids.layout.Query.ANY,
        help="a space delimited list of participant identifiers or a single "
        "identifier (the sub- prefix can be removed)",
    )
    parser.add_argument(
        "--session-label",
        action="store",
        nargs="+",
        default=[bids.layout.Query.NONE, bids.layout.Query.ANY],
        help="a space delimited list of sessions identifiers or a single "
        "identifier (the ses- prefix can be removed)",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Force pyBIDS reset_database and reindexing",
    )
    parser.add_argument(
        "--datalad",
        action="store_true",
        help="Update distribution-restrictions metadata and commit changes",
    )
    parser.add_argument(
        "--save-all-masks",
        action="store_true",
        help="Save mask for all defaced series, default is only saving mask for reference serie.",
    )
    parser.add_argument(
        "--debug-images",
        action="store_true",
        help="Output debug images in the current directory",
    )
    parser.add_argument(
        "--ref-bids-filters",
        dest="ref_bids_filters",
        action="store",
        type=_bids_filter,
        help="path to or inline json with pybids filters to select session reference to register defacemask",
    )
    parser.add_argument(
        "--other-bids-filters",
        dest="other_bids_filters",
        action="store",
        type=_bids_filter,
        help="path to or inline json with pybids filters to select all images to deface",
    )
    parser.add_argument(
        "--debug",
        dest="debug_level",
        action="store",
        default="info",
        help="debug level",
    )
    return parser.parse_args()
"""
def parse_args() -> dict:

    p = argparse.ArgumentParser(description="forbids - setup and validate protocol compliance")
    p.add_argument("command", help="init or validate")
    p.add_argument("bids_path", help="path to the BIDS dataset")
    p.add_argument("--participant-label", nargs="+",)
    p.add_argument("--session-label", nargs="*", default=[bids.layout.Query.NONE, bids.layout.Query.ANY])
    return p.parse_args()
"""

def main() -> None:
    args = parse_args()
    layout = bids.BIDSLayout(os.path.abspath(args.bids_path))
    success = False

    success = workflow(layout, args)

    exit(0 if success else 1)

if __name__ == "__main__":
    main()
