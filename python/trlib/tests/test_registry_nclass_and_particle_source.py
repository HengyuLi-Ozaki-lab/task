"""NCLASS, the equations solved, the current profile, particle transport and the particle source through the registry.

``tr/tr_param_registry.f90`` has a ``CASE`` entry for each of

* ``MDNCLS`` (0 off, else NCLASS for the neoclassical transport and the resistivity: ``tr/trcalc.f90``);
* ``MDLEQB``, ``MDLEQN``, ``MDLEQE`` (the B_theta and density equations: ``TR_EQS_SELECT``, ``tr/trprep.f90``);
* ``PROFJ1``, ``PROFJ2`` (the start current profile: ``tr/trprof.f90``);
* ``AD0``, ``AV0``, ``CDP``, ``CNP`` (particle diffusion, pinch, and the weights of the turbulent and neoclassical
  parts: ``tr/trcoef_adhoc.f90``);
* ``MDLPSC``, ``NPSCMAX``, ``PSCTOT[i]``, ``PSCR0[i]``, ``PSCRW[i]``, ``NSPSC[i]`` (Gaussian particle sources,
  ``tr/trpsc.f90``; i = 1..NPSCM = 10).

The variables, their defaults (``tr/trinit.f90``) and their namelist entries existed; the names make the PLATO
case of Mochinaga et al., Plasma Fusion Res. 16, 1403093 (2021) settable through the library. The values the
solver cannot take are refused before ``tr_prep`` by ``source_and_equation_violations`` (``tr/tr_api.f90``) and
reported by ``validate()``: measured before the check, NPSCMAX 11 and NSPSC 0 or 5 stopped the process on an array
bound, PSCRW 0 ended in NaN, and MDLEQN 2 and MDLPSC 2 ran as 0 without a word. MDLEQE 1 or 2 without the densities
evolved, and MDLEQE 2 beyond two species with a hydrogenic species 2 and no impurity model (whose quasi-neutrality in
``tr/trexec.f90`` adds the other species instead of subtracting them), are refused too. A source far from every mesh
point also ended in NaN (its normalising integral underflowed); ``TRPSCA`` now normalises by the Gaussian's largest
value on the mesh, so it runs.

The case is the PLATO tokamak (R 0.7 m, a 0.18 m, B 0.3 T, I_p 40 kA, hydrogen) for a few steps of 0.1 ms. One
test per case (``parametrize``, never ``subTest``: under ``--forked`` a failing ``subTest`` is reported as passed).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibParamError  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)

A = 0.18
PLATO = {"RR": 0.7, "RA": A, "RKAP": 1.9, "RDLT": 0.4, "BB": 0.3, "RIPS": 0.04, "RIPE": 0.04, "NSMAX": 2,
         "PA[2]": 1.0, "PZ[2]": 1.0, "PN[1]": 0.1, "PN[2]": 0.1, "PNS[1]": 0.01, "PNS[2]": 0.01,
         "PT[1]": 0.13, "PT[2]": 0.035, "PTS[1]": 0.01, "PTS[2]": 0.01, "MDLKAI": 31, "CK0": 12.0, "CK1": 12.0,
         "MDLNB": 0, "DT": 1.0e-4}
NTMAX = 20
# A gas puff peaked at rho = 0.7 (PSCR0 is in metres, RA*rho), with the densities evolved.
PUFF = {"MDLEQN": 1, "MDLPSC": 1, "NPSCMAX": 1, "PSCTOT[1]": 50.0, "PSCR0[1]": 0.7 * A, "PSCRW[1]": 0.1 * A,
        "NSPSC[1]": 2}
# A third species, deuterium (TR_TABLE places a deuterium after a hydrogen as its third class).
SP3 = {"NSMAX": 3, "PA[3]": 2.0, "PZ[3]": 1.0, "PN[3]": 0.02, "PNS[3]": 0.002, "PT[3]": 0.035, "PTS[3]": 0.01}

# The defaults of tr_init (tr/trinit.f90): setting them must change nothing.
DEFAULTS = {"MDNCLS": 0, "MDLEQB": 1, "MDLEQN": 0, "MDLEQE": 0, "PROFJ1": -2.0, "PROFJ2": 1.0, "AD0": 0.5,
            "AV0": 0.0, "CDP": 1.0, "CNP": 1.0, "MDLPSC": 0, "NPSCMAX": 1,
            **{f"PSCTOT[{i}]": 0.0 for i in range(1, 11)}, **{f"PSCR0[{i}]": 0.0 for i in range(1, 11)},
            **{f"PSCRW[{i}]": 0.5 for i in range(1, 11)}, **{f"NSPSC[{i}]": 2 for i in range(1, 11)}}
NAMES = ["MDNCLS", "MDLEQB", "MDLEQN", "MDLEQE", "PROFJ1", "PROFJ2", "AD0", "AV0", "CDP", "CNP",
         "MDLPSC", "NPSCMAX", "PSCTOT[1]", "PSCR0[1]", "PSCRW[1]", "NSPSC[1]"]
ARRAYS = ["PSCTOT", "PSCR0", "PSCRW", "NSPSC"]


def _run(extra: dict, ntmax: int = NTMAX):
    """(Te0, Ti0, ne0, WPT, n3 at mid-radius, n2 at mid-radius; the last two 0 below NSMAX 3) after ``ntmax`` steps
    of the PLATO case with ``extra`` set on it."""
    with Trlib() as tr:
        for name, value in {**PLATO, **extra}.items():
            tr.set_param(name, float(value))
        tr.run(ntmax)
        s = tr.get_state()
        mid = s.RN[len(s.RN) // 2]
        return (s.RT[0][0], s.RT[0][1], s.RN[0][0], s.scalars["WPT"],
                mid[2] if s.nsmax > 2 else 0.0, mid[1] if s.nsmax > 2 else 0.0)


# ------------------------------------------------------------------ the names

@pytest.mark.parametrize("name", NAMES)
def test_the_registry_takes_the_name(name):
    with Trlib() as tr:
        tr.set_param(name, float(DEFAULTS[name]))   # TrlibParamError without a CASE entry


@pytest.mark.parametrize("name", ARRAYS)
def test_a_source_array_takes_its_tenth_element(name):
    with Trlib() as tr:
        tr.set_param(f"{name}[10]", 2.0)


@pytest.mark.parametrize("subscript", ["[0]", "[11]", ""])
@pytest.mark.parametrize("name", ARRAYS)
def test_a_source_array_refuses_a_subscript_outside_1_to_10(name, subscript):
    with Trlib() as tr:
        with pytest.raises(TrlibParamError):
            tr.set_param(name + subscript, 2.0)


def test_the_defaults_set_by_name_reproduce_the_default_run():
    assert _run(DEFAULTS) == _run({})


# ------------------------------------------------- each name reaches the run

def test_nclass_changes_the_run():
    assert _run({"MDNCLS": 1})[0] != _run({})[0]


def test_the_density_equation_moves_the_density():
    ne0 = _run({"MDLEQN": 1})[2]
    assert ne0 != pytest.approx(PLATO["PN[1]"], rel=1e-3)


def test_a_fixed_b_theta_changes_the_run():
    assert _run({"MDLEQB": 0})[0] != _run({})[0]


@pytest.mark.parametrize("profile", [{"PROFJ1": 2.0}, {"PROFJ1": 2.0, "PROFJ2": 2.0}], ids=["PROFJ1", "PROFJ2"])
def test_the_start_current_profile_changes_the_run(profile):
    reference = _run({"PROFJ1": 2.0, "PROFJ2": 1.0}) if "PROFJ2" in profile else _run({})
    assert _run(profile)[0] != reference[0]


def test_the_gas_puff_raises_the_density():
    without = _run({**PUFF, "MDLPSC": 0})[2]
    assert _run(PUFF)[2] > without * 1.01


def test_a_second_source_adds_to_the_first():
    one = _run(PUFF)[2]
    two = _run({**PUFF, "NPSCMAX": 2, "PSCTOT[2]": 50.0, "PSCR0[2]": 0.7 * A, "PSCRW[2]": 0.1 * A, "NSPSC[2]": 2})[2]
    assert two > one


@pytest.mark.parametrize("name, value", [("PSCR0[1]", 0.3 * A), ("PSCRW[1]", 0.3 * A)])
def test_where_the_source_sits_changes_the_run(name, value):
    assert _run({**PUFF, name: value})[2] != _run(PUFF)[2]


# Without NCLASS the particle flux is CDP*AD0*chi_turb + CNP*D_NC (MDLAD 3, the default: tr/trcoef_adhoc.f90); with
# NCLASS, CDP*AD0*chi_turb plus NCLASS's matrix weighted by CNP (MDDIAG 1). AD0 2 and CDP 3 end this case with a
# negative temperature within 20 steps.
@pytest.mark.parametrize("name, value", [("AD0", 1.0), ("CDP", 2.0), ("CNP", 3.0)])
def test_the_particle_transport_changes_the_density(name, value):
    assert _run({**PUFF, name: value})[2] != _run(PUFF)[2]


@pytest.mark.parametrize("name, value", [("AD0", 1.0), ("CDP", 2.0), ("CNP", 3.0)])
def test_the_particle_transport_changes_the_density_with_nclass(name, value):
    assert _run({**PUFF, "MDNCLS": 1, name: value})[2] != _run({**PUFF, "MDNCLS": 1})[2]


def test_the_pinch_factor_changes_the_density_where_the_model_has_a_pinch():
    # AV0 scales the turbulent pinch of MDLAD 1, 2 and 4; MDLAD 3 (the default) and NCLASS have none.
    assert _run({**PUFF, "MDLAD": 4, "AV0": 1.0})[2] != _run({**PUFF, "MDLAD": 4})[2]


def test_nclass_with_the_gas_puff_runs_finite():
    assert all(math.isfinite(x) for x in _run({**PUFF, "MDNCLS": 1}))


def test_the_source_feeds_the_species_nspsc_names():
    # Hydrogen (species 2) and deuterium (species 3); the source raises the density of the one it feeds.
    to_h = _run({**PUFF, **SP3, "NSPSC[1]": 2}, 50)
    to_d = _run({**PUFF, **SP3, "NSPSC[1]": 3}, 50)
    assert to_d[4] > to_h[4] and to_h[5] > to_d[5]


def test_a_source_far_outside_puts_its_rate_at_the_edge():
    near = _run({**PUFF, "PSCR0[1]": 5.0, "PSCRW[1]": 0.01})
    assert all(math.isfinite(x) for x in near) and near[2] != _run({**PUFF, "MDLPSC": 0})[2]


# --------------------------------------------- what tr_run and validate refuse

BAD = {
    "MDLEQB 2": ({"MDLEQB": 2}, "MDLEQB"),
    "MDLEQN 2": ({"MDLEQN": 2}, "MDLEQN"),
    "MDLEQN -1": ({"MDLEQN": -1}, "MDLEQN"),
    "MDLEQE 3": ({"MDLEQN": 1, "MDLEQE": 3}, "MDLEQE"),
    "MDLEQE -1": ({"MDLEQN": 1, "MDLEQE": -1}, "MDLEQE"),
    "MDLPSC 2": ({**PUFF, "MDLPSC": 2}, "MDLPSC"),
    "NPSCMAX 11": ({**PUFF, "NPSCMAX": 11}, "NPSCMAX"),
    "NPSCMAX -1": ({**PUFF, "NPSCMAX": -1}, "NPSCMAX"),
    "NSPSC 0": ({**PUFF, "NSPSC[1]": 0}, "NSPSC[1]"),
    "NSPSC 1": ({**PUFF, "NSPSC[1]": 1}, "NSPSC[1]"),
    "NSPSC above NSMAX": ({**PUFF, "NSPSC[1]": 3}, "NSPSC[1]"),
    "NSPSC above NSM": ({**PUFF, "NSPSC[1]": 5}, "NSPSC[1]"),
    "PSCRW 0": ({**PUFF, "PSCRW[1]": 0.0}, "PSCRW[1]"),
    "PSCRW negative": ({**PUFF, "PSCRW[1]": -0.018}, "PSCRW[1]"),
    "the second source": ({**PUFF, "NPSCMAX": 2, "PSCTOT[2]": 1.0, "PSCRW[2]": 0.0}, "PSCRW[2]"),
    "MDLEQE 1 without MDLEQN": ({"MDLEQE": 1}, "MDLEQE"),
    "MDLEQE 2 without MDLEQN": ({"MDLEQE": 2}, "MDLEQE"),
    "MDLEQE 2 with a third species": ({"MDLEQN": 1, "MDLEQE": 2, **SP3}, "MDLEQE"),
    "MDLEQE 2 with tritium as species 2": ({"MDLEQN": 1, "MDLEQE": 2, "PA[2]": 3.0}, "MDLEQE"),
    "MDLEQE 2 with an impurity density": ({"MDLEQN": 1, "MDLEQE": 2, "MDLIMP": 1, "PNC": 0.01}, "MDLEQE"),
    # an impurity mode tr_prof_impurity has no branch for leaves ANC and ANFE as an earlier run left them
    "MDLEQE 2 with an impurity mode outside 1..4": ({"MDLEQN": 1, "MDLEQE": 2, "MDLIMP": 5}, "MDLEQE"),
    "PSCRW below 1e-10 m": ({**PUFF, "PSCRW[1]": 1.0e-200}, "PSCRW[1]"),
    "PSCR0 beyond 1e10 m": ({**PUFF, "PSCR0[1]": 1.0e20}, "PSCR0[1]"),
    "MDLEQE 2 with species 2 of charge 2": ({"MDLEQN": 1, "MDLEQE": 2, "PA[2]": 2.0, "PZ[2]": 2.0}, "MDLEQE"),
}


@pytest.mark.parametrize("case", list(BAD), ids=list(BAD))
def test_tr_run_refuses_and_the_handle_stays_usable(case):
    extra, _ = BAD[case]
    with Trlib() as tr:
        for name, value in {**PLATO, **extra}.items():
            tr.set_param(name, float(value))
        with pytest.raises(TrlibParamError):
            tr.run(1)
        for name, value in {**PUFF, "MDLEQB": 1, "MDLEQE": 0, "NPSCMAX": 1, "NSMAX": 2, "PA[2]": 1.0,
                            "PZ[2]": 1.0, "MDLIMP": 0, "PNC": 0.0}.items():
            tr.set_param(name, float(value))
        tr.run(1)
        assert tr.get_state().nt == 1


@pytest.mark.parametrize("case", list(BAD), ids=list(BAD))
def test_validate_names_the_value(case):
    extra, param = BAD[case]
    with Trlib() as tr:
        for name, value in {**PLATO, **extra}.items():
            tr.set_param(name, float(value))
        assert param in [d.param for d in tr.validate()]


# With a UFILE (MDLUF /= 0) tr_prep may change NSMAX (TR_EQS_SELECT adds carbon when the UFILE has an impurity), so
# validate() holds MDLEQE 2 and a source to a species other than 2 against it before the run. No UFILE fixture
# exists, so these are validate() only (tr_run would need the UFILE data).
@pytest.mark.parametrize("extra, param", [
    ({"MDLEQN": 1, "MDLEQE": 2}, "MDLEQE"),
    ({**PUFF, **SP3, "NSPSC[1]": 3}, "NSPSC[1]"),
], ids=["MDLEQE 2", "NSPSC 3"])
def test_validate_with_a_ufile_names_what_tr_prep_may_change(extra, param):
    with Trlib() as tr:
        for name, value in {**PLATO, **extra, "MDLUF": 1}.items():
            tr.set_param(name, float(value))
        assert param in [d.param for d in tr.validate()]


def test_validate_with_a_ufile_takes_a_source_to_species_2():
    with Trlib() as tr:
        for name, value in {**PLATO, **PUFF, "MDLUF": 1}.items():
            tr.set_param(name, float(value))
        assert "NSPSC[1]" not in [d.param for d in tr.validate()]


def test_validate_returns_every_finding_beyond_its_first_buffer():
    # 4 species with nothing set (3 findings each) + 3 switches + 10 sources with 2 findings each = 35, more than
    # trlib's first buffer of 32 entries.
    bad = {"NSMAX": 4, "MDLEQB": 2, "MDLEQN": 2, "MDLEQE": 3, "MDLPSC": 1, "NPSCMAX": 10,
           **{f"NSPSC[{i}]": 0 for i in range(1, 11)}, **{f"PSCRW[{i}]": 0.0 for i in range(1, 11)},
           **{f"{n}[{k}]": 0.0 for n in ("PN", "PNS", "PT", "PTS") for k in (1, 2, 3, 4)}}
    with Trlib() as tr:
        for name, value in bad.items():
            tr.set_param(name, float(value))
        params = [d.param for d in tr.validate()]
    assert len(params) > 32
    assert {f"PSCRW[{i}]" for i in range(1, 11)} <= set(params), params


ALLOWED = {
    "no source, NPSCMAX 11": {"MDLPSC": 0, "NPSCMAX": 11, "NSPSC[1]": 0, "PSCRW[1]": 0.0},
    "NPSCMAX 0": {**PUFF, "NPSCMAX": 0},
    "a source beyond NPSCMAX": {**PUFF, "PSCRW[2]": 0.0, "NSPSC[2]": 0},
    "PSCR0 just outside": {**PUFF, "PSCR0[1]": A + 0.1, "PSCRW[1]": 0.05},
    "MDLEQE 2": {"MDLEQN": 1, "MDLEQE": 2},
    "MDLEQE 2 with deuterium": {"MDLEQN": 1, "MDLEQE": 2, "PA[2]": 2.0},
    # MDLIMP 1 with PNC = PNFE = 0 (the defaults) puts no impurity in (trprof.f90 scales ANC, ANFE by them)
    "MDLEQE 2 with an impurity model and no impurity": {"MDLEQN": 1, "MDLEQE": 2, "MDLIMP": 1},
    "PSCRW at 1e-10 m": {**PUFF, "PSCRW[1]": 1.0e-10},
    "MDNCLS 2 (on)": {"MDNCLS": 2},
    # TRPSCA normalises the Gaussian by its largest value on the mesh: a source far from every mesh point puts
    # its whole rate PSCTOT where it is nearest (before, the integral underflowed to 0 and the run went NaN).
    "a source far outside the plasma": {**PUFF, "PSCR0[1]": 5.0, "PSCRW[1]": 0.01},
    # (with PSCTOT 50 the whole rate in the cell on the axis ends in a negative temperature: a run failure,
    # not a NaN)
    "a source far inside": {**PUFF, "PSCR0[1]": -5.0, "PSCRW[1]": 0.01, "PSCTOT[1]": 5.0},
    # between the mesh points at rho 0.49 and 0.51 (RA*rho, NRMAX 50), far narrower than their spacing
    "a source narrower than the mesh": {**PUFF, "PSCR0[1]": 0.5 * A, "PSCRW[1]": 1.0e-6},
}


@pytest.mark.parametrize("case", list(ALLOWED), ids=list(ALLOWED))
def test_what_the_checks_leave_alone_runs(case):
    with Trlib() as tr:
        for name, value in {**PLATO, **ALLOWED[case]}.items():
            tr.set_param(name, float(value))
        assert tr.validate() == []
        tr.run(2)
        s = tr.get_state()
        assert all(math.isfinite(x) for row in s.RT + s.RN for x in row)
