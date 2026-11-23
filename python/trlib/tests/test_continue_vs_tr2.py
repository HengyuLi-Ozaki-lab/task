"""``tr_continue`` against the product ``tr2``'s ``C``, one control parameter at a time, at 1e-10.

For each control parameter (``tr_param_class`` 1) a two-stage case runs twice:

- ``tr2``: the namelist, ``r`` (``NTMAX`` = n1 steps), the change and ``NTMAX`` = n2, ``c``, ``q``, with
  ``TR_REGRESS_DUMP=1``: ``tr_regress.dat`` holds the state ``tr_loop`` leaves after ``c``;
- the library: the same names through ``set_param``, ``run(n1)``, the change, ``continue_run(n2)``.

The dump goes through ``test_run/scripts/extract_tr_metrics.py`` and is compared with ``TrState.to_dict()`` by
``test_run/scripts/compare_metrics.py`` at 1e-10, as the Layer 1 baselines are (``test_equivalence.py``). ``tr2``'s
``C`` starts ``NT`` at 0 again and the library counts on, so the dump's ``NT`` (n2) stands for n1 + n2. A third run,
``tr2`` without the change, must differ from the first: the change takes effect.

n1 is a multiple of ``NTSTEP``, ``NGTSTP``, ``NGRSTP`` and ``NTEQIT``, the step counts ``tr_loop`` and ``tr_eval``
compare ``NT`` with: ``tr2`` counts them from 0 in each ``C``, the library from the preparation.

The ``MODELG`` 3 cases are ``tr_iter01``'s (``fixtures/tr_iter01_params.py``, ``eqdata.ITER01``). ``NTEQIT`` and
``RIPE`` need ``MODELG`` 9 (under ``MODELG`` 3 the current profile comes from ``eqdata``): the ITER geometry of RESULTS
section 5, with ``eqparm`` RB 2.1 and NSGMAX 128 (``eq:RB`` and ``eq:NSGMAX`` for the library).

The last test documents where ``tr2``'s ``C`` is not a continuation: with NCLASS (``MDNCLS`` 1) its first step after
the cut takes the classical resistivity (``NT`` = 0 there, ``tr/trcoef_resistivity.f90:123``), and ``tr_continue``,
which counts on, equals one call instead.

Measured (macOS, -O0, -fcheck=all): every control case is bit-identical to ``tr2``'s ``C`` (largest relative
difference 0), and each change moves the state by 18 % to 100 % (``tr2`` with and without it).

Skipped when ``tr/tr2`` is not built. The fork's CI builds ``tr2`` in its "build modules not covered by pytest" job, not
in the pytest jobs, so there these tests skip: they are local evidence for the pull request.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
REPO = HERE.parents[3]
TR2 = REPO / "tr" / "tr2"
RUNNER = HERE.parent / "continue_runner.py"
FIXTURES_DIR = HERE.parent / "fixtures"
EXTRACT = REPO / "test_run" / "scripts" / "extract_tr_metrics.py"
COMPARE = REPO / "test_run" / "scripts" / "compare_metrics.py"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import _ffi as _tr_ffi  # noqa: E402

pytestmark = [
    pytest.mark.forked,
    pytest.mark.skipif(not TR2.exists(), reason=f"tr2 not built at {TR2} (make -C tr libs && make -C tr tr2)"),
    pytest.mark.skipif(not _tr_ffi._default_lib_path().exists(),     # Trlib()'s own resolution, as continue_runner's
                       reason=f"libtrapi.so not found at {_tr_ffi._default_lib_path()}"),
]


def _iter01():
    """tr_iter01's namelist as (strings, params), in the fixture's order."""
    from trlib.tests.fixtures import tr_iter01_params as f
    params = [[k, v] for k, v in f.SCALARS.items()]
    for k, arr in f.ARRAYS.items():
        params += [[f"{k}[{i}]", v] for i, v in enumerate(arr, start=1)]
    return [[k, v] for k, v in f.STRINGS.items()], params


def _iter_m9(nteqit: int):
    """The ITER case of RESULTS section 5 under MODELG 9 (ref-dee378ce/n50/tr.in), NTSTEP 50, and EQ's eqparm."""
    params = [["MODELG", 9], ["NTEQIT", nteqit], ["RR", 6.2], ["RA", 2.0], ["RKAP", 1.7], ["RDLT", 0.33], ["BB", 5.3],
              ["NSMAX", 4], ["PROFN2", 0.15], ["MDLNF", 1],
              ["PNBR0", 0.0], ["PNBRW", 1.0], ["PNBENG", 1000.0], ["PNBRTG", 6.2],
              ["PICCD", 0.1], ["PICR0", 0.0], ["PICRW", 0.2], ["PICNPR", 5.0],
              ["PECCD", 0.5], ["PECR0", 1.1], ["PECRW", 0.05], ["PECNPR", 5.0],
              ["PLHCD", 1.0], ["PLHR0", 0.8], ["PLHRW", 0.2], ["PLHNPR", 2.0],
              ["DT", 0.02], ["NTSTEP", 50], ["RIPS", 2.0], ["RIPE", 7.0]]
    for k, arr in dict(PN=[0.7, 0.315, 0.315, 0.035], PNS=[0.1, 0.045, 0.045, 0.005],
                       PT=[1.0] * 4, PTS=[0.1] * 4).items():
        params += [[f"{k}[{i}]", v] for i, v in enumerate(arr, start=1)]
    return [], params + [["eq:RB", 2.1], ["eq:NSGMAX", 128]]


def _value(v) -> str:
    return str(v) if isinstance(v, int) else repr(float(v))


def _namelist_line(name: str, v) -> str:
    return "   " + name.replace("[", "(").replace("]", ")") + "=" + _value(v)


def _write_tr2_case(d: Path, strings, params, n1, change, n2, with_change=True):
    """tr.in and, for eq: names, eqparm, in d."""
    d.mkdir()
    lines = [f"   {k}='{v}'" for k, v in strings]
    lines += [_namelist_line(k, v) for k, v in params if not k.startswith("eq:") and k != "NTMAX"]
    lines += [f"   NTMAX={n1}", "r"]
    lines += [_namelist_line(k, v) for k, v in change] if with_change else []
    lines += [f"   NTMAX={n2}", "c", "q"]
    (d / "tr.in").write_text("\n".join(lines) + "\n")
    eq = [f"   {k[3:]}={_value(v)}" for k, v in params if k.startswith("eq:")]
    if eq:
        (d / "eqparm").write_text(" &eq\n" + "\n".join(eq) + "\n &end\n")
    for k, v in strings:
        if k == "KNAMEQ":
            shutil.copy(FIXTURES_DIR / v, d / v)


# The time every process of one test shares, under the suite's 120 s pytest timeout (--timeout=120).
DEADLINE = 100.0


def _left(start: float) -> float:
    return max(1.0, start + DEADLINE - time.monotonic())


def _reap(procs) -> None:
    """Kill and wait for each process still running, so that a failed comparison or a timeout leaves none behind."""
    for p in procs:
        if p.poll() is None:
            p.kill()
        p.wait()


def _start_tr2(d: Path) -> subprocess.Popen:
    env = dict(os.environ, TR_REGRESS_DUMP="1")
    with open(d / "tr.in") as stdin, open(d / "out.txt", "w") as stdout:     # the child keeps its own descriptors
        return subprocess.Popen([str(TR2)], cwd=d, stdin=stdin, stdout=stdout, stderr=subprocess.STDOUT, env=env)


def _dump_json(d: Path, n1: int, n2: int) -> Path:
    """The dump of tr2 in d as the baseline JSON of extract_tr_metrics.py, its NT moved from n2 to n1 + n2."""
    res = subprocess.run([sys.executable, str(EXTRACT), str(d / "tr_regress.dat")], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    m = json.loads(res.stdout)
    assert m["NT"] == n2, (m["NT"], n2)       # tr2's C starts NT at 0
    m["NT"] = n1 + n2
    p = d / "metrics.json"
    p.write_text(json.dumps(m))
    return p


def _compare(baseline: Path, actual: Path, tol: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(COMPARE), "--baseline", str(baseline), "--actual", str(actual),
                           "--tolerance", tol], capture_output=True, text=True, timeout=60)


def _check(case, change, n1=100, n2=100):
    strings, params = case
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        _write_tr2_case(tmp / "tr2", strings, params, n1, change, n2)
        _write_tr2_case(tmp / "tr2_same", strings, params, n1, change, n2, with_change=False)
        start = time.monotonic()
        procs = {}
        try:
            for name in ("tr2", "tr2_same"):
                procs[name] = _start_tr2(tmp / name)
            api = tmp / "api"
            api.mkdir()
            for k, v in strings:
                if k == "KNAMEQ":
                    shutil.copy(FIXTURES_DIR / v, api / v)
            spec = {"cwd": str(api), "strings": strings, "params": params,
                    "calls": [{"call": "run", "nsteps": n1}, {"call": "continue", "nsteps": n2, "set": change}]}
            (tmp / "spec.json").write_text(json.dumps(spec))
            env = {k: v for k, v in os.environ.items() if k != "TR_REGRESS_DUMP"}
            res = subprocess.run([sys.executable, str(RUNNER), str(tmp / "spec.json"), str(tmp / "api.json")],
                                 capture_output=True, text=True, timeout=_left(start), env=env)
            assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
            for name, p in procs.items():
                assert p.wait(timeout=_left(start)) == 0, (name, (tmp / name / "out.txt").read_text()[-2000:])
        finally:
            _reap(procs.values())
        out = json.loads((tmp / "api.json").read_text())
        assert out["nt"] == [n1, n1 + n2]
        (tmp / "actual.json").write_text(json.dumps(out["state"]))
        same = _compare(_dump_json(tmp / "tr2", n1, n2), tmp / "actual.json", "1e-10")
        assert same.returncode == 0, same.stdout[-3000:]
        moved = _compare(_dump_json(tmp / "tr2_same", n1, n2), tmp / "actual.json", "1e-6")
        assert moved.returncode != 0, "the change made no difference: " + moved.stdout[-1000:]


def test_ripe():
    # MODELG 9: under MODELG 3 the current profile comes from eqdata and RIPE moves nothing in the state compared.
    # RIP ramps from 2 to 7 MA in the first stage and from 7 to 9 MA in the second.
    _check(_iter_m9(50), [["RIPE", 9.0]])


def test_pnbtot():
    _check(_iter01(), [["PNBTOT", 40.0]])


def test_pictot():
    _check(_iter01(), [["PICTOT", 10.0]])


def test_pectot():
    _check(_iter01(), [["PECTOT", 10.0]])


def test_plhtot():
    _check(_iter01(), [["PLHTOT", 10.0]])


def test_tprst():
    # MDLST 1 (structural, set before the run) flattens the temperature at each sawtooth; TPRST 10 s gives none in
    # these 4 s, TPRST 0.1 s a crash every 0.1 s of q(0) < 1 in the second stage.
    strings, params = _iter01()
    _check((strings, params + [["MDLST", 1], ["TPRST", 10.0]]), [["TPRST", 0.1]])


def test_nteqit():
    # Re-solves at steps 50 and 100, then at 125, 150, 175 and 200 (tr2: 25, 50, 75 and 100 of its C).
    _check(_iter_m9(50), [["NTEQIT", 25]])


def test_with_nclass_tr2_s_c_is_not_a_continuation():
    """With NCLASS (MDNCLS != 0), tr2's C differs from tr_continue, and tr_continue equals one call.

    tr2's C starts NT at 0 again, and TRCFET takes NCLASS's resistivity only when NT /= 0
    (tr/trcoef_resistivity.f90:123), so the first step after tr2's cut has the classical one; tr_continue counts NT on.
    Measured on tr_iter01 with nothing changed at the cut: 1.2e-4 (relative) from tr2's C, 5e-14 from one call. This
    test fails when either changes: then the control list's tests above may need MDNCLS cases.
    """
    strings, params = _iter01()
    params = params + [["MDNCLS", 1]]
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        _write_tr2_case(tmp / "tr2", strings, params, 100, [], 100)
        start = time.monotonic()
        env = {k: v for k, v in os.environ.items() if k != "TR_REGRESS_DUMP"}
        procs = []
        runs = {}
        try:
            proc = _start_tr2(tmp / "tr2")
            procs.append(proc)
            for tag, calls in (("cut", [{"call": "run", "nsteps": 100}, {"call": "continue", "nsteps": 100}]),
                               ("one", [{"call": "run", "nsteps": 200}])):
                d = tmp / tag
                d.mkdir()
                shutil.copy(FIXTURES_DIR / "eqdata.ITER01", d / "eqdata.ITER01")
                (d / "spec.json").write_text(json.dumps({"cwd": str(d), "strings": strings, "params": params,
                                                         "calls": calls}))
                with open(d / "log", "w") as log:
                    runs[tag] = subprocess.Popen([sys.executable, str(RUNNER), str(d / "spec.json"),
                                                  str(d / "out.json")], stdout=log, stderr=subprocess.STDOUT, env=env)
                procs.append(runs[tag])
            for tag, p in runs.items():
                assert p.wait(timeout=_left(start)) == 0, (tmp / tag / "log").read_text()[-2000:]
            assert proc.wait(timeout=_left(start)) == 0, (tmp / "tr2" / "out.txt").read_text()[-2000:]
        finally:
            _reap(procs)
        for tag in runs:
            (tmp / f"{tag}.json").write_text(json.dumps(json.loads((tmp / tag / "out.json").read_text())["state"]))
        assert _compare(tmp / "one.json", tmp / "cut.json", "1e-10").returncode == 0
        assert _compare(_dump_json(tmp / "tr2", 100, 100), tmp / "cut.json", "1e-6").returncode != 0
