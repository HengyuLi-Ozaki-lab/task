"""FpDistribution and FpFnsInfoC without the library (task-web-client #232)."""
from __future__ import annotations

import array
import ctypes
import math
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from fplib import FplibAbiError  # noqa: E402
from fplib import _ffi  # noqa: E402
from fplib.distribution import FpDistribution  # noqa: E402

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


def _info(**over):
    info = {name: 0 for name, _ in _ffi.FpFnsInfoC._fields_}
    info.update(nsa=1, ns=2, rtfp0=3.0, vtfp0=1.0e6, theta0=0.0)
    info.update(over)
    return info


def _dist(nr=2, np_=3, nth=4, **info):
    """Values 10000*ir + 100*ip + ith, laid out as Fortran's FNS(nth, np, nr)."""
    data = array.array("d", [0.0] * (nr * np_ * nth))
    k = 0
    for ir in range(nr):              # Fortran's last index varies slowest
        for ip in range(np_):
            for ith in range(nth):    # its first index varies fastest
                data[k] = 10000.0 * ir + 100.0 * ip + ith
                k += 1
    return FpDistribution(data=data, shape=(nr, np_, nth), pm=[0.5 + i for i in range(np_)],
                          thm=[(i + 0.5) * math.pi / nth for i in range(nth)],
                          rm=[(i + 0.5) / nr for i in range(nr)], info=_info(**info))


class TestFormulas(unittest.TestCase):
    def test_energy_without_relativity_is_half_rtfp0_p_squared(self):
        d = _dist()
        self.assertEqual(d.energy_keV(), [0.5 * 3.0 * p * p for p in d.pm])

    def test_speed_without_relativity_is_p_vtfp0(self):
        d = _dist()
        self.assertEqual(d.speed(), [p * 1.0e6 for p in d.pm])

    def test_energy_with_relativity_is_m_c2_gamma_minus_1(self):
        d = _dist(theta0=0.01)
        mc2 = 3.0 / 0.01   # FP's theta0 = RTFP0 / (m c^2), same temperature and mass
        for p, e in zip(d.pm, d.energy_keV()):
            self.assertAlmostEqual(e, mc2 * (math.sqrt(1.0 + 0.01 * p * p) - 1.0), delta=1e-12 * e)

    def test_speed_and_energy_with_relativity_agree_on_gamma(self):
        c = 2.99792458e8
        d = _dist(theta0=0.01, rtfp0=3.0, vtfp0=c * math.sqrt(0.01))
        for v, e in zip(d.speed(), d.energy_keV()):
            self.assertLess(v, c)
            gamma_v = 1.0 / math.sqrt(1.0 - (v / c) ** 2)
            self.assertAlmostEqual(gamma_v - 1.0, e / (3.0 / 0.01), delta=1e-12 * (gamma_v - 1.0))

    def test_pitch_is_cos_thm(self):
        d = _dist()
        self.assertEqual(d.pitch(), [math.cos(t) for t in d.thm])


class TestLayout(unittest.TestCase):
    def test_data_index_is_ir_ip_ith_in_c_order(self):
        d = _dist()
        nr, np_, nth = d.shape
        for ir in range(nr):
            for ip in range(np_):
                for ith in range(nth):
                    self.assertEqual(d.data[(ir * np_ + ip) * nth + ith],
                                     10000.0 * ir + 100.0 * ip + ith)

    @unittest.skipIf(np is None, "numpy not installed")
    def test_to_numpy_is_f_ir_ip_ith(self):
        a = _dist().to_numpy()
        self.assertEqual(a.shape, (2, 3, 4))
        for ir in range(2):
            for ip in range(3):
                for ith in range(4):
                    self.assertEqual(a[ir, ip, ith], 10000 * ir + 100 * ip + ith)
        self.assertEqual(a.dtype, np.float64)

    @unittest.skipIf(np is None, "numpy not installed")
    def test_save_npy_reads_back_equal(self):
        d = _dist()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.npy"
            d.save_npy(path)
            raw = path.read_bytes()
            back = np.load(path)
        self.assertEqual((10 + int.from_bytes(raw[8:10], "little")) % 64, 0)
        self.assertTrue(np.array_equal(back, d.to_numpy()))

    @unittest.skipIf(np is None, "numpy not installed")
    def test_save_npy_replaces_a_symlink_and_leaves_its_target(self):
        d = _dist()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.bin"
            target.write_bytes(b"keep me")
            link = Path(tmp) / "f.npy"
            os.symlink(target, link)
            d.save_npy(link)
            self.assertFalse(link.is_symlink())
            self.assertEqual(target.read_bytes(), b"keep me")
            self.assertTrue(np.array_equal(np.load(link), d.to_numpy()))

    @unittest.skipIf(np is None, "numpy not installed")
    def test_save_npy_replaces_an_existing_file(self):
        d = _dist()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.npy"
            path.write_bytes(b"old content")
            d.save_npy(path)
            self.assertTrue(np.array_equal(np.load(path), d.to_numpy()))

    def test_a_failed_write_keeps_the_old_file_and_leaves_no_temporary(self):
        d = _dist()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.npy"
            path.write_bytes(b"old content")
            with mock.patch("fplib.distribution.os.replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    d.save_npy(path)
            self.assertEqual(path.read_bytes(), b"old content")
            self.assertEqual(os.listdir(tmp), ["f.npy"])


class TestFnsInfoC(unittest.TestCase):
    def test_layout_is_six_ints_then_eleven_doubles(self):
        self.assertEqual(ctypes.sizeof(_ffi.FpFnsInfoC), 6 * 4 + 11 * 8)
        self.assertEqual(_ffi.FpFnsInfoC.timefp.offset, 24)
        self.assertEqual(_ffi.FpFnsInfoC.delth.offset, 24 + 10 * 8)

    def test_a_library_without_the_query_is_refused(self):
        class _NoQuery:
            _name = "/x/libfpapi.so"
        with self.assertRaises(FplibAbiError) as ctx:
            _ffi.attach_fns_prototypes(_NoQuery())
        self.assertIn("fp_fns_info_abi_version", str(ctx.exception))


class TestFieldOrder(unittest.TestCase):
    def test_fields_follow_fp_fns_info_t(self):
        fields = _ffi.FpFnsInfoC._fields_
        self.assertEqual([n for n, _ in fields],
                         ["nsa", "ns", "nthmax", "npmax", "nrmax", "modela", "timefp", "amfp",
                          "aefp", "rnfp0", "rtfp0", "ptfp0", "vtfp0", "theta0", "pmax", "delp",
                          "delth"])
        self.assertTrue(all(t is ctypes.c_int for _, t in fields[:6]))
        self.assertTrue(all(t is ctypes.c_double for _, t in fields[6:]))


class _Fn:
    def __init__(self, value=None):
        self._value = value
        self.restype = None
        self.argtypes = None

    def __call__(self):
        return self._value


class _FakeLib:
    _name = "/x/libfpapi.so"

    def __init__(self, version=1, size=None, getters=True):
        self.fp_fns_info_abi_version = _Fn(version)
        self.fp_fns_info_size = _Fn(ctypes.sizeof(_ffi.FpFnsInfoC) if size is None else size)
        if getters:
            self.fp_get_fns_info = _Fn()
            self.fp_get_fns_grid = _Fn()
            self.fp_get_fns = _Fn()


class TestAttachFnsPrototypes(unittest.TestCase):
    def test_another_version_is_refused(self):
        with self.assertRaises(FplibAbiError) as ctx:
            _ffi.attach_fns_prototypes(_FakeLib(version=2))
        self.assertIn("fns_info layout is v2", str(ctx.exception))

    def test_another_size_is_refused(self):
        wrong = ctypes.sizeof(_ffi.FpFnsInfoC) + 8
        with self.assertRaises(FplibAbiError) as ctx:
            _ffi.attach_fns_prototypes(_FakeLib(size=wrong))
        self.assertIn(str(wrong), str(ctx.exception))

    def test_query_without_getters_is_refused(self):
        with self.assertRaises(FplibAbiError) as ctx:
            _ffi.attach_fns_prototypes(_FakeLib(getters=False))
        self.assertIn("has the fp_fns_info_t layout query but not the getters", str(ctx.exception))

    def test_prototypes_are_attached(self):
        lib = _FakeLib()
        _ffi.attach_fns_prototypes(lib)
        self.assertEqual(lib.fp_get_fns_info.argtypes,
                         [ctypes.c_int, ctypes.POINTER(_ffi.FpFnsInfoC)])
        self.assertEqual(len(lib.fp_get_fns_grid.argtypes), 7)
        self.assertEqual(len(lib.fp_get_fns.argtypes), 3)
        for fn in (lib.fp_get_fns_info, lib.fp_get_fns_grid, lib.fp_get_fns):
            self.assertIs(fn.restype, ctypes.c_int)


class TestPostInit(unittest.TestCase):
    def _make(self, **over):
        d = _dist()
        kw = dict(data=d.data, shape=d.shape, pm=d.pm, thm=d.thm, rm=d.rm, info=d.info)
        kw.update(over)
        return FpDistribution(**kw)

    def test_wrong_data_length_is_refused(self):
        with self.assertRaises(ValueError):
            self._make(data=array.array("d", [0.0] * 5))

    def test_wrong_pm_length_is_refused(self):
        with self.assertRaises(ValueError):
            self._make(pm=[1.0, 2.0])

    def test_shape_list_becomes_tuple(self):
        self.assertEqual(self._make(shape=[2, 3, 4]).shape, (2, 3, 4))
        self.assertIsInstance(self._make(shape=[2, 3, 4]).shape, tuple)


if __name__ == "__main__":
    unittest.main()
