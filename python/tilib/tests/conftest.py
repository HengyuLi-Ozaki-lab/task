"""pytest fixtures for tilib tests.

The ``ti`` module hard-codes two runtime data-file paths in
``ti/tiinit.f90``:

* ``adpost_dir`` = ``'../adpost/'`` + ``adpost_filename`` = ``'ADPOST-DATA'``
* ``adas_adf11_dir`` = ``'./'`` + ``adas_adf11_filename`` = ``'ADF11-bin.data'``

These are resolved relative to the process working directory at the time
of the first ``ti_run`` call (which triggers ``ti_prep`` inside
``libtiapi.so``). When tests are launched through
``test_run/run_tests.sh``, the harness symlinks the adpost directory
and optional ADF11 fixture into ``test_output/<test_name>/``, then
chdirs the binary into that directory (see the ``case ti)`` block in
``test_run/run_tests.sh``).

When pytest is launched directly (``pytest python/tilib/tests/...``)
no such setup exists, so every test that calls ``ti.run()`` fails with::

    XX FROPEN (ADPOST): FILE NOT FOUND: ../adpost/ADPOST-DATA

This conftest reproduces the run_tests.sh setup for pytest: per test it
chdirs the process into a fresh temp directory that looks like::

    <tmp>/
      adpost/ADPOST-DATA      -> <repo>/adpost/ADPOST-DATA           (if exists)
      work/                   <- cwd during the test
      work/ADF11-bin.data     -> <repo>/test_run/fixtures/ADF11-bin.data
                                 or <repo>/adpost/ADF11-bin.data      (if exists)

so the default ``'../adpost/ADPOST-DATA'`` resolves from ``work/`` and
``'./ADF11-bin.data'`` resolves in ``work/``. If a data source is
missing the symlink is skipped -- tiprep's IERR guard then fails the
test with a clear message (rather than a silent NaN).

Scope = function so each test sees a fresh cwd (and so process state
cannot leak across tests via the cwd).
"""
from __future__ import annotations

from pathlib import Path

import pytest


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]  # .../python/tilib/tests -> repo root

# Candidate data locations, mirroring ``test_run/run_tests.sh``.
ADPOST_SRC = REPO / "adpost" / "ADPOST-DATA"
ADF11_CANDIDATES = (
    REPO / "test_run" / "fixtures" / "ADF11-bin.data",
    REPO / "adpost" / "ADF11-bin.data",
    REPO / "open-adas" / "adf11" / "ADF11-bin.data",
)


def _first_existing(paths):
    """Return the first existing path from ``paths`` or ``None``."""
    for p in paths:
        if p.exists():
            return p
    return None


@pytest.fixture(autouse=True)
def _ti_data_cwd(tmp_path, monkeypatch):
    """Chdir each test into a tmp dir that exposes TI's runtime data.

    Always active (autouse). Tests that do not exercise ``libtiapi.so``
    simply chdir and see an empty workspace -- harmless. Tests that do
    call ``ti.run()`` find ``../adpost/ADPOST-DATA`` and (optionally)
    ``./ADF11-bin.data`` where the library expects them.

    Missing data files are not fatal: tiprep in ``ti/tiprep.f90``
    returns IERR=1 with a clear message so the test fails loudly rather
    than silently mis-computing.
    """
    # Layout: <tmp>/adpost/, <tmp>/work/
    adpost_dir = tmp_path / "adpost"
    work_dir = tmp_path / "work"
    adpost_dir.mkdir()
    work_dir.mkdir()

    # Expose adpost/ADPOST-DATA when the real file is present in the
    # repo (it is committed -- see adpost/ADPOST-DATA).
    if ADPOST_SRC.exists():
        (adpost_dir / "ADPOST-DATA").symlink_to(ADPOST_SRC)

    # Expose ADF11-bin.data in cwd when any candidate source exists.
    # PR #112 committed a synthetic fixture at test_run/fixtures/; real
    # ADAS data at adpost/ADF11-bin.data is also accepted.
    adf11_src = _first_existing(ADF11_CANDIDATES)
    if adf11_src is not None:
        (work_dir / "ADF11-bin.data").symlink_to(adf11_src)

    monkeypatch.chdir(work_dir)
    yield
    # monkeypatch reverts cwd automatically on teardown.
