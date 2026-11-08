from __future__ import annotations

import argparse
import logging

import pytest

from skullduggery import run
from skullduggery.run import _default_age, main, parse_args


def test_default_age_parses_value_and_normalises_unit():
    assert _default_age("5:Years") == (5.0, "years")


def test_default_age_accepts_fractional_value():
    assert _default_age("1.5:months") == (1.5, "months")


@pytest.mark.parametrize(
    "value, message",
    [
        ("5", "must be in the form"),
        ("abc:years", "must be numeric"),
        ("5:decades", "must be one of"),
    ],
)
def test_default_age_rejects_invalid_input(value, message):
    with pytest.raises(argparse.ArgumentTypeError, match=message):
        _default_age(value)


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["skullduggery", "/data/bids"])
    args = parse_args()
    assert args.bids_path == "/data/bids"
    assert args.template is None
    assert args.default_age is None
    assert args.force_reindex is False
    assert args.no_strict_bids_validation is False
    assert args.datalad is False
    assert args.save_all_masks is False
    assert args.report_dir is None
    assert args.deface_sensitive is False
    assert args.ref_bids_filters == {"suffix": "T1w", "datatype": "anat", "echo": [None, 1], "part": [None, "mag"]}
    assert args.other_bids_filters == [{"datatype": "anat"}]


def test_parse_args_explicit_options(monkeypatch):
    argv = [
        "skullduggery",
        "/data/bids",
        "--participant-label",
        "01",
        "02",
        "--session-label",
        "pre",
        "--template",
        "MNIInfant",
        "--default-age",
        "3:months",
        "--force-reindex",
        "--no-strict-bids-validation",
        "--datalad",
        "--save-all-masks",
        "--report-dir",
        "/tmp/reports",
        "--other-bids-filters",
        '{"suffix": "T2w"}',
        "--deface-sensitive",
        "--debug",
        "debug",
    ]
    monkeypatch.setattr("sys.argv", argv)
    args = parse_args()
    assert args.participant_label == ["01", "02"]
    assert args.session_label == ["pre"]
    assert args.template == "MNIInfant"
    assert args.default_age == (3.0, "months")
    assert args.force_reindex is True
    assert args.no_strict_bids_validation is True
    assert args.datalad is True
    assert args.save_all_masks is True
    assert args.report_dir == "/tmp/reports"
    assert args.other_bids_filters == {"suffix": "T2w"}
    assert args.deface_sensitive is True
    assert args.debug_level == "debug"


def _args(**overrides):
    base = dict(
        bids_path="/data/bids",
        no_strict_bids_validation=False,
        debug_level="info",
    )
    base.update(overrides)
    return argparse.Namespace(**base)


@pytest.mark.parametrize("success, exit_code", [(True, 0), (False, 1)])
def test_main_exits_with_workflow_status(mocker, monkeypatch, success, exit_code):
    args = _args()
    mocker.patch.object(run, "parse_args", return_value=args)
    layout = object()
    create = mocker.patch.object(run, "create_bids_layout", return_value=layout)
    workflow = mocker.patch.object(run, "deface_workflow", return_value=success)

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == exit_code
    create.assert_called_once_with(args)
    workflow.assert_called_once_with(layout, args)


def test_main_configures_package_logger(mocker):
    args = _args(debug_level="debug")
    mocker.patch.object(run, "parse_args", return_value=args)
    mocker.patch.object(run, "create_bids_layout", return_value=object())
    mocker.patch.object(run, "deface_workflow", return_value=True)
    package_logger = logging.getLogger("skullduggery")
    original_level = package_logger.level
    original_handlers = list(package_logger.handlers)
    package_logger.handlers.clear()
    try:
        with pytest.raises(SystemExit):
            main()
        assert package_logger.level == logging.DEBUG
        assert len(package_logger.handlers) == 1
    finally:
        package_logger.setLevel(original_level)
        package_logger.handlers[:] = original_handlers
