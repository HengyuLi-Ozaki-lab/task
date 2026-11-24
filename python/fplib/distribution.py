"""The FP distribution function of one kinetic species (task-web-client #232).

:meth:`fplib.Fplib.get_distribution` returns an :class:`FpDistribution`: FP's
``FNS(1:NTHMAX, 1:NPMAX, 1:NRMAX, nsa)``, unscaled, with its grid and normalisation.
Speed, energy and pitch are computed with FP's own formulas.

``data`` holds the Fortran array in its own order, which is the C-order array of
shape ``(nr, np, nth)``: ``f[ir, ip, ith]`` is ``data[(ir * np + ip) * nth + ith]``
(0-origin).

The values are normalised as FP's density moment uses them: for ``MODELA = 0``,
``n = rnfp0 * sum(VOLP * f)`` [1e20 m^-3] over a surface, with
``VOLP = 2 pi sin(thm) pm^2 delp delth``. For ``MODELA = 1`` FP also weights by
``RLAMDA * RFSADG``, which the library does not export.
"""
from __future__ import annotations

import array
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union


@dataclass(frozen=True)
class FpDistribution:
    """FNS of one kinetic species, its grid (``pm``, ``thm``, ``rm``) and ``info``.

    ``info`` holds every field of ``fp_fns_info_t``: ``nsa``, ``ns``, ``nthmax``,
    ``npmax``, ``nrmax``, ``modela``, ``timefp`` [s], ``amfp`` [kg], ``aefp`` [C],
    ``rnfp0`` [1e20 m^-3], ``rtfp0`` [keV], ``ptfp0`` [kg m/s], ``vtfp0`` [m/s],
    ``theta0``, ``pmax``, ``delp``, ``delth`` [rad].
    """

    data: array.array
    shape: Tuple[int, int, int]
    pm: List[float]
    thm: List[float]
    rm: List[float]
    info: Dict[str, Any]

    def __post_init__(self) -> None:
        shape = tuple(int(n) for n in self.shape)
        if len(shape) != 3:
            raise ValueError(f"shape must be (nr, np, nth), not {self.shape!r}")
        object.__setattr__(self, "shape", shape)
        nr, np_, nth = shape
        if len(self.data) != nr * np_ * nth:
            raise ValueError(f"data has {len(self.data)} values, shape {shape} needs {nr * np_ * nth}")
        for name, want in (("pm", np_), ("thm", nth), ("rm", nr)):
            got = len(getattr(self, name))
            if got != want:
                raise ValueError(f"{name} has {got} values, shape {shape} needs {want}")

    def speed(self) -> List[float]:
        """Speed [m/s] at each ``pm``: ``v = p * VTFP0 / gamma``, ``gamma = sqrt(1 + theta0 p^2)``."""
        t0 = float(self.info["theta0"])
        vt = float(self.info["vtfp0"])
        return [p * vt / math.sqrt(1.0 + t0 * p * p) for p in self.pm]

    def energy_keV(self) -> List[float]:
        """Kinetic energy [keV] at each ``pm``.

        ``m c^2 (gamma - 1)``, written as ``RTFP0 p^2 / (gamma + 1)``. FP sets
        ``theta0 = RTFP0 / (m c^2)`` from the temperature and mass that give
        ``PTFP0`` (fp/fpprep.f90), so the two are equal, and the second is
        ``1/2 RTFP0 p^2`` when ``theta0 = 0`` (``MODELR = 0``).
        """
        t0 = float(self.info["theta0"])
        rt = float(self.info["rtfp0"])
        return [rt * p * p / (math.sqrt(1.0 + t0 * p * p) + 1.0) for p in self.pm]

    def pitch(self) -> List[float]:
        """``cos(theta)`` at each ``thm``; theta is measured from the field, ``v_par = v cos(theta)``.

        With ``MODELA = 1`` theta is the pitch angle at the field minimum of the surface.
        """
        return [math.cos(t) for t in self.thm]

    def to_numpy(self):
        """A float64 ndarray ``f[ir, ip, ith]`` (a copy). Needs numpy."""
        import numpy as np

        return np.array(self.data, dtype=np.float64).reshape(self.shape)

    def save_npy(self, path: Union[str, Path]) -> None:
        """Write a ``.npy`` file (format 1.0, little-endian float64, C order) with the standard library."""
        header = "{'descr': '<f8', 'fortran_order': False, 'shape': (%d, %d, %d), }" % self.shape
        # magic (6) + version (2) + header length (2) + header: spaces and a newline make
        # the whole a multiple of 64 bytes, as numpy writes it.
        pad = (-(10 + len(header) + 1)) % 64
        header_bytes = (header + " " * pad + "\n").encode("latin1")
        values = array.array("d", self.data)
        if sys.byteorder != "little":
            values.byteswap()
        with open(path, "wb") as fh:
            fh.write(b"\x93NUMPY\x01\x00")
            fh.write(struct.pack("<H", len(header_bytes)))
            fh.write(header_bytes)
            fh.write(values.tobytes())


__all__ = ["FpDistribution"]
