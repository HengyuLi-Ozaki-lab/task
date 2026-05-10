"""eqlib.Eq.save() - file coupling smoke test."""
from __future__ import annotations

import os
import tempfile

import pytest

import eqlib


@pytest.mark.skipif(not os.environ.get("EQLIB_PATH"), reason="needs EQLIB_PATH")
def test_save_creates_file():
    with tempfile.TemporaryDirectory() as workdir:
        path = os.path.join(workdir, "eq.bin")
        with eqlib.Eq() as e:
            e.save(path)
        assert os.path.isfile(path), f"expected file at {path}"
        assert os.path.getsize(path) > 0, "file is empty"
