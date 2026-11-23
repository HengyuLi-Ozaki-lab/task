"""``tr_continue`` and the parameter classes (PR 3 of #96, Task 6 of the plan).

``tr_continue`` advances the prepared case by more steps without preparing again: it takes in the control parameters
set since the last call (``tr_param_class`` 1: RIPE, PNBTOT, PICTOT, PECTOT, PLHTOT, NTEQIT, TPRST) and runs the same
``tr_loop`` as ``tr_run``. It refuses (``TR_ERR_INVALID`` with a ``REFUSED`` record) before a preparation, after a
failed ``tr_run`` or ``tr_continue`` until a preparation, after a structural set (naming the last one), for a negative
count, and for a value ``tr_run``'s own checks refuse. The current ramp runs from RIPS to RIPE over the steps of one
call (``tr/trloop.f90``, ``DIPDT``).

A run in several calls is not bit-for-bit one call (the plan's findings F2): each call begins with ``tr_loop``'s
prologue. The last test measures that on the ITER ``MODELG`` 9 case and holds it to its size.

One test per case, no ``subTest``. A case that can fail inside Fortran runs in a child process.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
REPO = HERE.parents[3]
SERVERS_ROOT = PYTHON_ROOT / "mcp-servers"
RUNNER = HERE.parent / "continue_runner.py"

for _root in (PYTHON_ROOT, SERVERS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from trlib import Trlib, TrlibParamError, TrlibRunError  # noqa: E402
from trlib import _ffi as _tr_ffi  # noqa: E402
from trlib.tests.regrid_marks import NEEDS_BPSD_FIX  # noqa: E402

pytestmark = [
    pytest.mark.forked,
    pytest.mark.skipif(not _tr_ffi._default_lib_path().exists(),     # Trlib()'s own resolution: MONO_LIB_PATH,
                       reason=f"libtrapi.so not found at {_tr_ffi._default_lib_path()}"),   # TRLIB_PATH, tr/, lib/
]

CONTROL = {"RIPE", "PNBTOT", "PICTOT", "PECTOT", "PLHTOT", "NTEQIT", "TPRST"}


def _child(body: str) -> subprocess.CompletedProcess:
    code = (
        "import sys\nsys.path.insert(0, %r)\n" % str(PYTHON_ROOT)
        + "from trlib import Trlib, TrlibParamError, TrlibRunError\n"
        + textwrap.dedent(body)
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=600)


def _lines(p: subprocess.CompletedProcess, tag: str) -> list:
    return [line[len(tag) + 1:] for line in p.stdout.splitlines() if line.startswith(tag + " ")]


# ------------------------------------------------------------------ continuing

def test_continue_carries_t_and_nt_after_a_control_set():
    with Trlib() as t:
        t.run(10)
        s0 = t.get_state()
        t.set_param("PECTOT", 1.0)
        t.continue_run(10)
        s1 = t.get_state()
        assert s1.nt == s0.nt + 10 and s1.scalars["T"] > s0.scalars["T"]


def test_two_calls_ramp_to_each_ripe():
    # DIPDT is (RIPE - RIPS) over this call's steps: with NTMAX over the whole run the second call
    # reached 2 + 20/30 MA, not 3.
    with Trlib() as t:
        t.set_param("RIPS", 1.0); t.set_param("RIPE", 2.0)
        t.run(10)
        assert t.get_scalar("RIP") == pytest.approx(2.0, rel=1e-12)
        t.set_param("RIPE", 3.0)
        t.continue_run(20)
        assert t.get_scalar("RIP") == pytest.approx(3.0, rel=1e-12)


def test_a_zero_step_continue_keeps_a_pending_ripe():
    # tr_loop with no step leaves at once and sets RIPS = RIPE at its exit (tr/trloop.f90): the next call then had
    # DIPDT 0 and RIP = device%ip from bpsd, and stayed at 2 MA. tr_continue(0) checks and does nothing instead.
    with Trlib() as t:
        t.set_param("RIPS", 1.0); t.set_param("RIPE", 2.0)
        t.run(10)
        t.set_param("RIPE", 3.0)
        t.continue_run(0)
        t.continue_run(10)
        assert t.get_scalar("RIP") == pytest.approx(3.0, rel=1e-12)
        assert t.get_state().nt == 20


def test_a_zero_step_continue_takes_no_step():
    with Trlib() as t:
        t.run(10)
        before = (t.get_state().nt, t.get_scalar("T"), t.history_length())
        t.set_param("PECTOT", 1.0)
        t.continue_run(0)
        assert (t.get_state().nt, t.get_scalar("T"), t.history_length()) == before
        assert t.last_error().kind == "NONE"


def test_a_zero_step_continue_leaves_the_control_sets_pending():
    # Not taken in: tr_run, which prepares again after any set since its preparation, still sees the set.
    with Trlib() as t:
        t.run(5)
        t.set_param("PECTOT", 1.0)
        t.continue_run(0)
        t.run(5)
        assert t.get_state().nt == 5


def test_a_zero_step_continue_still_refuses_after_a_structural_set():
    with Trlib() as t:
        t.run(2)
        t.set_param("RR", 3.0)
        with pytest.raises(TrlibParamError) as e:
            t.continue_run(0)
        assert e.value.failure.kind == "REFUSED" and "RR" in e.value.failure.detail


def test_a_later_run_with_nothing_set_continues():
    with Trlib() as t:
        t.run(5); t.set_param("PECTOT", 1.0); t.continue_run(5)
        t.run(5)
        assert t.get_state().nt == 15


def test_a_run_after_a_control_set_still_prepares_again():
    # tr_run is unchanged: any set since its last preparation makes it prepare again (nt starts at 0).
    with Trlib() as t:
        t.run(5); t.set_param("PECTOT", 1.0)
        t.run(5)
        assert t.get_state().nt == 5


def test_continue_appends_to_the_history():
    with Trlib() as t:
        t.run(10)
        assert t.history_length() == 6          # t = 0, then one row per NGTSTP = 2 steps
        t.set_param("PECTOT", 1.0)
        t.continue_run(10)
        assert t.history_length() == 11
        times = list(t.history("T")["T"])
        assert all(b > a for a, b in zip(times, times[1:])), times


def test_a_good_continue_clears_the_record():
    with Trlib() as t:
        t.run(2)
        assert t._lib.tr_continue(-1) == 1 and t.last_error().kind == "REFUSED"
        t.continue_run(2)
        assert t.last_error().kind == "NONE"


# ------------------------------------------------------------------ refusals

def test_continue_refuses_after_a_structural_set_and_names_it():
    with Trlib() as t:
        t.run(10)
        t.set_param("RR", 3.0)
        with pytest.raises(TrlibParamError) as e:
            t.continue_run(5)
        assert t.last_error().kind == "REFUSED" and "RR" in t.last_error().detail
        assert e.value.failure == t.last_error()
        assert t.get_state().nt == 10


def test_the_refusal_names_the_last_structural_set():
    with Trlib() as t:
        t.run(2)
        t.set_param("RR", 3.0); t.set_param("PECTOT", 1.0); t.set_param("PN[2]", 0.3); t.set_param("PNBTOT", 1.0)
        with pytest.raises(TrlibParamError) as e:
            t.continue_run(1)
        assert "PN[2]" in e.value.failure.detail and "RR" not in e.value.failure.detail


def test_a_string_set_is_structural():
    with Trlib() as t:
        t.run(2)
        t.set_param_str("KNAMEQ", "eqdata.NOSUCH")
        with pytest.raises(TrlibParamError) as e:
            t.continue_run(1)
        assert "KNAMEQ" in e.value.failure.detail


def test_after_a_structural_refusal_run_prepares_and_continue_works():
    with Trlib() as t:
        t.run(10)
        t.set_param("RR", 3.0)
        with pytest.raises(TrlibParamError):
            t.continue_run(5)
        t.run(5)
        assert t.get_state().nt == 5            # prepared again
        t.continue_run(5)
        assert t.get_state().nt == 10 and t.last_error().kind == "NONE"


def test_continue_needs_a_prepared_state():
    with Trlib() as t, pytest.raises(TrlibParamError) as e:
        t.continue_run(1)
    assert e.value.failure.kind == "REFUSED" and "no prepared case" in e.value.failure.detail


def test_a_set_before_the_first_run_is_taken_in_by_the_preparation():
    with Trlib() as t:
        t.set_param("RR", 3.1); t.set_param("eq:NSGMAX", 64.0)
        t.run(2)
        t.continue_run(2)
        assert t.get_state().nt == 4


def test_continue_refuses_a_negative_count_with_a_record():
    with Trlib() as t:
        t.run(2)
        with pytest.raises(TrlibParamError) as e:     # trlib checks the count before the call
            t.continue_run(-1)
        assert e.value.failure is None
        assert t._lib.tr_continue(-1) == 1
        f = t.last_error()
        assert f.kind == "REFUSED" and "negative" in f.detail
        assert t.get_state().nt == 2


def test_continue_and_param_class_before_tr_init():
    # Raw library in a child: tr_continue is NOT_INIT (2) before tr_init; tr_param_class needs no init.
    p = _child('''
        from trlib import _ffi
        lib = _ffi.load_library()
        print("CONT", lib.tr_continue(1))
        print("CLASS", lib.tr_param_class(b"RIPE"), lib.tr_param_class(b"RR"), lib.tr_param_class(b"NOSUCH"))
    ''')
    assert _lines(p, "CONT") == ["2"], p.stdout[-800:] + p.stderr[-800:]
    assert _lines(p, "CLASS") == ["1 0 -1"]


def test_continue_refuses_after_a_failed_run_until_a_preparation():
    # DT = 100 s: TR_CHECK at nt 8 (test_loop_failures.py). A run with nothing set goes on as before and
    # prepares nothing; a run after a set prepares again, and then continue works. (Not DT = 1e6: after its
    # NONFINITE state a preparation in the same lifecycle fails NONFINITE again at nt 1, with or without tr_continue.)
    p = _child('''
        t = Trlib()
        t.set_param("DT", 100.0)
        try:
            t.run(30)
        except TrlibRunError as e:
            print("RUN", e.failure.kind)
        try:
            t.continue_run(1)
        except TrlibParamError as e:
            print("CONT1", e.failure.kind, e.failure.detail)
        t.run(0)
        try:
            t.continue_run(1)
        except TrlibParamError as e:
            print("CONT2", e.failure.kind, e.failure.detail)
        t.set_param("DT", 0.01)
        t.run(2)
        t.continue_run(2)
        print("NT", t.get_state().nt, t.last_error().kind)
    ''')
    assert _lines(p, "RUN") == ["TR_CHECK"], p.stdout[-1500:] + p.stderr[-1500:]
    for tag in ("CONT1", "CONT2"):
        got = _lines(p, tag)
        assert len(got) == 1 and got[0].startswith("REFUSED") and "failed" in got[0], (tag, p.stdout[-1500:])
    assert _lines(p, "NT") == ["4 NONE"]


def test_continue_refuses_after_a_failed_continue():
    # PECTOT 1e7 MW: NONFINITE at the first step of the continue (a control set that breaks the run).
    p = _child('''
        t = Trlib()
        t.run(2)
        t.set_param("PECTOT", 1.0e7)
        try:
            t.continue_run(5)
        except TrlibRunError as e:
            print("CONT1", e.failure.kind, e.failure.nt)
        try:
            t.continue_run(1)
        except TrlibParamError as e:
            print("CONT2", e.failure.kind, e.failure.detail)
    ''')
    assert _lines(p, "CONT1") == ["NONFINITE 3"], p.stdout[-1500:] + p.stderr[-1500:]
    got = _lines(p, "CONT2")
    assert len(got) == 1 and got[0].startswith("REFUSED") and "failed" in got[0], p.stdout[-1500:]


def test_continue_refuses_after_a_failed_preparation():
    # A good preparation, then a set that makes the next preparation fail (MODEL_PNF 5: set_usigmav_nf refuses it
    # inside tr_prep). The refusal says the run failed (the structural set alone would be refused too, with
    # another message).
    p = _child('''
        t = Trlib()
        t.run(2)
        t.set_param("MODEL_PNF", 5)
        try:
            t.run(1)
        except TrlibRunError as e:
            print("RUN", e.failure.kind)
        try:
            t.continue_run(1)
        except TrlibParamError as e:
            print("CONT", e.failure.kind, e.failure.detail)
    ''')
    assert len(_lines(p, "RUN")) == 1, p.stdout[-1500:] + p.stderr[-1500:]
    got = _lines(p, "CONT")
    assert len(got) == 1 and got[0].startswith("REFUSED") and "failed" in got[0], p.stdout[-1500:]


def test_continue_refuses_what_run_refuses():
    # tr_run refuses a negative current with MODELG 9 before the run (current_for_eq); RIPE is a control parameter,
    # so tr_continue asks the same checks.
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9)
        t.run(2)
        t.set_param("RIPE", -1.0)
        try:
            t.continue_run(1)
        except TrlibParamError as e:
            print("CONT", e.failure.kind, e.failure.detail)
        print("NT", t.get_state().nt)
    ''')
    got = _lines(p, "CONT")
    assert len(got) == 1 and got[0].startswith("REFUSED") and "RIPE" in got[0], p.stdout[-1500:] + p.stderr[-1500:]
    assert _lines(p, "NT") == ["2"]


# ------------------------------------------------------------------ classes

def test_param_class():
    with Trlib() as t:
        assert t.param_class("RIPE") == 1 and t.param_class("PNBTOT") == 1
        assert t.param_class("RR") == 0 and t.param_class("eq:RB") == 0
        assert t.param_class("NOSUCH") == -1


@pytest.mark.parametrize("name,cls", [
    ("MDLST", 0), ("PECR0", 0), ("NTMAX", 0), ("DT", 0), ("KNAMEQ", 0), ("PN[1]", 0), ("PSCTOT[3]", 0),
    ("NRMAX", 0), ("eq:NSGMAX", 0), ("TPRST", 1), ("NTEQIT", 1), ("PLHTOT", 1),
    ("", -1), ("eq:", -1), ("rr", -1), ("NOSUCH[1]", -1), ("PN[zz]", -1), (" eq:RB", -1), ("KNAMEQ[1]", -1), ("KNAMEQ[0]", -1),
    ("RIPE ", 1), (" RR", 0),   # the setter takes these: blanks around a name are not counted
])
def test_the_class_of_a_name(name, cls):
    with Trlib() as t:
        assert t.param_class(name) == cls


def _setter_names_in_the_source():
    """The names of the CASEs of tr_param_set_impl and tr_param_set_str_impl, and the names of KNOWN_NAMES."""
    source = (REPO / "tr" / "tr_param_registry.f90").read_text()

    def code(text):
        lines = [line.split("!", 1)[0].rstrip() for line in text.splitlines()]   # no name or selector holds a "!"
        return re.sub(r"&\s*\n\s*&?", " ", "\n".join(lines))

    def cases(text):
        names = set()
        for m in re.finditer(r"\bCASE\s*\(([^)]*)\)", text, flags=re.I):
            names.update(n.upper() for n in re.findall(r"""["']([A-Za-z_0-9]+)["']""", m.group(1)))
        return names

    def between(start, end):
        i = source.index(start)
        return code(source[i:source.index(end, i)])

    setter = cases(between("FUNCTION tr_param_set_impl(name, value)", "END FUNCTION tr_param_set_impl"))
    setter |= cases(between("FUNCTION tr_param_set_str_impl(name, value)", "END FUNCTION tr_param_set_str_impl"))
    known = between("KNOWN_NAMES(", "]")
    listed = {n.upper() for n in re.findall(r"""["']([A-Za-z_0-9]+)["']""", known)}
    return setter, listed


def test_the_known_names_are_the_cases_of_the_setter():
    """KNOWN_NAMES against the setter's CASEs, read from the source: a new CASE must be listed."""
    setter, listed = _setter_names_in_the_source()
    assert len(setter) == 90, sorted(setter)       # today's names: a new one changes the count here too
    assert {"NTEQIT", "TPRST", "NRMAX", "MDNCLS", "MDLEQB", "MDLPSC", "NSPSC", "KNAMEQ"} <= setter
    assert listed == setter, (sorted(listed - setter), sorted(setter - listed))
    assert CONTROL <= setter


def test_every_name_of_the_setter_has_its_class():
    setter, _ = _setter_names_in_the_source()
    with Trlib() as t:
        got = {n: t.param_class(n) for n in setter}
    wrong = {n: c for n, c in got.items() if c != (1 if n in CONTROL else 0)}
    assert not wrong, wrong


def test_every_name_the_mcp_server_declares_has_a_class():
    from tr_mcp.server import PARAMETER_REGISTRY
    with Trlib() as t:
        unknown = [n for n in PARAMETER_REGISTRY if t.param_class(n.split("[")[0]) < 0]
    assert not unknown, unknown


# ------------------------------------------------------------------ F2: several calls are not one call

# The ITER case of RESULTS section 5 under MODELG 9 with NTEQIT 50, at a flat 7 MA (the plan's chunk probe): a
# continue keeps RIPS = RIPE, so a ramp would differ by design.
ITER_M9_FLAT = [
    ["MODELG", 9], ["NTEQIT", 50], ["RR", 6.2], ["RA", 2.0], ["RKAP", 1.7], ["RDLT", 0.33], ["BB", 5.3],
    ["NSMAX", 4], ["PROFN2", 0.15], ["MDLNF", 1], ["DT", 0.02], ["NTSTEP", 250], ["RIPS", 7.0], ["RIPE", 7.0],
    ["PN[1]", 0.7], ["PN[2]", 0.315], ["PN[3]", 0.315], ["PN[4]", 0.035],
    ["PNS[1]", 0.1], ["PNS[2]", 0.045], ["PNS[3]", 0.045], ["PNS[4]", 0.005],
    ["PT[1]", 1.0], ["PT[2]", 1.0], ["PT[3]", 1.0], ["PT[4]", 1.0],
    ["PTS[1]", 0.1], ["PTS[2]", 0.1], ["PTS[3]", 0.1], ["PTS[4]", 0.1],
    ["eq:RB", 2.1], ["eq:NSGMAX", 128],
]


def _run_case(spec: dict, tmp: Path, tag: str) -> subprocess.Popen:
    (tmp / f"{tag}.json").write_text(json.dumps(spec))
    return subprocess.Popen([sys.executable, str(RUNNER), str(tmp / f"{tag}.json"), str(tmp / f"{tag}.out.json")],
                            stdout=open(tmp / f"{tag}.log", "w"), stderr=subprocess.STDOUT)


@NEEDS_BPSD_FIX
def test_aligned_calls_differ_from_one_call_by_less_than_1e_7():
    """Measured 1.4e-12 (WPT) and 1.3e-13 (Q0) with calls of 100 steps under NTEQIT 50; this test holds them to 1e-7.

    Gated on TRLIB_BPSD_REGRID_FIX=1: on a bpsd without k-yoshimi/bpsd#7 EQ's plasma point count can grow between
    the NTEQIT re-solves and overrun bpsd's splines without a message, and the comparison is not defined there.

    The history agrees at single precision, except on the row after each cut: there WPDOT, TAUE2 and H98Y2 differ
    (the call's first TRGLOB re-anchors WPPRE/TPRE on the WPT of the re-solved equilibrium; the plan's "F2,
    extended").
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        one = {"params": ITER_M9_FLAT, "calls": [{"call": "run", "nsteps": 300}], "history": True}
        cut = {"params": ITER_M9_FLAT, "history": True,
               "calls": [{"call": "run", "nsteps": 100}, {"call": "continue", "nsteps": 100},
                         {"call": "continue", "nsteps": 100}]}
        procs = {"one": _run_case(one, tmp, "one"), "cut": _run_case(cut, tmp, "cut")}
        for tag, p in procs.items():
            assert p.wait(timeout=600) == 0, (tmp / f"{tag}.log").read_text()[-2000:]
        a, b = (json.loads((tmp / f"{tag}.out.json").read_text()) for tag in ("one", "cut"))
    assert a["state"]["NT"] == b["state"]["NT"] == 300
    for name in ("WPT", "Q0"):
        x, y = a["scalars"][name], b["scalars"][name]
        assert abs(x - y) <= 1e-7 * abs(x), (name, x, y)
    ha, hb = a["history"], b["history"]
    assert len(ha["T"]) == len(hb["T"]) == 151 and ha["T"] == hb["T"]
    after_cut = {ha["T"].index(min(t for t in ha["T"] if t > 100 * 0.02 + 1e-9)),
                 ha["T"].index(min(t for t in ha["T"] if t > 200 * 0.02 + 1e-9))}
    bad = []
    for name, col in ha.items():
        scale = max(abs(v) for v in col) or 1.0
        for i, (x, y) in enumerate(zip(col, hb[name])):
            if i in after_cut and name in ("WPDOT", "TAUE2", "H98Y2"):
                continue
            if abs(x - y) > 1e-6 * max(abs(x), abs(y)) + 1e-7 * scale:
                bad.append((name, i, x, y))
    assert not bad, bad[:20]
