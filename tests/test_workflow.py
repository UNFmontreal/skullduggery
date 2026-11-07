from __future__ import annotations

import argparse
from types import SimpleNamespace

import bids
import nibabel as nb
import nitransforms as nt
import numpy as np
import pytest

from skullduggery import report, workflow
from skullduggery.workflow import _compose_transform_chain, deface_workflow


def _identity_itk_transform(path):
    nt.linear.Affine(np.eye(4)).to_filename(path, fmt="itk")
    return str(path)


def _args(**overrides):
    base = dict(
        bids_path="",
        participant_label="01",
        session_label=None,
        template=None,
        default_age=None,
        ref_bids_filters={"suffix": "T1w", "datatype": "anat", "echo": [None, 1], "part": [None, "mag"]},
        other_bids_filters=[{"datatype": "anat"}],
        save_all_masks=False,
        datalad=False,
        deface_sensitive=False,
        report_dir=None,
        debug_level="info",
    )
    base.update(overrides)
    return argparse.Namespace(**base)


@pytest.fixture
def workflow_env(mocker, bids_dataset, make_nifti, tmp_path, monkeypatch):
    monkeypatch.setattr(report, "default_path_patterns", None)
    tpl_path = make_nifti(tmp_path / "tpl" / "tpl.nii.gz")
    tpl_mask = make_nifti(tmp_path / "tpl" / "mask.nii.gz", value=1)
    mocker.patch.object(workflow, "get_template", return_value=(tpl_path, tpl_mask, None))

    def fake_registration(ref, moving, **kwargs):
        return {"fwdtransforms": [_identity_itk_transform(tmp_path / "fwd.mat")]}

    registration = mocker.patch.object(workflow, "registration_antspy", side_effect=fake_registration)
    mocker.patch("skullduggery.mask.registration_antspy", side_effect=fake_registration)
    mosaic = mocker.patch.object(workflow, "generate_deface_mosaic_report")
    report_mock = mocker.patch.object(workflow, "generate_report", return_value=tmp_path / "report.html")

    layout = bids.BIDSLayout(bids_dataset, validate=False)
    return SimpleNamespace(
        layout=layout,
        root=bids_dataset,
        registration=registration,
        mosaic=mosaic,
        report=report_mock,
        tpl_path=tpl_path,
    )


def test_compose_transform_chain_single_transform_is_returned_as_is():
    tx = nt.linear.Affine(np.eye(4))
    assert _compose_transform_chain(None, tx, None) is tx


def test_compose_transform_chain_flattens_nested_chains():
    a = nt.linear.Affine(np.eye(4))
    b = nt.linear.Affine(np.eye(4))
    c = nt.linear.Affine(np.eye(4))
    chain = _compose_transform_chain(nt.manip.TransformChain([a, b]), c)
    assert isinstance(chain, nt.manip.TransformChain)
    assert list(chain.transforms) == [a, b, c]


def test_compose_transform_chain_requires_one_transform():
    with pytest.raises(ValueError, match="at least one transform"):
        _compose_transform_chain(None, None)


def test_deface_workflow_defaces_reference_and_other_series(workflow_env):
    env = workflow_env
    result = deface_workflow(env.layout, _args())

    assert result is True
    anat = env.root / "sub-01" / "anat"
    assert (anat / "sub-01_from-T1w_to-MNIInfant_xfm.mat").exists()
    assert (anat / "sub-01_space-T1w_desc-deface_mask.nii.gz").exists()
    assert not (anat / "sub-01_space-T2w_desc-deface_mask.nii.gz").exists()

    mask = np.asanyarray(nb.load(anat / "sub-01_space-T1w_desc-deface_mask.nii.gz").dataobj)
    for name in ("sub-01_T1w.nii.gz", "sub-01_T2w.nii.gz"):
        masked = np.asanyarray(nb.load(anat / name).dataobj)
        assert masked.shape == (8, 8, 8)
        assert np.all(masked[mask == 0] == 0)

    assert env.mosaic.call_count == 2
    env.report.assert_called_once()
    assert env.report.call_args.kwargs == {"subject": "01", "session": None}


def test_deface_workflow_saves_masks_for_every_series(workflow_env):
    env = workflow_env
    deface_workflow(env.layout, _args(save_all_masks=True))
    assert (env.root / "sub-01" / "anat" / "sub-01_space-T2w_desc-deface_mask.nii.gz").exists()


def test_deface_workflow_reuses_existing_registration_matrix(workflow_env):
    env = workflow_env
    deface_workflow(env.layout, _args())
    deface_workflow(env.layout, _args())

    assert env.registration.call_count == 1


def test_deface_workflow_uses_default_age_when_participants_lack_age(workflow_env):
    env = workflow_env
    (env.root / "participants.tsv").write_text("participant_id\tsex\nsub-01\tF\n")
    get_template = workflow.get_template

    deface_workflow(env.layout, _args(default_age=(2.0, "years")))

    assert get_template.call_args_list[-1].kwargs["age"] == (2.0, "years")


def test_deface_workflow_returns_false_without_reference_image(workflow_env):
    assert deface_workflow(workflow_env.layout, _args(participant_label="99")) is False


def test_deface_workflow_datalad_flag_requires_datalad(workflow_env, monkeypatch):
    monkeypatch.setattr(workflow, "datalad", None)
    with pytest.raises(ImportError, match="datalad is required"):
        deface_workflow(workflow_env.layout, _args(datalad=True))


def test_deface_workflow_deface_sensitive_skips_series_without_restrictions(workflow_env, monkeypatch):
    env = workflow_env
    repo = SimpleNamespace(
        get_metadata=lambda path: iter([(path, {})]),
        set_metadata=lambda files, remove: setattr(repo, "last_set", (files, remove)),
    )
    dataset = SimpleNamespace(repo=repo)
    monkeypatch.setattr(workflow, "datalad", SimpleNamespace(api=SimpleNamespace(Dataset=lambda path: dataset)))

    result = deface_workflow(env.layout, _args(deface_sensitive=True))

    assert result is True
    assert repo.last_set == ([], {"distribution-restrictions": "sensitive"})
    assert env.mosaic.call_count == 0
    assert not (env.root / "sub-01" / "anat" / "sub-01_space-T1w_desc-deface_mask.nii.gz").exists()


def test_deface_workflow_datalad_fetches_unlocks_and_saves(workflow_env, monkeypatch):
    env = workflow_env
    calls = []

    class FakeRepo:
        def unlock(self, paths):
            calls.append(("unlock", sorted(paths)))

        def set_metadata(self, files, remove):
            calls.append(("set_metadata", files, remove))

    class FakeDataset:
        def __init__(self, path):
            self.repo = FakeRepo()

        def get(self, paths):
            calls.append(("get", paths))

        def save(self, files, message):
            calls.append(("save", files, message))

    monkeypatch.setattr(workflow, "datalad", SimpleNamespace(api=SimpleNamespace(Dataset=FakeDataset)))

    assert deface_workflow(env.layout, _args(datalad=True)) is True

    kinds = [call[0] for call in calls]
    assert kinds[0] == "get"
    assert "unlock" in kinds
    save = next(call for call in calls if call[0] == "save")
    assert "2 series/images" in save[2]
    assert calls[-1][0] == "set_metadata"
    assert calls[-1][2] == {"distribution-restrictions": "sensitive"}
