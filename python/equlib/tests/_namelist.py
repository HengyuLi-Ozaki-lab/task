"""A reader of the &EQU namelist files of equ/example, for replaying them
through ``Equ.set_params`` (the parity test's second route).

It handles what those files use: ``NAME = v``, ``NAME = v1, v2, ...``
(consecutive elements from the array's lower bound), ``NAME(i) = v`` and
``NAME(i) = v1, v2`` (from element i), quoted strings, ``D`` exponents,
several assignments on a line, the ``&EQU`` ... ``&END`` frame. Later
assignments of a name win, as in a namelist read.
"""
from __future__ import annotations

import re
from pathlib import Path

LOWER = {"IVAC": 0, "NCOIL": 0, "CVAC": 0, "CVACST": 0, "CVACWG": 0, "CVACT": 0,
         "RVAC": 0, "ZVAC": 0, "ICP": 1, "CP": 1, "IEQOUT": 1}
STRINGS = {"DEVICE", "DEVNAM", "TITLE", "KNAMCOIL"}

_ASSIGN = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*(?:\(\s*(\d+)\s*\))?\s*=")


def read_equ_namelist(path: str | Path) -> list[tuple[str, object]]:
    text = Path(path).read_text()
    start = re.search(r"&equ\b", text, re.IGNORECASE)
    end = re.search(r"&end\b|/", text[start.end():], re.IGNORECASE)
    body = text[start.end(): start.end() + end.start()]
    matches = list(_ASSIGN.finditer(body))
    out: list[tuple[str, object]] = []
    for k, m in enumerate(matches):
        name = m.group(1).upper()
        stop = matches[k + 1].start() if k + 1 < len(matches) else len(body)
        raw = body[m.end():stop]
        if name in STRINGS:
            out.append((name, re.search(r"'([^']*)'", raw).group(1)))
            continue
        values = [v.strip() for v in raw.split(",") if v.strip()]
        nums = [float(v.replace("D", "E").replace("d", "e")) for v in values]
        if name in LOWER:
            first = int(m.group(2)) if m.group(2) is not None else LOWER[name]
            out.extend((f"{name}[{first + j}]", v) for j, v in enumerate(nums))
        else:
            assert len(nums) == 1 and m.group(2) is None, (name, raw)
            out.append((name, nums[0]))
    return out
