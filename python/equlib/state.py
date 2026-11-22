"""``EquState``: a snapshot of ``equ_state_t``, sliced to the valid sizes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._ffi import EquStateC

SCALARS = (
    "mode", "fct_steps", "fct_converged", "xpoint_status", "erreq",
    "raxis", "zaxis", "psi_axis", "rsep", "zsep", "psi_sep",
    "ip", "ip_target", "rbt", "beta_t", "beta_s", "beta_j", "li",
    "q_axis", "q_surf", "q95", "qqj",
    "rmaj", "rpla", "elip", "trig", "el95", "volume",
)
PROFILES = ("psi", "psit", "pressure", "q", "f", "vol", "rminor", "rcentre",
            "kappa", "delta")


@dataclass
class EquState:
    nr: int
    nz: int
    nv: int
    nsu: int
    scalars: dict[str, float] = field(default_factory=dict)
    cvac: list[float] = field(default_factory=list)
    rg: list[float] = field(default_factory=list)
    zg: list[float] = field(default_factory=list)
    profiles: dict[str, list[float]] = field(default_factory=dict)
    rsu: list[float] = field(default_factory=list)
    zsu: list[float] = field(default_factory=list)

    @classmethod
    def from_c(cls, c: EquStateC) -> "EquState":
        nr, nz, nv, nsu = c.nr, c.nz, c.nv, c.nsu
        return cls(
            nr=nr, nz=nz, nv=nv, nsu=nsu,
            scalars={k: getattr(c, k) for k in SCALARS},
            cvac=list(c.cvac),
            rg=list(c.rg[:nr]), zg=list(c.zg[:nz]),
            profiles={k: list(getattr(c, k)[:nv]) for k in PROFILES},
            rsu=list(c.rsu[:nsu]), zsu=list(c.zsu[:nsu]),
        )

    def __getattr__(self, name: str) -> Any:
        # state.q_axis, state.pressure, ... for convenience.
        d = self.__dict__
        if "scalars" in d and name in d["scalars"]:
            return d["scalars"][name]
        if "profiles" in d and name in d["profiles"]:
            return d["profiles"][name]
        raise AttributeError(name)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable, upper-case keys (EQ's to_dict convention)."""
        return {
            "NR": self.nr, "NZ": self.nz, "NV": self.nv, "NSU": self.nsu,
            "scalars": {k.upper(): v for k, v in self.scalars.items()},
            "CVAC": self.cvac, "RG": self.rg, "ZG": self.zg,
            "profiles": {k.upper(): v for k, v in self.profiles.items()},
            "RSU": self.rsu, "ZSU": self.zsu,
        }
