"""TR's validate() reports the files the preparation reads, and the run names them (task-web-client #201).

``tr_set_metric`` (``tr/trmetric.f90``) loads ``KNAMEQ`` for ``MODELG`` 3, 5 and 8 (equnit's ``eq_load``) and
7 (``pl_vmec``, the VMEC reader), and for ``MODELG`` 8 ``KNAMEQ2`` too, which ``tr_set_param_str`` does not
set (it stays the namelist's, blank by default). ``validate()`` reports each as ``FILE_MISSING`` when it is
blank or names no file, as EQ's ``validate()`` does since task-web-client #191, and ``KNAMEQ2`` when blank
(``eq:KNAMEQ2`` is refused: TR hands EQ its own). Before: a blank ``KNAMEQ`` only; a ``KNAMEQ`` that named no
file validated clean, and with ``MODELG`` 7 the run then completed with non-finite results, ``pl_vmec``'s
error being overwritten by the next call. Now that run fails, and the failure record of a run that cannot
load its file names it, within the 102 characters of detail that ``tr_last_error``'s 127 leave.

Each case runs in a scratch directory, the working directory the run opens its file from.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from trlib import Trlib, TrDiagCode, TrlibParamError, TrlibRunError

_HERE = Path(__file__).resolve()
_DEFAULT_SO = _HERE.parents[3] / "tr" / "libtrapi.so"
_TST2 = _HERE.parent / "fixtures" / "eqdata.TST-2"

pytestmark = pytest.mark.skipif(
    not Path(os.environ.get("TRLIB_PATH") or _DEFAULT_SO).exists(),
    reason="libtrapi.so not built",
)

KNAMEQ_MODELS = (3, 5, 7, 8)


@pytest.fixture(autouse=True)
def _in_tmp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def _file_missing(modelg, knameq=None, files=()):
    for name in files:
        shutil.copy(_TST2, name)
    with Trlib() as tr:
        tr.set_param("MODELG", float(modelg))
        if knameq is not None:
            tr.set_param_str("KNAMEQ", knameq)
        return [(d.param, d.message) for d in tr.validate() if d.code == TrDiagCode.FILE_MISSING]


_KNAMEQ2_BLANK = ("KNAMEQ2", "MODELG=8 loads the file KNAMEQ2 names too, and KNAMEQ2 is blank"
                             " (neither tr_set_param_str nor eq:KNAMEQ2 sets it)")


@pytest.mark.parametrize("modelg", KNAMEQ_MODELS)
def test_a_blank_knameq_is_reported(modelg):
    expected = [("KNAMEQ", f"MODELG={modelg} loads the file KNAMEQ names, and KNAMEQ is blank")]
    assert _file_missing(modelg, "") == expected + ([_KNAMEQ2_BLANK] if modelg == 8 else [])


@pytest.mark.parametrize("modelg", KNAMEQ_MODELS)
def test_a_knameq_that_names_no_file_is_reported(modelg):
    expected = [("KNAMEQ", f"KNAMEQ='nofile.dat' not found: MODELG={modelg} loads it")]
    assert _file_missing(modelg, "nofile.dat") == expected + ([_KNAMEQ2_BLANK] if modelg == 8 else [])


def test_the_default_knameq_is_looked_up_too():
    # tr_init leaves KNAMEQ='eqdata', which a fresh folder does not hold.
    assert _file_missing(3) == [("KNAMEQ", "KNAMEQ='eqdata' not found: MODELG=3 loads it")]


@pytest.mark.parametrize("modelg", (3, 5, 7))
def test_a_knameq_that_is_there_is_clean(modelg):
    assert _file_missing(modelg, "eqdata.TST-2", files=["eqdata.TST-2"]) == []


def test_modelg_8_reads_knameq2_too_which_tr_cannot_set():
    # The other formats read KNAMEQ only; TR's KNAMEQ2 is the namelist's, blank.
    assert _file_missing(8, "eqdata.TST-2", files=["eqdata.TST-2"]) == [_KNAMEQ2_BLANK]


def test_the_longest_knameq_is_named_whole():
    name = "k" * 80   # KNAMEQ holds 80 characters
    assert _file_missing(5, name) == [("KNAMEQ", f"KNAMEQ='{name}' not found: MODELG=5 loads it")]


@pytest.mark.parametrize("modelg", (0, 1, 2, 9))
def test_a_model_that_loads_no_file_does_not_look_for_one(modelg):
    assert _file_missing(modelg, "nofile.dat") == []
    assert _file_missing(modelg, "") == []


@pytest.mark.forked
def test_eq_knameq2_is_refused_before_the_first_run_too():
    # tr_set_metric hands EQ TR's own KNAMEQ2 under MODELG 8, which overwrote an eq:KNAMEQ2 set.
    with Trlib() as tr:
        with pytest.raises(TrlibParamError):
            tr.set_param_str("eq:KNAMEQ2", "jaea2.dat")


def _run_failure(modelg, knameq):
    with Trlib() as tr:
        tr.set_param("MODELG", float(modelg))
        tr.set_param_str("KNAMEQ", knameq)
        tr.set_param("NTMAX", 2.0)
        with pytest.raises(TrlibRunError) as err:
            tr.run(2)
    return err.value.failure


@pytest.mark.parametrize("name", ["nofile.dat", "v" * 61], ids=["short", "61 characters"])
def test_modelg_7_with_no_vmec_file_fails_and_names_it(name):
    # pl_vmec's error was overwritten by tr_bpsd_get's, and the run completed with non-finite results. The name
    # comes last in the detail: 61 characters of it fit whole.
    failure = _run_failure(7, name)
    assert failure is not None
    assert (failure.kind, failure.code, failure.nt) == ("PREP_FAILED", 7, 0)
    assert failure.detail == f"pl_vmec (ierr=7) could not open KNAMEQ='{name}'"


@pytest.mark.parametrize("modelg, name", [(3, "nofile.dat"), (5, "nofile.dat"), (3, "e" * 43)],
                         ids=["3", "5", "3, 43 characters"])
def test_a_load_that_finds_no_file_names_it(modelg, name):
    # The record was PREP_FAILED "tr_prep failed"; now EQ_FAILED with EQ_READ's reason, whole up to a
    # 43-character name.
    failure = _run_failure(modelg, name)
    assert failure is not None
    assert (failure.kind, failure.nt) == ("EQ_FAILED", 0)
    assert failure.detail == f"eq_load: EQ_READ: MODELG={modelg} load failed: KNAMEQ='{name}' not found"


def test_a_longer_name_is_cut_with_the_record():
    # tr_last_error keeps 127 characters, 102 of them detail; validate() names the 80 characters whole.
    name = "k" * 80
    failure = _run_failure(3, name)
    assert len(failure.detail) == 102
    assert failure.detail == f"eq_load: EQ_READ: MODELG=3 load failed: KNAMEQ='{name}"[:102]


def test_modelg_8_fails_on_its_blank_second_file(tmp_path):
    # A first file in EQJAEAR's layout (the grid counts, the box, psi, BtR) gets the load to KNAMEQ2, which
    # TR cannot set.
    import struct

    def rec(b):
        return struct.pack("<i", len(b)) + b + struct.pack("<i", len(b))
    (tmp_path / "jaea.dat").write_bytes(
        rec(struct.pack("<2i", 3, 3)) + rec(struct.pack("<4d", 0.1, 0.5, -0.3, 0.3))
        + rec(struct.pack("<9d", *([0.0] * 9))) + rec(struct.pack("<d", 1.0)))
    assert _file_missing(8, "jaea.dat") == [_KNAMEQ2_BLANK]
    failure = _run_failure(8, "jaea.dat")
    assert (failure.kind, failure.nt) == ("EQ_FAILED", 0)
    assert failure.detail == "eq_load: EQ_READ: MODELG=8 load failed: its second file KNAMEQ2 is blank"
