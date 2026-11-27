"""Quick start: the QUEST example of equ/example through equlib.

    PYTHONPATH=python python python/equlib/examples/quickstart.py [--dry-run]

Copies equparm.quest and coildata.quest into a temporary directory (the
namelist names its coil file 'coildata'), runs the menu's R (mode 1),
prints a few results and writes quest.geqdsk there. --dry-run only checks
that the wrapper imports and the example files exist.
"""
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[3] / "equ" / "example"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    from equlib import Equ
    if args.dry_run:
        assert (EXAMPLE / "equparm.quest").is_file() and (EXAMPLE / "coildata.quest").is_file()
        print("dry run: equlib imports; the QUEST example is in", EXAMPLE)
        return 0
    work = Path(tempfile.mkdtemp(prefix="equ-quest-"))
    shutil.copy(EXAMPLE / "equparm.quest", work / "equparm")
    shutil.copy(EXAMPLE / "coildata.quest", work / "coildata")
    os.chdir(work)
    with Equ() as equ:
        equ.read_parm("equparm")
        problems = equ.validate()
        if problems:
            for d in problems:
                print(f"{d.param}: {d.message}")
            return 1
        equ.run(1)
        st = equ.get_state()
        equ.write_geqdsk("quest.geqdsk")
    print(f"I_p = {st.ip:.4f} MA (target {st.ip_target} MA), q_axis = {st.q_axis:.4f}, "
          f"q95 = {st.q95:.3f}, R_axis = {st.raxis:.4f} m")
    print(f"FCT: {st.fct_steps} steps, converged = {bool(st.fct_converged)}, erreq = {st.erreq:.3e}")
    print("G-EQDSK:", work / "quest.geqdsk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
