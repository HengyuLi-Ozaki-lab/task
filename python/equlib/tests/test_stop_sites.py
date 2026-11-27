"""The STOP statements left in equ/ are off the library's path.

Each one, with the routine around it, must be in KNOWN: routines the
library never calls (dead code, the menu's CSV reader, the program's end)
and equ_fail, which stops only outside library mode. A new STOP elsewhere
fails this test, so a process-ending statement cannot reach the library's
path unseen (design 2026-11-22, section 9.2).
"""
from __future__ import annotations

import re
from pathlib import Path

EQU = Path(__file__).resolve().parents[3] / "equ"
KNOWN = {
    ("equsub.f90", "eqdsk0"),            # never called
    ("equinp.f90", "eqinp"),             # never called
    ("equinp.f90", "eqrest"),            # never called
    ("equtrsvq.f90", "trsvq"),           # not compiled
    ("equ_convert.f90", "equ_read_gfile_csv"),  # the menu's Z only
    ("equmain.f90", "equ"),              # the program's end
    ("equ_status.f90", "equ_fail"),      # stops outside library mode only
}
_UNIT = re.compile(r"^\s*(?:end\s+)?(subroutine|function|program)\s+([a-z0-9_]+)", re.I)


def _stops():
    found = set()
    for path in sorted(EQU.glob("*.f90")):
        unit = None
        for line in path.read_text(errors="replace").splitlines():
            code = line.split("!", 1)[0]
            m = _UNIT.match(code)
            if m and not code.strip().lower().startswith("end"):
                unit = m.group(2).lower()
            if re.search(r"(^|[\s;)])stop\b", code, re.I) and not re.search(r"'[^']*stop", code, re.I):
                found.add((path.name, unit))
    return found


def test_stops_are_known():
    assert _stops() <= KNOWN, sorted(_stops() - KNOWN)


def test_the_list_is_not_stale():
    assert KNOWN <= _stops(), sorted(KNOWN - _stops())
