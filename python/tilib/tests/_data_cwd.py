"""Mixin that gives a ``unittest.TestCase`` the ADPOST/ADF11 data cwd.

The ``ti`` module hard-codes two runtime data-file paths in
``ti/tiinit.f90``:

* ``adpost_dir`` = ``'../adpost/'`` + ``adpost_filename`` = ``'ADPOST-DATA'``
* ``adas_adf11_dir`` = ``'./'`` + ``adas_adf11_filename`` = ``'ADF11-bin.data'``

Both are resolved against the process working directory at the time
``ti_run`` first triggers ``ti_prep`` inside ``libtiapi.so``. The
``test_run/run_tests.sh`` harness wires this up by symlinking
``adpost`` next to ``test_output/<test_name>/`` and chdir-ing the
binary into that directory (see the ``case ti)`` block).

When the test suite is launched a different way -- for example::

    python3 -m unittest -v tilib.tests.test_equivalence
    pytest python/tilib/tests/test_equivalence.py

-- nothing arranges that layout, so every test that calls ``ti.run()``
fails with::

    XX FROPEN (ADPOST): FILE NOT FOUND: ../adpost/ADPOST-DATA

PR #115 added a pytest-only ``conftest.py`` autouse fixture, which
covers ``pytest`` invocation but does nothing under ``python3 -m
unittest`` because plain ``unittest`` ignores ``conftest.py``.

This mixin gives ``unittest.TestCase`` subclasses the same per-test
cwd setup as the conftest fixture, while remaining compatible with
``pytest`` (pytest also drives ``setUp`` / ``tearDown`` for
``TestCase`` subclasses, so the mixin "just works" in both runners
and the ``conftest.py`` autouse fixture becomes redundant).

Layout created in :py:meth:`TiDataCwdMixin.setUp`::

    <tmp>/
      adpost/ADPOST-DATA      -> <repo>/adpost/ADPOST-DATA           (if exists)
      work/                   <- cwd during the test
      work/ADF11-bin.data     -> <repo>/test_run/fixtures/ADF11-bin.data
                                 or <repo>/adpost/ADF11-bin.data      (if exists)

Missing data sources are not fatal: tiprep in ``ti/tiprep.f90``
returns ``IERR=1`` with a clear message so the test fails loudly
rather than silently NaN-ing.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


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


class TiDataCwdMixin:
    """Mix into a ``unittest.TestCase`` to get a per-test data cwd.

    The mixin chains via ``super().setUp()`` / ``super().tearDown()``
    so subclasses may override either hook without losing the cwd
    setup -- as long as they call ``super()`` themselves.

    Co-operative multiple inheritance: list this mixin **before**
    ``unittest.TestCase`` in the MRO, e.g.::

        class TestEquivalence(TiDataCwdMixin, unittest.TestCase):
            ...

    so that ``super().setUp()`` from the mixin reaches
    ``TestCase.setUp`` (a no-op) instead of stopping at ``object``.
    """

    def setUp(self):  # noqa: D401 -- unittest hook
        # Track previous cwd so tearDown can restore it. We use
        # ``os.getcwd`` (not the stdlib ``Path.cwd``) because some CI
        # runners set the cwd to a path that no longer exists; getcwd
        # raises in that case which is the right behaviour.
        self.__ti_data_cwd_prev = os.getcwd()
        # Create the per-test tmp tree in a dedicated directory we
        # control, so tearDown can recursively delete it without
        # racing the tempfile module's cleanup.
        self.__ti_data_cwd_tmp = Path(tempfile.mkdtemp(prefix="tilib_test_"))

        adpost_dir = self.__ti_data_cwd_tmp / "adpost"
        work_dir = self.__ti_data_cwd_tmp / "work"
        adpost_dir.mkdir()
        work_dir.mkdir()

        # Expose adpost/ADPOST-DATA when the real file is present in
        # the repo (it is committed -- see adpost/ADPOST-DATA).
        if ADPOST_SRC.exists():
            (adpost_dir / "ADPOST-DATA").symlink_to(ADPOST_SRC)

        # Expose ADF11-bin.data in cwd when any candidate source
        # exists. PR #112 committed a synthetic fixture at
        # test_run/fixtures/; real ADAS data at adpost/ADF11-bin.data
        # is also accepted.
        adf11_src = _first_existing(ADF11_CANDIDATES)
        if adf11_src is not None:
            (work_dir / "ADF11-bin.data").symlink_to(adf11_src)

        os.chdir(work_dir)

        # Chain into the rest of the MRO (TestCase.setUp + any other
        # mixins to the right of this one).
        super().setUp()

    def tearDown(self):  # noqa: D401 -- unittest hook
        # Drain the rest of the MRO first so other tearDowns still
        # run inside the data cwd. Swallow no exceptions here -- the
        # tempdir cleanup below runs in a finally so it always fires.
        try:
            super().tearDown()
        finally:
            # Restore the prior cwd before nuking the tmpdir, so the
            # rmtree cannot fail with EBUSY on the cwd handle.
            try:
                os.chdir(self.__ti_data_cwd_prev)
            except OSError:
                # Prev cwd may have disappeared mid-test. Falling back
                # to the repo root keeps the process in a sane state.
                os.chdir(str(REPO))
            shutil.rmtree(self.__ti_data_cwd_tmp, ignore_errors=True)
