#   ---------------------------------------------------------------------------------
#   Copyright (c) <Your Name or Organization>. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Pytest configuration and shared fixtures."""

from __future__ import annotations

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
