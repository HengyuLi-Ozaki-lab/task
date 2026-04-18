"""Pythonic snapshot of the C ``wrx_state_t`` structure.

:class:`WrxState` is a plain :mod:`dataclasses` view. No numpy
dependency; per-ray and per-species fields are Python lists so
``to_dict()`` is JSON-serialisable out of the box. The ``to_dict()``
layout follows the same ``rays`` / ``profile_rs`` / ``profile_rl``
layout as :mod:`wrlib.state` so the ``compare_metrics.py`` tooling
from L-6 can diff Layer-2 (direct C ABI) and Layer-3 (Python) outputs
against a Layer-1 baseline.

Note that WRX's per-species profile axis (NSAMAX) replaces WR's
radial-profile axis (NRSMAX / NRLMAX); the ``rs`` / ``rl`` suffixes
here refer to the two distinct peak-power positions (see ``wrx_api.h``
for details).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ._ffi import WRX_MAX_NSAMAX, WrxStateC


# Scalar (global) field names in canonical order.
SCALAR_FIELDS = ("pwr_tot",)


@dataclass
class WrxState:
    """Pure-Python snapshot of ``wrx_state_t``.

    Attributes:
        nraymax:           number of rays actually in use
        nstpmax:           NSTPMAX used for this run
        nsamax:            number of species actually in use
        nsmax:             NSMAX (plasma species count)
        modelg:            MODELG model switch
        mdlwrq:            MDLWRQ power-deposition switch
        scalars:           dict with {"pwr_tot": total absorbed power}
        nstp_end:          [nraymax] end-step index for each ray
                           (alias of ``nstpmax_nray``)
        pwr_nray:          [nraymax] per-ray absorbed power
        pwr_nsa:           [nsamax]  per-species absorbed power
        pwr_nsa_nray:      [nraymax][nsamax] per-ray per-species power
        pos_pwrmax_rs_nsa: [nsamax] peak-power position (rs axis) by species
        pwrmax_rs_nsa:     [nsamax] peak-power value    (rs axis) by species
        pos_pwrmax_rl_nsa: [nsamax] peak-power position (rl axis) by species
        pwrmax_rl_nsa:     [nsamax] peak-power value    (rl axis) by species
    """

    nraymax: int
    nstpmax: int
    nsamax: int
    nsmax: int
    modelg: int
    mdlwrq: int
    scalars: Dict[str, float]
    nstp_end: List[int] = field(default_factory=list)
    pwr_nray: List[float] = field(default_factory=list)
    pwr_nsa: List[float] = field(default_factory=list)
    pwr_nsa_nray: List[List[float]] = field(default_factory=list)
    pos_pwrmax_rs_nsa: List[float] = field(default_factory=list)
    pwrmax_rs_nsa: List[float] = field(default_factory=list)
    pos_pwrmax_rl_nsa: List[float] = field(default_factory=list)
    pwrmax_rl_nsa: List[float] = field(default_factory=list)

    @classmethod
    def from_c(cls, s: WrxStateC) -> "WrxState":
        """Build a WrxState from a populated :class:`WrxStateC`.

        Only ``[0:nraymax]`` / ``[0:nsamax]`` slices are copied out;
        trailing padding (up to ``WRX_MAX_*``) is ignored so zero-
        padded struct tails do not leak into the Python view.
        """
        nray = int(s.nraymax)
        nsa = int(s.nsamax)
        scalars = {k: float(getattr(s, k)) for k in SCALAR_FIELDS}
        nstp_end = [int(s.nstpmax_nray[i]) for i in range(nray)]
        pwr_nray = [float(s.pwr_nray[i]) for i in range(nray)]
        pwr_nsa = [float(s.pwr_nsa[j]) for j in range(nsa)]
        # 2D: C layout [NRAYMAX][NSAMAX]; slice the active corner only.
        pwr_nsa_nray = [
            [float(s.pwr_nsa_nray[i][j]) for j in range(nsa)]
            for i in range(nray)
        ]
        pos_pwrmax_rs_nsa = [float(s.pos_pwrmax_rs_nsa[j]) for j in range(nsa)]
        pwrmax_rs_nsa = [float(s.pwrmax_rs_nsa[j]) for j in range(nsa)]
        pos_pwrmax_rl_nsa = [float(s.pos_pwrmax_rl_nsa[j]) for j in range(nsa)]
        pwrmax_rl_nsa = [float(s.pwrmax_rl_nsa[j]) for j in range(nsa)]
        return cls(
            nraymax=nray,
            nstpmax=int(s.nstpmax),
            nsamax=nsa,
            nsmax=int(s.nsmax),
            modelg=int(s.modelg),
            mdlwrq=int(s.mdlwrq),
            scalars=scalars,
            nstp_end=nstp_end,
            pwr_nray=pwr_nray,
            pwr_nsa=pwr_nsa,
            pwr_nsa_nray=pwr_nsa_nray,
            pos_pwrmax_rs_nsa=pos_pwrmax_rs_nsa,
            pwrmax_rs_nsa=pwrmax_rs_nsa,
            pos_pwrmax_rl_nsa=pos_pwrmax_rl_nsa,
            pwrmax_rl_nsa=pwrmax_rl_nsa,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialisable dict in the ``rays`` / ``profile_rs`` / ``profile_rl``
        shape used by :mod:`wrlib.state`.

        ``rays`` is indexed by the NRAY axis; ``profile_rs`` /
        ``profile_rl`` are indexed by the NSA (species) axis because
        WRX's per-species power deposition replaces WR's radial
        profile in the C ABI.
        """
        return {
            "NRAYMAX": self.nraymax,
            "NSTPMAX": self.nstpmax,
            "NSAMAX": self.nsamax,
            "NSMAX": self.nsmax,
            "MODELG": self.modelg,
            "MDLWRQ": self.mdlwrq,
            "scalars": dict(self.scalars),
            "rays": [
                {
                    "NRAY": i + 1,
                    "nstp_end": self.nstp_end[i],
                    "pwr": self.pwr_nray[i],
                    "pwr_nsa": list(self.pwr_nsa_nray[i]),
                }
                for i in range(self.nraymax)
            ],
            "profile_rs": [
                {
                    "NSA": j + 1,
                    "pos_pwrmax": self.pos_pwrmax_rs_nsa[j],
                    "pwrmax": self.pwrmax_rs_nsa[j],
                    "pwr": self.pwr_nsa[j],
                }
                for j in range(self.nsamax)
            ],
            "profile_rl": [
                {
                    "NSA": j + 1,
                    "pos_pwrmax": self.pos_pwrmax_rl_nsa[j],
                    "pwrmax": self.pwrmax_rl_nsa[j],
                }
                for j in range(self.nsamax)
            ],
        }


__all__ = ["WrxState", "SCALAR_FIELDS", "WRX_MAX_NSAMAX"]
