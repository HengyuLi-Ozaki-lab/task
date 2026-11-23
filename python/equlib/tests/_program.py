"""Run the EQU program without graphics (``equ/equ_nogr``) on an example case.

``make -C equ equ_nogr`` builds it: the program ``equ`` linked with no-op GSAF
entries, so it reads its menu commands from standard input at once. The
cases are the examples of ``equ/example``, copied into a working directory
under the names their ``&EQU`` namelist expects (``KNAMCOIL`` is relative).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXAMPLE = REPO / "equ" / "example"
PROGRAM = REPO / "equ" / "equ_nogr"

# case -> (namelist file, coil file, name the namelist's KNAMCOIL gives it)
CASES = {
    "quest": ("equparm.quest", "coildata.quest", "coildata"),
    "iter01": ("equparm.ITER#1", "coildata.ITER#1", "coildata.ITER#1"),
}


def stage(case: str, workdir: str | Path) -> Path:
    """Copy the case's files into ``workdir``; return the namelist's path."""
    parm, coil, coil_as = CASES[case]
    workdir = Path(workdir)
    shutil.copy(EXAMPLE / parm, workdir / "equparm")
    shutil.copy(EXAMPLE / coil, workdir / coil_as)
    return workdir / "equparm"


def program_geqdsk(case: str, workdir: str | Path, out: str = "prog.geqdsk") -> Path:
    """Run ``R`` then ``E`` in the program on the case; return the G-EQDSK."""
    workdir = Path(workdir)
    stage(case, workdir)
    r = subprocess.run([str(PROGRAM)], cwd=workdir, input=f"R\nE\n{out}\nQ\n",
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (r.stdout[-2000:], r.stderr[-2000:])
    path = workdir / out
    assert path.is_file() and path.stat().st_size > 0, r.stdout[-2000:]
    return path
