"""Run one TR case through trlib in a process of its own and write what it gives as JSON.

A helper of ``test_continue.py`` and ``test_continue_vs_tr2.py``: a Fortran ``STOP`` or a hang then ends this
child, not the test run, and every case starts in a fresh process (``eq:`` names are refused after a process's first
preparation, ``tr/tr_api.f90`` ``eq_name_refused``).

    python continue_runner.py <spec.json> <out.json>

spec (JSON)::

    {"cwd": "<dir>" or null,                 # MODELG 3 reads KNAMEQ's file from here
     "strings": [["KNAMEQ", "eqdata.ITER01"]],
     "params": [["MODELG", 3], ["PN[1]", 0.7], ["eq:RB", 2.1], ...],
     "calls": [{"call": "run" | "continue", "nsteps": 100, "set": [["PECTOT", 10.0]]}, ...],
     "history": true}                        # also write every history column

out (JSON): ``state`` (``TrState.to_dict()``), ``scalars`` (every named scalar), ``nt`` (after each call),
``history`` ({name: list}, when asked). The library's unit 6 goes to this process's stdout.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


def main(spec_path: str, out_path: str) -> int:
    from trlib import Trlib
    from trlib import _ffi

    spec = json.loads(Path(spec_path).read_text())
    lib = str(_ffi._default_lib_path().resolve())     # before the chdir: a relative TRLIB_PATH or MONO_LIB_PATH
    if spec.get("cwd"):
        os.chdir(spec["cwd"])
    out: dict = {"nt": []}
    with Trlib(lib) as t:
        for name, value in spec.get("strings", []):
            t.set_param_str(name, value)
        for name, value in spec.get("params", []):
            t.set_param(name, float(value))
        for c in spec["calls"]:
            for name, value in c.get("set", []):
                t.set_param(name, float(value))
            if c["call"] == "run":
                t.run(int(c["nsteps"]))
            else:
                t.continue_run(int(c["nsteps"]))
            out["nt"].append(t.get_state().nt)
        state = t.get_state()
        out["state"] = state.to_dict()
        out["scalars"] = dict(state.scalars)
        if spec.get("history"):
            out["history"] = {k: [float(x) for x in v] for k, v in t.history().items()}
    Path(out_path).write_text(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
