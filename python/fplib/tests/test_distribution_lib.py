"""Fplib.get_distribution against the library (task-web-client #232).

Same-process equality with FP_SAVE2, the density moment against RNT, the birth peak
of an 80 keV beam, continuation, and the window after a set. Runs that are compared
with each other each get a process of their own (one run per process).
"""
from __future__ import annotations

import array
import contextlib
import ctypes
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "fp" / "libfpapi.so"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from fplib import Fplib, FplibCalcFailedError, FplibInvalidParamError  # noqa: E402
from fplib import _ffi  # noqa: E402

DELT = 0.002
SMALL = {"NPMAX": 12, "NTHMAX": 8, "DELT": DELT}
# Deuterium (species 2) is kinetic species 1 at 3 keV; PMAX 10 holds an 80 keV beam.
D_RUN = {
    "NSMAX": 2, "NSAMAX": 1, "NSBMAX": 2, "NS_NSA[1]": 2,
    "PTPR[1]": 3.0, "PTPP[1]": 3.0, "PTPR[2]": 3.0, "PTPP[2]": 3.0,
    "PMAX[2]": 10.0, "NPMAX": 20, "NTHMAX": 10, "DELT": DELT,
}
# SPBTOT is in 1e20 particles/s; 1e20 (a source of 1e40 /s) is far beyond a real beam: the collision
# operator is linear in f, so the size only makes the signal clear.
BEAM = {
    "MODEL_NBI": 1, "NBEAMMAX": 1, "NSSPB[1]": 2, "SPBTOT[1]": 1.0e20,
    "SPBENG[1]": 8.0e4, "SPBANG[1]": 30.0, "SPBR0[1]": 0.0, "SPBRW[1]": 0.5,
}

_NEEDS_THE_LIBRARY = unittest.skipUnless(
    DEFAULT_SO.exists(), f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`")


def _set(fp, params):
    for name, value in params.items():
        fp.set_param(name, float(value))


@contextlib.contextmanager
def _cwd(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _records(path):
    """The records of a gfortran unformatted sequential file (4-byte length markers)."""
    raw = Path(path).read_bytes()
    out, i = [], 0
    while i < len(raw):
        (n,) = struct.unpack_from("<i", raw, i)
        out.append(raw[i + 4:i + 4 + n])
        (m,) = struct.unpack_from("<i", raw, i + 4 + n)
        assert m == n, (i, n, m)
        i += 8 + n
    return out


_CHILD = r"""
import json, os, sys
sys.path.insert(0, sys.argv[1])
from fplib import Fplib
params, runs, out = json.loads(sys.argv[2]), json.loads(sys.argv[3]), sys.argv[4]
with Fplib() as fp:
    for name, value in params.items():
        fp.set_param(name, float(value))
    for n in runs:
        fp.run(n)
    d = fp.get_distribution(1)
    with open(out, "wb") as fh:
        fh.write(d.data.tobytes())
    print("TIMEFP", repr(fp.get_state().timefp), flush=True)
os._exit(0)
"""


def _child(params, runs, out):
    done = subprocess.run([sys.executable, "-c", _CHILD, str(PYTHON_ROOT), json.dumps(params),
                           json.dumps(runs), str(out)], capture_output=True, text=True,
                          errors="replace", timeout=50)
    lines = [line for line in done.stdout.splitlines() if line.startswith("TIMEFP ")]
    assert done.returncode == 0 and len(lines) == 1, done.stdout[-600:] + done.stderr[-600:]
    return lines[0]


@_NEEDS_THE_LIBRARY
class TestTheWindow(unittest.TestCase):
    def test_refused_before_a_run(self):
        with Fplib() as fp:
            with self.assertRaises(FplibCalcFailedError):
                fp.get_distribution(1)

    def test_refused_after_a_set_until_the_next_run(self):
        with Fplib() as fp:
            _set(fp, SMALL)
            fp.run(1)
            fp.get_distribution(1)
            fp.set_param("DELT", DELT)
            with self.assertRaises(FplibCalcFailedError):
                fp.get_distribution(1)
            fp.run(1)
            fp.get_distribution(1)


@_NEEDS_THE_LIBRARY
class TestWhatComesBack(unittest.TestCase):
    def test_shape_grid_and_info_follow_fp(self):
        with Fplib() as fp:
            _set(fp, SMALL)
            fp.run(2)
            state = fp.get_state()
            d = fp.get_distribution(1)
        self.assertEqual(d.shape, (state.nrmax, state.npmax, state.nthmax))
        self.assertEqual(len(d.data), state.nrmax * state.npmax * state.nthmax)
        self.assertEqual(d.pm, [d.info["delp"] * (i + 0.5) for i in range(state.npmax)])
        self.assertEqual(d.thm, [d.info["delth"] * (i + 0.5) for i in range(state.nthmax)])
        self.assertEqual((d.info["nsa"], d.info["ns"], d.info["timefp"]), (1, 1, state.timefp))
        self.assertTrue(all(math.isfinite(v) for v in d.data))

    def test_info_fields_equal_values_derived_from_fp_s_inputs(self):
        # bpsd/bpsd_constants.f90 (the active lines).
        aee, amp = 1.602176634e-19, 1.67262192369e-27
        with Fplib() as fp:
            _set(fp, D_RUN)
            fp.run(1)
            info = fp.get_distribution(1).info
        # Exact by construction: a value FP copies from an input or a constant with one
        # multiplication, or computes from exactly representable inputs (3.0, 10.0/20, pi/10
        # are the same IEEE operations here as in the Fortran).
        self.assertEqual(info["amfp"], 2.0 * amp)       # deuterium PA 2
        self.assertEqual(info["aefp"], 1.0 * aee)       # PZ 1
        self.assertEqual(info["rtfp0"], 3.0)            # (PTPR + 2 PTPP) / 3
        self.assertEqual(info["rnfp0"], 1.0)            # PN default
        self.assertEqual(info["pmax"], 10.0)
        self.assertEqual(info["delp"], 10.0 / 20)
        self.assertEqual(info["delth"], math.pi / 10)
        self.assertEqual((info["ns"], info["nsa"], info["modela"]), (2, 1, 0))
        self.assertEqual(info["theta0"], 0.0)
        self.assertEqual((info["nthmax"], info["npmax"], info["nrmax"]), (10, 20, 1))
        # Not exact: sqrt and the products may be rounded differently, so a relative 1e-14.
        ptfp0 = math.sqrt(info["rtfp0"] * 1e3 * aee * info["amfp"])
        self.assertAlmostEqual(info["ptfp0"] / ptfp0, 1.0, delta=1e-14)
        self.assertAlmostEqual(info["vtfp0"] / (info["ptfp0"] / info["amfp"]), 1.0, delta=1e-14)

    def test_nsa_outside_the_c_int_range_is_refused(self):
        with Fplib() as fp:
            _set(fp, SMALL)
            fp.run(1)
            with self.assertRaises(FplibInvalidParamError):
                fp.get_distribution(2**32 + 1)

    def test_nsa_beyond_nsamax_is_refused(self):
        with Fplib() as fp:
            _set(fp, SMALL)
            fp.run(1)
            with self.assertRaises(FplibInvalidParamError):
                fp.get_distribution(2)

    def test_a_non_integer_nsa_is_a_type_error(self):
        with Fplib() as fp:
            _set(fp, SMALL)
            fp.run(1)
            with self.assertRaises(TypeError):
                fp.get_distribution(1.5)

    def test_the_record_layout_is_the_library_s(self):
        with Fplib() as fp:
            _ffi.attach_fns_prototypes(fp._lib)
            self.assertEqual(fp._lib.fp_fns_info_size(), ctypes.sizeof(_ffi.FpFnsInfoC))

    def test_density_moment_is_rnt(self):
        with Fplib() as fp:
            _set(fp, SMALL)
            fp.run(2)
            rnt = fp.get_state().RNT[0][0]
            d = fp.get_distribution(1)
        nr, np_, nth = d.shape
        total = 0.0
        for ip in range(np_):
            for ith in range(nth):
                volp = 2.0 * math.pi * math.sin(d.thm[ith]) * d.pm[ip] ** 2 * d.info["delp"] * d.info["delth"]
                total += volp * d.data[(0 * np_ + ip) * nth + ith]
        n = d.info["rnfp0"] * total
        # Not to the bit: FP multiplies by 1e20 and then by 1e-20 (fp/fpsave.f90).
        self.assertLess(abs(n - rnt), 1e-12 * abs(rnt))


_EQUALITY_CHILD = r"""
import array, ctypes, json, os, struct, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from fplib import Fplib
params = json.loads(sys.argv[2])


def records(path):
    raw = Path(path).read_bytes()
    out, i = [], 0
    while i < len(raw):
        (n,) = struct.unpack_from("<i", raw, i)
        out.append(raw[i + 4:i + 4 + n])
        (m,) = struct.unpack_from("<i", raw, i + 4 + n)
        assert m == n, (i, n, m)
        i += 8 + n
    return out


with Fplib() as fp:
    for name, value in params.items():
        fp.set_param(name, float(value))
    fp.run(2)
    dists = {nsa: fp.get_distribution(nsa) for nsa in (1, 2)}
    try:
        save2 = getattr(fp._lib, "__fpfile_MOD_fp_save2")
    except AttributeError:
        print("VERDICT NOSYMBOL", flush=True)
        os._exit(0)
    save2.restype = None
    save2.argtypes = []
    # After fp_init MODEFW is 0 (eq/eqinit.f90): FWOPEN writes without a prompt.
    save2()
recs = records("fpdata")
nrmax, npmax, nthmax, nsamax, _nsbmax, nsmax = struct.unpack("<6i", recs[0])
first = 2 + 2 * nsamax + nsmax              # header, mesh, per-NSA, per-NS records
for nsa in (1, 2):
    d = dists[nsa]
    assert d.shape == (nrmax, npmax, nthmax), (d.shape, nrmax, npmax, nthmax)
    for ir in range(nrmax):
        for ip in range(npmax):
            rec = array.array("d", recs[first + ((nsa - 1) * nrmax + ir) * npmax + ip])
            k = (ir * npmax + ip) * nthmax
            if list(rec) != list(d.data[k:k + nthmax]):
                print("VERDICT DIFF", nsa, ir, ip, flush=True)
                os._exit(0)
print("VERDICT SAME", nsamax, flush=True)
os._exit(0)
"""


@_NEEDS_THE_LIBRARY
class TestSameProcessEquality(unittest.TestCase):
    def test_get_fns_equals_fp_save2_for_both_species(self):
        params = {**SMALL, "NSAMAX": 2, "NSBMAX": 2}
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run(
                [sys.executable, "-c", _EQUALITY_CHILD, str(PYTHON_ROOT), json.dumps(params)],
                capture_output=True, text=True, errors="replace", timeout=50, cwd=tmp,
                stdin=subprocess.DEVNULL)
        verdict = [line for line in done.stdout.splitlines() if line.startswith("VERDICT ")]
        self.assertEqual(done.returncode, 0, done.stdout[-600:] + done.stderr[-600:])
        self.assertEqual(len(verdict), 1, done.stdout[-600:] + done.stderr[-600:])
        if verdict[0] == "VERDICT NOSYMBOL":
            self.skipTest("__fpfile_MOD_fp_save2 is not exported by this build")
        self.assertEqual(verdict[0], "VERDICT SAME 2")


@_NEEDS_THE_LIBRARY
class TestBirthPeak(unittest.TestCase):
    def test_an_80_kev_beam_rises_most_in_its_momentum_and_pitch_cell(self):
        with Fplib() as fp:
            _set(fp, {**D_RUN, **BEAM})
            fp.run(0)
            start = fp.get_distribution(1)
            fp.run(3)
            d = fp.get_distribution(1)
        nr, np_, nth = d.shape
        delp = d.info["delp"]
        ith = int(30.0 / (180.0 / nth))                 # FP's cell: THG(k) <= 30 deg < THG(k+1)
        peak_ip = int(math.sqrt(2.0 * 80.0 / 3.0) / delp)   # FP's rule for the beam momentum
        e = d.energy_keV()

        def rise(ip, it):
            k = (0 * np_ + ip) * nth + it
            return d.data[k] - start.data[k]

        cells = [(ip, it) for ip in range(np_) if d.pm[ip] > 4.0 for it in range(nth)]
        best = max(cells, key=lambda c: rise(*c))
        self.assertEqual(best, (peak_ip, ith), sorted(cells, key=lambda c: -rise(*c))[:5])
        self.assertGreater(rise(peak_ip, ith), 0.0)
        mirror = rise(peak_ip, nth - 1 - ith)           # 153 degrees: the beam is v_par > 0
        self.assertLess(abs(mirror), 1e-3 * rise(peak_ip, ith), mirror)
        # The cell's edges hold 80 keV, and the energy the record gives is the nearest to it.
        lo = 0.5 * d.info["rtfp0"] * (d.pm[peak_ip] - 0.5 * delp) ** 2
        hi = 0.5 * d.info["rtfp0"] * (d.pm[peak_ip] + 0.5 * delp) ** 2
        self.assertTrue(lo <= 80.0 < hi, (peak_ip, e[peak_ip], lo, hi))
        self.assertEqual(min(range(np_), key=lambda k: abs(e[k] - 80.0)), peak_ip)
        # Only a check of pitch()'s sign convention (v_par/v > 0 below 90 degrees), not of the data.
        self.assertGreater(d.pitch()[ith], 0.0)


@_NEEDS_THE_LIBRARY
class TestContinuation(unittest.TestCase):
    def test_run_2_then_2_is_run_4_to_the_bit(self):
        params = {**D_RUN, **BEAM}                      # a beam makes FNS change between steps
        with tempfile.TemporaryDirectory() as tmp:
            a = _child(params, [2, 2], Path(tmp) / "a")
            b = _child(params, [4], Path(tmp) / "b")
            c = _child(params, [2], Path(tmp) / "c")
            self.assertEqual(a, b)
            self.assertEqual((Path(tmp) / "a").read_bytes(), (Path(tmp) / "b").read_bytes())
            # Negative control: the comparison can fail.
            self.assertNotEqual((Path(tmp) / "c").read_bytes(), (Path(tmp) / "b").read_bytes())


if __name__ == "__main__":
    unittest.main()


@_NEEDS_THE_LIBRARY
class TestBeamSourceUnit(unittest.TestCase):
    """SPBTOT is in 1e20 particles/s (fp/fpinit.f90's comment says [1/s]).

    On one radial surface, one step of DELT adds SPBTOT * DELT * 1e20 particles to the plasma, so
    the density increment RNT [1e20 m^-3] times the plasma volume [m^3] is SPBTOT * DELT. The
    source is linear in SPBTOT.
    """
    DELT = 1.0e-3

    def _added(self, spbtot):
        params = {**D_RUN, **BEAM, "NRMAX": 1, "MODELA": 0, "DELT": self.DELT, "SPBTOT[1]": spbtot}
        with Fplib() as fp:
            _set(fp, params)
            fp.run(0)
            s0 = fp.get_state()
            fp.run(1)
            s1 = fp.get_state()
        return (s1.RNT[0][0] - s0.RNT[0][0]) * s1.scalars["PLASMA_VOLUME"]

    def test_the_density_increment_times_the_volume_is_spbtot_delt(self):
        for spbtot in (1.0, 0.5):
            added = self._added(spbtot)
            self.assertAlmostEqual(added / (spbtot * self.DELT), 1.0, delta=1.0e-9, msg=added)
