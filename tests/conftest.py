#   ---------------------------------------------------------------------------------
#   Copyright (c) <Your Name or Organization>. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json

import nibabel as nb
import numpy as np
import pytest
from _pytest.nodes import Item


def pytest_collection_modifyitems(items: list[Item]):
    for item in items:
        if "spark" in item.nodeid:
            item.add_marker(pytest.mark.spark)
        elif "_int_" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def unit_test_mocks(monkeypatch: None):
    """Include Mocks here to execute all commands offline and fast."""
    pass


@pytest.fixture
def sample_template_image():
    """Create a sample template image for testing."""
    shape = (256, 256, 256)
    affine = np.eye(4)
    data = np.ones(shape, dtype=np.uint8)
    return nb.Nifti1Image(data, affine)


@pytest.fixture
def make_nifti():
    def _make(path, shape=(8, 8, 8), value=None, affine=None):
        rng = np.random.default_rng(0)
        data = (
            rng.uniform(100, 1000, size=shape).astype(np.float32)
            if value is None
            else np.full(shape, value, np.float32)
        )
        image = nb.Nifti1Image(data, np.eye(4) if affine is None else affine)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.to_filename(path)
        return path

    return _make


@pytest.fixture
def bids_dataset(tmp_path, make_nifti):
    """Minimal BIDS dataset with one participant, a T1w and a T2w scan, and an age."""
    root = tmp_path / "bids"
    root.mkdir()
    (root / "dataset_description.json").write_text(
        json.dumps({"Name": "test", "BIDSVersion": "1.9.0", "DatasetType": "raw"})
    )
    (root / "participants.tsv").write_text("participant_id\tage\nsub-01\t30\n")
    (root / "participants.json").write_text(json.dumps({"age": {"Units": "months"}}))
    anat = root / "sub-01" / "anat"
    make_nifti(anat / "sub-01_T1w.nii.gz")
    make_nifti(anat / "sub-01_T2w.nii.gz")
    return root
