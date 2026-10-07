"""FTAUE and FTAUI (``tr/trcoll.f90``): what the zero-density guard replaces.

Both divide by the density of the ion species they are given, and a run with
fewer ion species than the code has slots calls them with a density of
exactly zero (TRAJBS asks for species 3 and 4 whatever NSMAX is).  The guard
returns ``1.D8`` there instead of dividing by zero.

It is for exactly zero, and only where the function divides by that density.
``trx`` tests ``ABS(ANIL) <= 1.D-8`` at the head of both functions, and the
port first did the same; that also replaced results that were finite:

* a species present at a trace density (measured on the whole code:
  tr_iter01 with helium at 1.D-9, 20 steps, 182 of 567 state values moved, by
  up to 2.3e-9);
* FTAUE's impurity branch, taken when Zeff is above the charge of species 2,
  whose denominator is the electron density and never depended on the ion
  density at all.

The functions are module procedures with no entry on the C ABI, so they are
called here through their gfortran symbols, as ``test_libnf.py`` calls libnf.
"""

from __future__ import annotations

import ctypes
import math

import pytest

from trlib import Trlib

SYM_FTAUE = "__trcoll_MOD_ftaue"   # FTAUE(ANEL, ANIL, TEL, ZL)
SYM_FTAUI = "__trcoll_MOD_ftaui"   # FTAUI(ANEL, ANIL, TIL, ZL, PAL)

GUARD_VALUE = 1.0e8

# Densities in 1e20 m^-3, temperatures in keV.  ZL = 1 is the charge of
# species 2 after tr_init, so FTAUE takes the branch that divides by ANIL;
# ZL = 2.5 is an effective charge above it, the impurity branch.
ANE, TEMP = 0.7, 3.0
Z_MAIN, Z_EFF = 1.0, 2.5
TRACE = (1.0e-8, 1.0e-9, 1.0e-12, 1.0e-30)


@pytest.fixture()
def coll():
    """(ftaue, ftaui) on an initialised library: FTAUE reads PZ(2)."""
    from trlib._ffi import load_library

    lib = load_library()
    dbl = ctypes.POINTER(ctypes.c_double)
    raw_e = getattr(lib, SYM_FTAUE)
    raw_e.restype, raw_e.argtypes = ctypes.c_double, [dbl] * 4
    raw_i = getattr(lib, SYM_FTAUI)
    raw_i.restype, raw_i.argtypes = ctypes.c_double, [dbl] * 5

    def call(fn, *values):
        return fn(*(ctypes.byref(ctypes.c_double(v)) for v in values))

    with Trlib():
        yield (lambda ane, ani, te, z: call(raw_e, ane, ani, te, z),
               lambda ane, ani, ti, z, a: call(raw_i, ane, ani, ti, z, a))


def test_ftaue_takes_the_branch_this_file_assumes(coll):
    """The premise of the tests below: ZL = 1 divides by ANIL, ZL = 2.5 does not."""
    ftaue, _ = coll
    assert ftaue(ANE, 0.2, TEMP, Z_MAIN) != ftaue(ANE, 0.4, TEMP, Z_MAIN)
    assert ftaue(ANE, 0.2, TEMP, Z_EFF) == ftaue(ANE, 0.4, TEMP, Z_EFF)


def test_no_ions_at_all_gives_the_large_finite_time(coll):
    ftaue, ftaui = coll
    assert ftaue(ANE, 0.0, TEMP, Z_MAIN) == GUARD_VALUE
    assert ftaui(ANE, 0.0, TEMP, 1.0, 2.0) == GUARD_VALUE


@pytest.mark.parametrize("n", TRACE)
def test_a_trace_density_keeps_its_own_time(coll, n):
    """tau goes as 1/n: at a trace density it is long, and it is not 1.D8.

    With the guard at ABS(n) <= 1.D-8 every value here came back as 1.D8.
    """
    ftaue, ftaui = coll
    for name, at in (("FTAUE", lambda d: ftaue(ANE, d, TEMP, Z_MAIN)),
                     ("FTAUI", lambda d: ftaui(ANE, d, TEMP, 1.0, 2.0))):
        tau, unit = at(n), at(1.0)
        assert math.isfinite(tau) and tau > 0.0, f"{name}(n={n:g}) = {tau!r}"
        assert tau == pytest.approx(unit / n, rel=1e-12), (
            f"{name}(n={n:g}) = {tau!r}, and 1/n of its value at n = 1 is "
            f"{unit / n!r}: something replaced the division"
        )


@pytest.mark.parametrize("n", (0.0,) + TRACE)
def test_the_impurity_branch_does_not_look_at_the_ion_density(coll, n):
    """Its denominator is the electron density: no ion density changes it."""
    ftaue, _ = coll
    reference = ftaue(ANE, 0.3, TEMP, Z_EFF)
    assert math.isfinite(reference) and reference != GUARD_VALUE
    assert ftaue(ANE, n, TEMP, Z_EFF) == reference
