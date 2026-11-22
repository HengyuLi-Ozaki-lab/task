"""``Equ.validate``: one test per check of design section 8.

Each starts from the QUEST example (which validates clean), sets the input
that breaks one check, and looks for that check's entry: its parameter
name and diagnostic code. ``run`` refuses with the same checks.
"""
from __future__ import annotations

import pytest

from equlib import Equ, EqulibInvalidParamError
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib

OUT_OF_RANGE, INCONSISTENT_PAIR, AFTER_DEP, FILE_MISSING = 1, 2, 3, 4


@pytest.fixture
def quest(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        yield equ


def _has(diags, param, code):
    return any(d.param == param and d.code == code for d in diags), diags


def test_quest_is_clean(quest):
    assert quest.validate() == []


CASES = [
    # (name, value, reported parameter, code)
    ("NR", 2, "NR", OUT_OF_RANGE),
    ("NR", 258, "NR", OUT_OF_RANGE),
    ("NZ", 2, "NZ", OUT_OF_RANGE),
    ("NZ", 258, "NZ", OUT_OF_RANGE),
    ("NV", 2, "NV", OUT_OF_RANGE),            # eqout prints rbv(nv-2)
    ("NR", 200, "NR", OUT_OF_RANGE),          # NR-1 not a power of two
    ("NZ", 100, "NZ", OUT_OF_RANGE),
    ("IVBND", 1, "IVBND", OUT_OF_RANGE),
    ("NV", 102, "NV", OUT_OF_RANGE),
    ("NSUMAX", 2, "NSUMAX", OUT_OF_RANGE),
    ("NSUMAX", 1543, "NSUMAX", OUT_OF_RANGE),
    ("MSFX", -30, "MSFX", OUT_OF_RANGE),
    ("NCOIL[3]", 101, "NCOIL[3]", OUT_OF_RANGE),
    ("NCOIL[0]", -1, "NCOIL[0]", OUT_OF_RANGE),
    ("ILIMT", 101, "ILIMT", OUT_OF_RANGE),
    ("IEQRD", 1, "IEQRD", OUT_OF_RANGE),
    ("IVAC[7]", 7, "IVAC", INCONSISTENT_PAIR),      # 3 fitted groups, |MSFX| = 2
    ("RWMN", 0.0, "RWMN", OUT_OF_RANGE),
    ("RWMX", 0.05, "RWMX", INCONSISTENT_PAIR),
    ("ZWMX", 0.0, "ZWMX", OUT_OF_RANGE),
    ("ICP[1]", 3, "ICP[1]", OUT_OF_RANGE),
    ("ISVAC", 2, "ISVAC", OUT_OF_RANGE),
    ("ISEP", 5, "ISEP", OUT_OF_RANGE),
    ("ISEP", -5, "ISEP", OUT_OF_RANGE),
    ("IUDSYM", 2, "IUDSYM", OUT_OF_RANGE),
    ("IEQMAX", -1, "IEQMAX", OUT_OF_RANGE),
    ("MSETUP", -1, "MSETUP", OUT_OF_RANGE),
    ("IODMAX", -1, "IODMAX", OUT_OF_RANGE),
    ("IADMAX", -1, "IADMAX", OUT_OF_RANGE),
    # QUEST's marker 2 is at Z = -0.70: outside |Z| < 0.6, and outside
    # eqchek's widened box too (1.2*ELIP*RPLA = 0.691 with RPLA from the markers).
    ("ZWMX", 0.6, "RVAC[2]", AFTER_DEP),
    # A marker at R = 0.02 makes eqchek's inner edge RMAJ - 1.2*RPLA < 0.
    ("RVAC[0]", 0.02, "RWMN", AFTER_DEP),
]


@pytest.mark.parametrize("name,value,param,code", CASES,
                         ids=[f"{c[0]}={c[1]}" for c in CASES])
def test_each_check(quest, name, value, param, code):
    quest.set_param(name, value)
    found, diags = _has(quest.validate(), param, code)
    assert found, diags


def test_missing_coil_file(quest):
    quest.set_param_str("KNAMCOIL", "no-such-coil-file")
    found, diags = _has(quest.validate(), "KNAMCOIL", FILE_MISSING)
    assert found, diags
    assert "no coil file" in diags[0].message


def test_short_coil_file(quest, workdir):
    lines = (workdir / "coildata").read_text().splitlines()
    (workdir / "coildata").write_text("\n".join(lines[:-3]) + "\n")
    found, diags = _has(quest.validate(), "KNAMCOIL", FILE_MISSING)
    assert found, diags
    assert "before group 6" in diags[0].message, diags


def test_done_skips_the_coil_file(quest):
    # 'done': the coils in memory (after init, eqinit's JT-60U set).
    quest.set_param_str("KNAMCOIL", "done")
    assert not any(d.param == "KNAMCOIL" for d in quest.validate())


def test_run_refuses_with_the_first_check(quest):
    quest.set_param("NV", 1)
    with pytest.raises(EqulibInvalidParamError, match="refused: NV"):
        quest.run(1)


def test_validate_is_read_only(quest):
    quest.set_param("NV", 1)
    first = quest.validate()
    assert quest.validate() == first


@pytest.mark.parametrize("name,value", [
    ("RWMN", 0.30),   # marker 0 at R = 0.28: eqchek lowers RWMN to 0.208, the program runs
    ("ISEP", -1),     # the code uses the sign
    ("MSFX", 30),     # a positive MSFX: eqchek lowers it
])
def test_accepted_inputs(quest, name, value):
    quest.set_param(name, value)
    assert quest.validate() == [], name


def test_flux_loop_point_off_the_grid_runs(quest):
    # The default flux-loop point (2.786, 0.952) with ZWMX = 0.9 made eqout
    # index psi at 68,217 of 66,049; it computes psloop on the grid only now.
    quest.set_param("ZWMX", 0.9)
    quest.run(1)
    assert quest.get_state().nr == 257


def test_generated_markers_outside_the_box(workdir):
    # MSFX > 0 (the default 9): eqchek generates the markers from the shape;
    # ELIPUP = 1.5 puts the upper ones at Z = 1.343, above the box's 1.2.
    with Equ() as equ:
        equ.set_param_str("KNAMCOIL", "done")     # the JT-60U coils in memory
        assert equ.validate() == []
        equ.set_param("ELIPUP", 1.5)
        diags = equ.validate()
        assert any(d.param.startswith("RVAC[") and d.code == AFTER_DEP for d in diags), diags
        equ.set_param("ELIPUP", 1.0)
        equ.set_param("ZPLA", 0.4)
        assert any(d.param.startswith("RVAC[") for d in equ.validate())


def test_validate_asks_again_past_its_capacity(quest, monkeypatch):
    import equlib.equlib as mod
    for n in range(1, 7):
        quest.set_param(f"NCOIL[{n}]", 101)
    full = quest.validate()
    monkeypatch.setattr(mod, "_DIAG_CAP", 2)
    assert quest.validate() == full and len(full) > 2
