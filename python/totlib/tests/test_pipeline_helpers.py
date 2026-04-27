"""Test the compute_rjt_volint helper using a synthetic state object."""
from unittest.mock import MagicMock
import math
import pytest
from unittest.mock import MagicMock
from totlib.pipeline import compute_rjt_volint


def _fake_state(rjt_values: list[list[float]]):
    """Build a mock FpState matching R2's confirmed shape.

    R2 outcome: RJT is shape [nsamax][nrmax] in MA/m^2, on uniform rho-grid in [0,1].
    nrmax is len(rjt[0]), nsamax is len(rjt).
    """
    s = MagicMock()
    s.RJT = rjt_values
    s.nrmax = len(rjt_values[0])
    s.nsamax = len(rjt_values)
    return s


def test_compute_rjt_volint_uniform_single_species():
    """RJT = 1.0 MA/m^2, uniform across nr=4 cells, R0=3.0, a=1.0 → expected ~3.14159 MA."""
    state = _fake_state([[1.0, 1.0, 1.0, 1.0]])
    # Per R2 helper: total = sum_ns sum_i RJT[ns][i] * 1e6 * 2*pi*rho_mid*a^2*drho
    # rho_mid = (i+0.5)/nr; drho = 1/nr
    # = 1e6 * 2*pi * a^2 * (1/nr) * sum_i (i+0.5)/nr
    # For nr=4, sum_i (i+0.5)/nr = (0.5+1.5+2.5+3.5)/4 = 8/4 = 2
    # = 1e6 * 2*pi * 1.0 * (1/4) * 2 = 1e6 * pi
    expected = 1.0e6 * math.pi
    result = compute_rjt_volint(state, R0=3.0, a=1.0)
    assert math.isclose(result, expected, rel_tol=1e-12), \
        f"got {result}, expected {expected}"


def test_compute_rjt_volint_zero_profile():
    state = _fake_state([[0.0, 0.0, 0.0, 0.0]])
    assert compute_rjt_volint(state, R0=3.0, a=1.0) == 0.0


def test_compute_rjt_volint_two_species_sums():
    """For 2 species, total is the sum across species (R2 confirms this matches fp's PIT)."""
    state = _fake_state([[1.0, 1.0], [2.0, 2.0]])
    # Per-species int with nr=2, a=1.0:
    #   spec_a: 1e6 * 2*pi * 1.0 * (1/2) * (0.5/2 + 1.5/2) = 1e6*pi
    #   spec_b: 1e6 * 2*pi * 1.0 * (1/2) * 2.0 * (0.5/2 + 1.5/2) = 2e6*pi
    expected = 1.0e6 * math.pi + 2.0e6 * math.pi
    result = compute_rjt_volint(state, R0=3.0, a=1.0)
    assert math.isclose(result, expected, rel_tol=1e-12)
