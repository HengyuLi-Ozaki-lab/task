"""eqlib.Eq.save() - file coupling smoke test."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

import eqlib

_HERE = Path(__file__).resolve()
_DEFAULT_SO = _HERE.parents[3] / "eq" / "libeqapi.so"


def _resolved_so() -> Path:
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    return _DEFAULT_SO


@pytest.mark.skipif(not _resolved_so().exists(), reason="libeqapi.so not built")
def test_save_creates_file():
    with tempfile.TemporaryDirectory() as workdir:
        path = os.path.join(workdir, "eq.bin")
        with eqlib.Eq() as e:
            e.save(path)
        assert os.path.isfile(path), f"expected file at {path}"
        assert os.path.getsize(path) > 0, "file is empty"


@pytest.mark.skipif(not _resolved_so().exists(), reason="libeqapi.so not built")
def test_save_raises_when_directory_missing():
    """#227 item 3: a failed save must not be reported as a success.

    ``EQSAVE`` has no error out-argument and simply returns when ``FWOPEN``
    fails, so ``eq_api_save`` verifies the artefact instead of trusting the
    call. Before that fix this returned EQ_OK and produced no file.
    """
    path = "/nonexistent_dir_for_eq_save_test/eq.bin"
    with eqlib.Eq() as e:
        with pytest.raises(eqlib.EqlibError):
            e.save(path)
    assert not os.path.exists(path)


@pytest.mark.skipif(not _resolved_so().exists(), reason="libeqapi.so not built")
def test_save_rejects_blank_path():
    """A blank KNAMEQ can never produce a file; it must be an error."""
    with eqlib.Eq() as e:
        with pytest.raises(eqlib.EqlibError):
            e.save("")
