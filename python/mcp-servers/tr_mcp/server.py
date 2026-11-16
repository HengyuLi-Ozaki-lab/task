"""FastMCP server exposing the TASK/TR library as MCP tools.

Entry point for ``python -m tr_mcp.server`` or the ``tr-mcp`` console
script declared in :file:`pyproject.toml`.

Design notes
------------
* **One `Trlib` instance per server process.** libtrapi.so holds
  Fortran COMMON-block singleton state, so there is at most one live
  handle. Subsequent ``init`` calls close the old handle and re-open a
  fresh one so that an LLM can "start over" without restarting the
  server.
* **FastMCP decorator API** (`mcp.server.fastmcp.FastMCP`). Each tool
  is a plain Python function with type hints; the SDK generates the
  JSON Schema advertised to the client automatically.
* **Error mapping.** `trlib.TrlibError` subclasses are re-raised as
  `ToolError` with a human-readable message. The LLM sees the error
  string and can often recover (e.g. by calling ``init`` first).

The server is intentionally small — the real heavy lifting is in
:mod:`trlib`. Adding new modules (ti / wr / wrx / fp) should be a
matter of copying this file and swapping the backing library.

fd-isolation (Fortran WRITE(6) vs MCP JSON-RPC)
-----------------------------------------------
Fortran WRITE(6,...) targets OS fd 1, which is also the JSON-RPC write
pipe to the MCP client parent.  Any Fortran diagnostic line corrupts the
pipe: the client logs "Failed to parse JSONRPC message from server" for
each junk line, and in the worst case the session drops with
"Connection closed".

main() therefore calls ``_fd_isolation.install()`` (the module shared by
the stdio servers, ``python/_fd_isolation.py``) immediately before the
stdio server is built -- NOT at import time, see #227 item 1.
It moves the pipe to a descriptor of its own, rebuilds ``sys.stdout`` on
it and gives fd 1 to stderr, so that Fortran WRITE(6,...) lands in the
server's log.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# ---------------------------------------------------------------------
# Make ``trlib`` importable without a wheel install.
#
# This file lives at
#   <repo>/python/mcp-servers/tr_mcp/server.py
# and we want to import ``trlib`` from
#   <repo>/python/trlib/
# so prepend ``<repo>/python`` to sys.path if not already there.
# ---------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_PYTHON_ROOT = _HERE.parents[2]  # .../python
if str(_PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(_PYTHON_ROOT))

# ---------------------------------------------------------------------
# MCP SDK import.
#
# `mcp` is an external dependency. We import lazily so that tooling
# (syntax check, `-m py_compile`) can still parse this file even when
# the SDK is not installed in the current environment.
# ---------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]

    try:
        from mcp.server.fastmcp.exceptions import ToolError  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - older mcp layouts
        ToolError = RuntimeError  # type: ignore[assignment,misc]
    MCP_AVAILABLE = True
except Exception:  # pragma: no cover - MCP SDK not installed
    FastMCP = None  # type: ignore[assignment,misc]
    ToolError = RuntimeError  # type: ignore[assignment,misc]
    MCP_AVAILABLE = False

# ---------------------------------------------------------------------
# trlib import (always available from the repo).
# ---------------------------------------------------------------------
from trlib import (  # noqa: E402
    Trlib,
    TrlibError,
    TrlibInitError,
    TrlibParamError,
    TrlibStateError,
    TrlibRunError,
    TrlibNotImplementedError,
)

# The fd isolation shared by the stdio servers; it lives beside the wrapper,
# in ``<repo>/python/``.
import _fd_isolation  # noqa: E402


# =====================================================================
# Parameter & state schema metadata.
#
# Keeping these in Python (rather than re-parsing tr_param_registry.f90)
# is a deliberate short-term choice: the LLM-facing description is more
# valuable than the last ounce of DRYness. When the Fortran registry
# changes we'll mirror it here.
# =====================================================================
# Includes `str` for string-valued parameters like KNAMEQ / MODELG
# (set via trlib.Trlib.set_param_str).
SupportedValue = Union[float, int, str, List[float], Dict[int, float]]


PARAMETER_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- geometry / device ------------------------------------------
    "RR":     {"type": "float", "group": "geometry",     "description": "major radius [m]"},
    "RA":     {"type": "float", "group": "geometry",     "description": "minor radius [m]"},
    "RKAP":   {"type": "float", "group": "geometry",     "description": "plasma elongation"},
    "RDLT":   {"type": "float", "group": "geometry",     "description": "plasma triangularity"},
    "BB":     {"type": "float", "group": "geometry",     "description": "toroidal field on axis [T]"},
    "PHIA":   {"type": "float", "group": "geometry",     "description": "plasma surface toroidal flux [Wb]"},
    "MODELG": {"type": "int",   "group": "geometry",     "description": "equilibrium/geometry selector"},
    # --- plasma arrays (1..NSMM) ------------------------------------
    "NSMAX":  {"type": "int",   "group": "plasma",       "description": "number of species"},
    "NRMAX":  {"type": "int",   "group": "plasma",       "description": "TR radial mesh points"},
    "PA":     {"type": "float[NSMM]", "group": "plasma", "description": "atomic mass per species (1-origin)"},
    "PZ":     {"type": "float[NSMM]", "group": "plasma", "description": "charge number per species"},
    "PN":     {"type": "float[NSMM]", "group": "plasma", "description": "initial density per species [10^20 m^-3]"},
    "PNS":    {"type": "float[NSMM]", "group": "plasma", "description": "edge (separatrix) density per species"},
    "PT":     {"type": "float[NSMM]", "group": "plasma", "description": "initial temperature per species [keV]"},
    "PTS":    {"type": "float[NSMM]", "group": "plasma", "description": "edge temperature per species [keV]"},
    "PROFN1": {"type": "float", "group": "plasma",       "description": "density profile parameter"},
    "PROFN2": {"type": "float", "group": "plasma",       "description": "density profile parameter"},
    "PNC":    {"type": "float", "group": "plasma",       "description": "impurity density"},
    "MDLIMP": {"type": "int",   "group": "plasma",       "description": "impurity model selector"},
    # --- current / time --------------------------------------------
    "RIPS":   {"type": "float", "group": "current",      "description": "plasma current at start [MA]"},
    "RIPE":   {"type": "float", "group": "current",      "description": "plasma current at end [MA]"},
    "DT":     {"type": "float", "group": "time",         "description": "time step [s]"},
    "NTMAX":  {"type": "int",   "group": "time",         "description": "max number of steps (per run)"},
    "NTSTEP": {"type": "int",   "group": "time",         "description": "output cadence"},
    "EPSLTR": {"type": "float", "group": "time",         "description": "convergence tolerance"},
    "LMAXTR": {"type": "int",   "group": "time",         "description": "max inner-iteration count"},
    "NTEQIT": {"type": "int",   "group": "time",         "description": "EQ re-solve interval in steps under MODELG=9 (0 = never)"},
    "NGTSTP": {"type": "int",   "group": "time",         "description": "graphics-output cadence (steps)"},
    "NGRSTP": {"type": "int",   "group": "time",         "description": "graphics-output cadence (radial)"},
    # --- transport coefficients ------------------------------------
    "MDLKAI": {"type": "int",   "group": "transport",    "description": "thermal-diffusivity model"},
    "MDLETA": {"type": "int",   "group": "transport",    "description": "resistivity model"},
    "MDLAD":  {"type": "int",   "group": "transport",    "description": "particle-diffusion model"},
    "MDLAVK": {"type": "int",   "group": "transport",    "description": "convection model"},
    "CDW":    {"type": "float[]", "group": "transport",  "description": "drift-wave tuning coefficients (array, 1-origin)"},
    "CHP":    {"type": "float", "group": "transport",    "description": "tuning coefficient"},
    "CK0":    {"type": "float", "group": "transport",    "description": "tuning coefficient"},
    "CK1":    {"type": "float", "group": "transport",    "description": "tuning coefficient"},
    "CDH":    {"type": "float", "group": "transport",    "description": "turbulent heat-diffusivity sum weight"},
    "CNH":    {"type": "float", "group": "transport",    "description": "neoclassical heat-diffusivity sum weight"},
    # --- module switches -------------------------------------------
    "MDLNB":  {"type": "int", "group": "modules", "description": "NBI heating module"},
    "MDLEC":  {"type": "int", "group": "modules", "description": "ECRF heating module"},
    "MDLLH":  {"type": "int", "group": "modules", "description": "LH heating module"},
    "MDLIC":  {"type": "int", "group": "modules", "description": "ICRF heating module"},
    "MDLPEL": {"type": "int", "group": "modules", "description": "pellet injection module"},
    "MDLJBS": {"type": "int", "group": "modules", "description": "bootstrap-current model"},
    "MDLST":  {"type": "int", "group": "modules", "description": "sawtooth model"},
    "TPRST":  {"type": "float", "group": "modules", "description": "sawtooth period [s]"},
    "MDLNF":  {"type": "int", "group": "modules", "description": "neutron/fusion module"},
    "MDLUF":  {"type": "int", "group": "modules", "description": "UFILE I/O mode"},
    # --- heating / current-drive scalars ---------------------------
    "PNBTOT": {"type": "float", "group": "nbi",  "description": "NBI total input power [MW]"},
    "PNBR0":  {"type": "float", "group": "nbi",  "description": "NBI deposition center [m]"},
    "PNBRW":  {"type": "float", "group": "nbi",  "description": "NBI deposition width [m]"},
    "PNBENG": {"type": "float", "group": "nbi",  "description": "NBI beam energy [keV]"},
    "PNBRTG": {"type": "float", "group": "nbi",  "description": "NBI tangency radius [m]"},
    "PICCD":  {"type": "float", "group": "icrf", "description": "ICRF CD efficiency"},
    "PICR0":  {"type": "float", "group": "icrf", "description": "ICRF deposition center"},
    "PICRW":  {"type": "float", "group": "icrf", "description": "ICRF deposition width"},
    "PICNPR": {"type": "float", "group": "icrf", "description": "ICRF parallel index"},
    "PICTOT": {"type": "float", "group": "icrf", "description": "ICRF total input power [MW]"},
    "PECCD":  {"type": "float", "group": "ecrf", "description": "ECRF CD efficiency"},
    "PECR0":  {"type": "float", "group": "ecrf", "description": "ECRF deposition center"},
    "PECRW":  {"type": "float", "group": "ecrf", "description": "ECRF deposition width"},
    "PECNPR": {"type": "float", "group": "ecrf", "description": "ECRF parallel index"},
    "PECTOT": {"type": "float", "group": "ecrf", "description": "ECRF total input power [MW]"},
    "PLHCD":  {"type": "float", "group": "lh",   "description": "LH CD efficiency"},
    "PLHR0":  {"type": "float", "group": "lh",   "description": "LH deposition center"},
    "PLHRW":  {"type": "float", "group": "lh",   "description": "LH deposition width"},
    "PLHNPR": {"type": "float", "group": "lh",   "description": "LH parallel index"},
    "PLHTOT": {"type": "float", "group": "lh",   "description": "LH total power [MW]"},
    # --- NCLASS, equations solved, current profile, particle transport
    "MDNCLS": {"type": "int",   "group": "transport", "description": "neoclassical transport, resistivity and bootstrap current: 0 = the MDLAD/MDLETA/MDLJBS models, else NCLASS"},
    "MDLEQB": {"type": "int",   "group": "modules",   "description": "B_theta (current) equation: 1 = evolved, 0 = held at the start profile (MODELG 3 reloads psi from EQ every step)"},
    "MDLEQN": {"type": "int",   "group": "modules",   "description": "density equations: 0 = densities held, 1 = evolved"},
    "MDLEQE": {"type": "int",   "group": "modules",   "description": "with MDLEQN 1: 0 = electrons from quasi-neutrality, 1 = both solved, 2 = bulk ions from quasi-neutrality (2 only with NSMAX 2, species 2 H or D, no impurity, no UFILE)"},
    "PROFJ1": {"type": "float", "group": "current",   "description": "start current profile, MODELG 2 only: <= 0 j from the resistivity (j ~ 1/eta), > 0 j ~ (1 - rho^|PROFJ1|)^|PROFJ2|"},
    "PROFJ2": {"type": "float", "group": "current",   "description": "start current profile exponent, with PROFJ1 > 0"},
    "AD0":    {"type": "float", "group": "transport", "description": "particle diffusivity: a factor of chi_turb (MDLAD 2-4, NCLASS) or a constant D (MDLAD 1)"},
    "AV0":    {"type": "float", "group": "transport", "description": "turbulent inward pinch factor (MDLAD 1, 2, 4)"},
    "CDP":    {"type": "float", "group": "transport", "description": "turbulent particle-diffusivity sum weight"},
    "CNP":    {"type": "float", "group": "transport", "description": "neoclassical particle-diffusivity sum weight"},
    # --- particle source (gas puff), arrays 1..NPSCM = 10 -------------
    "MDLPSC":  {"type": "int",          "group": "fueling", "description": "particle source: 0 = none, 1 = Gaussian sources"},
    "NPSCMAX": {"type": "int",          "group": "fueling", "description": "number of particle sources (0..10)"},
    "PSCTOT":  {"type": "float[NPSCM]", "group": "fueling", "description": "total rate of each source [10^20 /s]"},
    "PSCR0":   {"type": "float[NPSCM]", "group": "fueling", "description": "centre of each source [m] (minor radius RA*rho, not rho)"},
    "PSCRW":   {"type": "float[NPSCM]", "group": "fueling", "description": "width of each source [m], at least 1e-10"},
    "NSPSC":   {"type": "int[NPSCM]",   "group": "fueling", "description": "ion species each source feeds (2..NSMAX; the electrons follow)"},
    # --- string parameter (set via set_param_str under the hood) ----
    "KNAMEQ": {"type": "str", "group": "io", "description": "equilibrium data file name"},
}


# The global results the library names (``Trlib.scalar_names()``), with the unit each has in
# tr/trrslt_globals.f90. tests/test_scalar_schema.py fails for a name the library lists and this table lacks.
SCALAR_SCHEMA: Dict[str, Dict[str, str]] = {
    "T":      {"unit": "s",   "description": "time"},
    "WPT":    {"unit": "MJ",  "description": "stored energy of the bulk species and the fast ions"},
    "AJT":    {"unit": "MA",  "description": "total plasma current"},
    "Q0":     {"unit": "",    "description": "safety factor on axis"},
    "BETA0":  {"unit": "",    "description": "central toroidal beta (fraction)"},
    "BETAP0": {"unit": "",    "description": "central poloidal beta"},
    "BETAA":  {"unit": "",    "description": "volume-averaged toroidal beta (fraction)"},
    "BETAN":  {"unit": "% m T / MA", "description": "normalised toroidal beta (Troyon), 100 BETAA / (RIP / (RA BB))"},
    "TAUE1":  {"unit": "s",   "description": "energy confinement time, steady state: WPT / PINT"},
    "TAUE2":  {"unit": "s",   "description": "energy confinement time, transient: WPT / (PINT - WPDOT)"},
    "ZEFF0":  {"unit": "",    "description": "effective charge number on axis"},
    "ALI":    {"unit": "",    "description": "internal inductance"},
    "RQ1":    {"unit": "m",   "description": "distance of the q = 1 surface from the axis (0 when q0 >= 1)"},
    "AJRFT":  {"unit": "MA",  "description": "RF and external driven current"},
    "PNFT":   {"unit": "MW",  "description": "fusion alpha power (P_fus = 5 PNFT for D-T)"},
    "QF":     {"unit": "",    "description": "fusion gain: 5 PNFT / (POHT + PNBT + PRFST + PEXST)"},
    "PINT":   {"unit": "MW",  "description": "total input power: POHT + PNBT + PRFST + PNFT + PEXST (alpha power included)"},
    "POHT":   {"unit": "MW",  "description": "ohmic power"},
    "PNBT":   {"unit": "MW",  "description": "neutral-beam power"},
    "PRFST":  {"unit": "MW",  "description": "RF power, all species"},
    "PEXST":  {"unit": "MW",  "description": "external power from experimental data, all species"},
    "PRLT":   {"unit": "MW",  "description": "radiation loss (line)"},
    "POUT":   {"unit": "MW",  "description": "total output power: conduction, charge exchange, ionisation, radiation"},
    "AJOHT":  {"unit": "MA",  "description": "ohmic current"},
    "AJNBT":  {"unit": "MA",  "description": "neutral-beam driven current"},
    "AJBST":  {"unit": "MA",  "description": "bootstrap current"},
    "RIP":    {"unit": "MA",  "description": "boundary (programmed) plasma current at this time"},
    "VLOOP":  {"unit": "V",   "description": "one-turn voltage at the edge"},
    "WPDOT":  {"unit": "MW",  "description": "rate of change of WPT between the last two global evaluations"},
    "H98Y2":  {"unit": "",    "description": "H factor: TAUE2 / TAUE98"},
    "TAUE98": {"unit": "s",   "description": "IPB98(y,2) confinement time scaling"},
}


# The columns of the time history (``Trlib.history_names()``), with units from tr/trrslt_globals.f90 TRATOT.
# Values are single precision. tests/test_history_schema.py fails for a column the library lists and this lacks.
HISTORY_SCHEMA: Dict[str, Dict[str, str]] = {
    "T": {"unit": "s", "description": "time of the row"},
    "NE0": {"unit": "1e20 m^-3", "description": "electron density on axis"},
    "NEAV": {"unit": "1e20 m^-3", "description": "electron density, volume average"},
    "TE0": {"unit": "keV", "description": "electron temperature on axis"},
    "TI0": {"unit": "keV", "description": "temperature of the first bulk ion species (species 2) on axis"},
    "TEAV": {"unit": "keV", "description": "electron temperature, density-weighted volume average"},
    "TIAV": {"unit": "keV", "description": "temperature of the first bulk ion species, density-weighted volume average"},
    "WPT": {"unit": "MJ", "description": "stored energy"},
    "AJT": {"unit": "MA", "description": "total plasma current"},
    "AJOHT": {"unit": "MA", "description": "ohmic current"},
    "AJNBT": {"unit": "MA", "description": "neutral-beam driven current"},
    "AJRFT": {"unit": "MA", "description": "RF and external driven current"},
    "AJBST": {"unit": "MA", "description": "bootstrap current"},
    "PINT": {"unit": "MW", "description": "total input power, alpha power included"},
    "POHT": {"unit": "MW", "description": "ohmic power"},
    "PNBT": {"unit": "MW", "description": "neutral-beam power"},
    "PRFE": {"unit": "MW", "description": "RF power into species 1 (electrons)"},
    "PRFD": {"unit": "MW", "description": "RF power into species 2 (first bulk ion)"},
    "PNFT": {"unit": "MW", "description": "fusion alpha power"},
    "POUT": {"unit": "MW", "description": "total output power"},
    "VLOOP": {"unit": "V", "description": "one-turn voltage at the edge"},
    "ALI": {"unit": "", "description": "internal inductance"},
    "RQ1": {"unit": "m", "description": "distance of the q = 1 surface from the axis"},
    "Q0": {"unit": "", "description": "safety factor on axis"},
    "WPDOT": {"unit": "MW", "description": "rate of change of the stored energy"},
    "TAUE1": {"unit": "s", "description": "energy confinement time, steady state"},
    "TAUE2": {"unit": "s", "description": "energy confinement time, transient"},
    "BETAP0": {"unit": "", "description": "central poloidal beta"},
    "BETA0": {"unit": "", "description": "central toroidal beta (fraction)"},
    "BETAA": {"unit": "", "description": "volume-averaged toroidal beta (fraction)"},
    "ZEFF0": {"unit": "", "description": "effective charge number on axis"},
    "QF": {"unit": "", "description": "fusion gain 5 PNFT / (POHT + PNBT + PRFST + PEXST)"},
    "RIP": {"unit": "MA", "description": "boundary plasma current at the row's time"},
    "PEXE": {"unit": "MW", "description": "external power into species 1 (electrons)"},
    "PEXI": {"unit": "MW", "description": "external power into species 2 (first bulk ion)"},
    "PECE": {"unit": "MW", "description": "EC heating of electrons"},
    "PECI": {"unit": "MW", "description": "EC heating of ions"},
    "PLHE": {"unit": "MW", "description": "LH heating of electrons"},
    "PLHI": {"unit": "MW", "description": "LH heating of ions"},
    "PICE": {"unit": "MW", "description": "IC heating of electrons"},
    "PICI": {"unit": "MW", "description": "IC heating of ions"},
    "TAUE98": {"unit": "s", "description": "IPB98(y,2) confinement time scaling"},
    "H98Y2": {"unit": "", "description": "H factor TAUE2 / TAUE98"},
    "NLAV": {"unit": "1e20 m^-3", "description": "line-averaged electron density"},
    "PRLT": {"unit": "MW", "description": "radiation loss (line)"},
    "BETAN": {"unit": "% m T / MA", "description": "normalised toroidal beta, 100 BETAA / (RIP / (RA BB)); computed from the row's columns"},
    "PRFST": {"unit": "MW", "description": "RF power into the four species, sum of the four PRFT columns; computed from the row's columns"},
}


STATE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "title": "TrState (trlib.state.TrState.to_dict() with all the named scalars)",
    "properties": {
        "NT":    {"type": "integer", "description": "current time-step index"},
        "NRMAX": {"type": "integer", "description": "radial points in use"},
        "NSMAX": {"type": "integer", "description": "species in use"},
        "scalars": {
            "type": "object",
            "description": (
                "the library's named global results (31), each as of the last step TR computed them on; "
                "units are in each entry"
            ),
            "properties": {
                name: {"type": "number", **entry} for name, entry in SCALAR_SCHEMA.items()
            },
        },
        "profile": {
            "type": "array",
            "description": "radial profile, length = NRMAX",
            "items": {
                "type": "object",
                "properties": {
                    "NR": {"type": "integer", "description": "1-origin radial index"},
                    "RN": {"type": "array", "items": {"type": "number"}, "description": "density per species (length NSMAX)"},
                    "RT": {"type": "array", "items": {"type": "number"}, "description": "temperature per species"},
                    "AJ": {"type": "number", "description": "current density"},
                    "QP": {"type": "number", "description": "safety factor"},
                },
            },
        },
    },
    "required": ["NT", "NRMAX", "NSMAX", "scalars", "profile"],
}


# =====================================================================
# Server state (process-wide singleton).
# =====================================================================
class _ServerState:
    """Holds the single live :class:`Trlib` instance for this server."""

    def __init__(self) -> None:
        self.tr: Optional[Trlib] = None

    def ensure_open(self) -> Trlib:
        """Return the live handle, opening one if needed."""
        if self.tr is None or self.tr.closed:
            self.tr = Trlib()
        return self.tr

    def close(self) -> None:
        if self.tr is not None and not self.tr.closed:
            self.tr.close()
        self.tr = None


STATE = _ServerState()


# =====================================================================
# Helpers — parameter application.
# =====================================================================
def _short(text: str, limit: int) -> str:
    """``text`` for an error message: its start, when it is longer than ``limit``."""
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _number(key: str, value: Any) -> float:
    """``value`` as the float the library is given for ``key``.

    Raises :class:`TrlibError` for what ``float()`` does not take (a string
    that is no number, ``None``), for an integer too large for a float
    (``float()`` raises ``OverflowError``), and for a number that is not
    finite: ``float()`` also takes ``"nan"``, ``"inf"`` and ``"1e309"``,
    and no parameter has such a value.
    """
    key = _short(key, 80)
    if isinstance(value, int) and abs(value) >= 10**30:
        shown = "an integer of more than 30 digits"   # Python does not print one of 4300
    else:
        shown = _short(repr(value), 60)
    try:
        coerced = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        reason = _short(str(exc), 80)                 # float() repeats the string it refuses
        raise TrlibError(
            f"invalid numeric value for '{key}': {shown} ({reason})"
        ) from exc
    if not math.isfinite(coerced):
        raise TrlibError(
            f"invalid numeric value for '{key}': {shown} (not finite)"
        )
    return coerced


def _apply_bulk_params(tr: Trlib, params: Dict[str, SupportedValue]) -> List[str]:
    """Apply a bulk ``params`` dict, returning the list of applied keys.

    Accepted value shapes per key:

    * scalar (``float`` / ``int``)   — plain :py:meth:`Trlib.set_param`.
    * ``list`` / ``tuple``          — element at 1-origin index ``i``
      is applied as ``NAME[i]``.
    * ``dict[int, float]``          — sparse {index: value}, applied as
      ``NAME[index]``; indices must be 1-origin.
    * ``str``                       — forwarded to
      :py:meth:`Trlib.set_param_str` (e.g. ``KNAMEQ``).

    .. warning::

       This routine is **non-transactional**: parameters are forwarded
       to the underlying Fortran library one at a time and a failure
       partway through leaves earlier writes in place. Callers that
       need rollback semantics must validate the input dict (and snap
       the prior state) themselves. A two-pass dry-run + apply is
       tracked as a follow-up.
    """
    applied: List[str] = []
    for name, value in params.items():
        # Reject bool early: bool is a subclass of int and would be
        # silently coerced by float(); the contract is explicit numbers.
        if isinstance(value, bool):
            raise TrlibError(
                f"unsupported value type for '{name}': bool (use 0/1)"
            )
        if isinstance(value, (list, tuple)):
            for i, v in enumerate(value, start=1):
                key = f"{name}[{i}]"
                # Nested bool: subclass of int would be coerced to 1.0
                # by float() — reject before float() so the top-level
                # bool contract also holds inside bulk arrays.
                if isinstance(v, bool):
                    raise TrlibError(
                        f"unsupported value type for '{key}': "
                        f"bool (use 0/1)"
                    )
                tr.set_param(key, _number(key, v))
                applied.append(key)
        elif isinstance(value, dict):
            for idx, v in value.items():
                # Reject bool keys AND bool values up-front; int(True)
                # == 1 would otherwise silently land in NAME[1].
                if isinstance(idx, bool):
                    raise TrlibError(
                        f"invalid index for '{name}': bool (use 0/1)"
                    )
                if isinstance(v, bool):
                    raise TrlibError(
                        f"unsupported value type for '{name}[{idx}]': "
                        f"bool (use 0/1)"
                    )
                try:
                    int_idx = int(idx)
                except (TypeError, ValueError) as exc:
                    raise TrlibError(
                        f"invalid index for '{name}': {idx!r} ({exc})"
                    ) from exc
                key = f"{name}[{int_idx}]"
                tr.set_param(key, _number(key, v))
                applied.append(key)
        elif isinstance(value, str):
            # String-valued (e.g. KNAMEQ). Requires libtrapi.so with L-6
            # extension; otherwise trlib raises TrlibError with a
            # helpful message, which _wrap will translate.
            tr.set_param_str(name, value)
            applied.append(name)
        elif isinstance(value, (int, float)):
            tr.set_param(name, _number(name, value))
            applied.append(name)
        else:
            raise TrlibError(
                f"unsupported value type for '{name}': {type(value).__name__}"
            )
    return applied


def _wrap_trlib_error(exc: Exception) -> "ToolError":  # noqa: F821
    """Translate a trlib exception into the MCP ToolError class.

    Kept as a helper so tests can assert the mapping without depending
    on the MCP SDK being installed.
    """
    if isinstance(exc, TrlibParamError):
        msg = f"invalid parameter: {exc}"
    elif isinstance(exc, TrlibStateError):
        msg = f"library not initialized (call init first): {exc}"
    elif isinstance(exc, TrlibRunError):
        msg = f"calculation failed: {exc}"
        failure = getattr(exc, "failure", None)
        if failure is not None and failure.kind != "NONE":
            # The library's record of what failed (tr_last_error), in the same string.
            msg += (
                f" [failure: kind={failure.kind} code={failure.code} "
                f"nt={failure.nt} time={failure.time:g} s; {failure.detail}]"
            )
    elif isinstance(exc, TrlibNotImplementedError):
        msg = f"not implemented in this libtrapi.so build: {exc}"
    elif isinstance(exc, TrlibInitError):
        msg = f"tr_init failed: {exc}"
    elif isinstance(exc, TrlibError):
        msg = f"trlib error: {exc}"
    elif isinstance(exc, FileNotFoundError):
        msg = (
            f"libtrapi.so not found: {exc}. "
            "Build it via `make -C tr libtrapi.so` or set TRLIB_PATH."
        )
    else:
        # Unexpected — re-wrap so MCP still gets a clean error.
        msg = f"{type(exc).__name__}: {exc}"
    return ToolError(msg)  # type: ignore[operator,call-arg]


# =====================================================================
# Tool handler implementations (plain Python, unit-testable).
#
# The FastMCP-decorated tools below delegate here so that the test
# suite can exercise the same code without spinning up the MCP
# transport.
# =====================================================================
def handle_init() -> str:
    try:
        STATE.ensure_open()
        return "tr library initialized"
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def handle_set_param(name: str, value: float) -> str:
    try:
        tr = STATE.ensure_open()
        tr.set_param(name, _number(name, value))
        return f"set {name} = {value}"
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def handle_set_param_str(name: str, value: str) -> str:
    """Set a string-valued tr parameter (e.g. ``KNAMEQ``).

    Routed through :py:meth:`Trlib.set_param_str`, which requires a
    libtrapi.so built with the L-6 registry extension. Older builds
    raise :class:`TrlibError` with a rebuild hint; that message is
    translated by :func:`_wrap_trlib_error` into a human-readable
    ToolError.
    """
    try:
        tr = STATE.ensure_open()
        tr.set_param_str(name, str(value))
        return f"set {name} = {value!r}"
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def handle_set_params(params: Dict[str, SupportedValue]) -> str:
    if not isinstance(params, dict):
        raise ToolError(  # type: ignore[call-arg]
            f"set_params expects a dict; got {type(params).__name__}"
        )
    try:
        tr = STATE.ensure_open()
        applied = _apply_bulk_params(tr, params)
        return f"set {len(applied)} parameter(s): {applied}"
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def handle_run(ntmax: int = 1) -> str:
    try:
        tr = STATE.ensure_open()
        tr.run(int(ntmax))
        return f"advanced {ntmax} time step(s)"
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def _state_dict(tr: Trlib) -> Dict[str, Any]:
    """The state as the tools return it: ``to_dict()`` (the 14 scalars of the C struct, which the baselines
    compare) with ``scalars`` replaced by all the library's named global results."""
    state = tr.get_state()
    out = state.to_dict()
    out["scalars"] = dict(state.scalars)
    return out


def handle_get_state() -> Dict[str, Any]:
    try:
        return _state_dict(STATE.ensure_open())
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def handle_finalize() -> str:
    """Finalize the TR backend, mirroring ``eq_mcp.server.handle_finalize``.

    #227 item 2: this used to mark the :class:`Trlib` handle closed *without*
    calling ``tr_finalize``, as a workaround for a SIGABRT (~40% of calls) in
    the Fortran cleanup path.  That left ``g_initialized`` set in
    ``tr/tr_api.f90``, and since ``tr_init`` is idempotent (``tr_api_init`` in tr_api.f90 --
    "already initialized, just return OK") a subsequent ``init`` became a
    no-op that did **not** restore defaults.  It also disagreed with
    ``handle_run_and_get_state``, which needs a real finalize for its
    fresh-init contract and therefore kept calling the very path this one
    avoided.

    The underlying crash was a double ``DEALLOCATE`` and is fixed on this tree:
    ``DEALLOCATE_TRCOMM`` now returns early when nothing is allocated
    (tr/trcomm.f90).  Measured on the merged tree, gfortran-15/macOS:
    init+close 40/40 clean, init+run+close 40/40 clean, and an explicit double
    ``tr_finalize`` 30/30 clean (the second call returns TR_OK via the
    not-initialized guard).  So both lifecycle paths now use the honest one.
    """
    try:
        STATE.close()
        return "tr library finalized"
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def handle_describe_parameters() -> Dict[str, Any]:
    return {
        "module": "tr",
        "count": len(PARAMETER_REGISTRY),
        "array_syntax": "Use NAME[i] (1-origin) for array elements, e.g. PN[1].",
        "eq_names": (
            "A name 'eq:NAME' (e.g. eq:RB, eq:NSGMAX) is passed to the "
            "library as is and set in EQ's registry; it is not listed "
            "here, and the library refuses an unknown one. TR prepares "
            "again before its next run. eq:RR, RA, RKAP, RDLT, BB, RIP and "
            "KNAMEQ are refused (set TR's own), and so is every eq: name "
            "after the process's first preparation attempt (until the "
            "pinned bpsd has k-yoshimi/bpsd#7; for eq:RIP set RIPS and "
            "RIPE). That guard closes only the direct route: under MODELG "
            "9 any input that moves EQ's plasma grid (TR's RA, RR and "
            "other device inputs, MODELG, the eq: names, the drift "
            "between NTEQIT re-solves) needs a bpsd with "
            "k-yoshimi/bpsd#7. Under MODELG 3/5/8 EQ's NRMAX is TR's "
            "NRMAX + 1, NTHMAX is 64 and NSUMAX is 0."
        ),
        "parameters": PARAMETER_REGISTRY,
    }


def handle_describe_state_schema() -> Dict[str, Any]:
    return STATE_SCHEMA


def handle_describe_history_schema() -> Dict[str, Any]:
    return {
        "description": (
            "The columns get_history can return, each with its unit and meaning. One row is recorded every "
            "NGTSTP steps (default 2), the state at t = 0 first; a run in several calls adds nsteps / NGTSTP "
            "rows per call; a changed parameter starts the history again; at most 10001 rows are kept "
            "('full' says when they are). Values are single precision (about 7 digits)."
        ),
        "columns": HISTORY_SCHEMA,
    }


def handle_get_history(names: Optional[List[str]] = None) -> Dict[str, Any]:
    """The run's time history: ``{"rows": n, "full": bool, "columns": {name: [values]}}``.

    ``names`` selects columns (``None`` = all); an unknown name is an error that names it.
    """
    try:
        tr = STATE.ensure_open()
        data = tr.history(names)
        return {
            "rows": tr.history_length(),
            "full": tr.history_full(),
            "columns": {k: [float(x) for x in v] for k, v in data.items()},
        }
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


def handle_run_and_get_state(
    params: Optional[Dict[str, SupportedValue]] = None,
    ntmax: int = 1,
) -> Dict[str, Any]:
    """One-shot init -> set_params -> run -> get_state.

    Codex MCP audit 2026-04-22 (HIGH) fix: force-close any prior
    :class:`Trlib` handle before opening a fresh one so this call is
    genuinely isolated. Without the close, prior tool calls in the
    same MCP server process leak their parameter mutations (MODELG,
    mesh sizes, NSMAX, etc.) into the one-shot run because libtrapi.so
    holds singleton Fortran state -- the user-facing contract
    ("init + set + run + get_state") requires a fresh init each call.
    Mirrors the canonical fix in ``eq_mcp.server.handle_run_and_get_state``.
    """
    try:
        # Force a fresh handle: STATE.close() finalizes any prior Trlib,
        # then ensure_open() opens a new one. Mirrors the documented
        # init step of the one-shot contract.
        STATE.close()
        tr = STATE.ensure_open()
        if params:
            _apply_bulk_params(tr, params)
        tr.run(int(ntmax))
        return _state_dict(tr)
    except Exception as exc:
        raise _wrap_trlib_error(exc) from exc


# =====================================================================
# FastMCP server wiring.
#
# Declared only when the SDK is importable; the handle_* functions
# above are the unit-testable surface either way.
# =====================================================================
def build_server() -> Any:
    """Build and return a FastMCP server instance with the 12 tr tools."""
    if not MCP_AVAILABLE:
        raise RuntimeError(
            "Python MCP SDK (`mcp`) is not installed. "
            "Install it with: pip install 'mcp>=1.2,<2'"
        )

    mcp = FastMCP(  # type: ignore[misc]
        name="task-tr",
        instructions=(
            "TASK/TR transport-code MCP server. "
            "Call `init` first, configure parameters with `set_param` "
            "/ `set_param_str` / `set_params`, advance with `run`, and "
            "read state with `get_state`. Use `describe_parameters` to "
            "discover valid parameter names. `run_and_get_state` is a "
            "convenience one-shot wrapper. Note: `set_params` is "
            "*non-transactional* — on a partial failure, parameters "
            "applied before the failing key remain set."
        ),
    )

    @mcp.tool()
    def init() -> str:
        """Initialize the tr library with its default parameters.

        Call this once before any other tool. If the library is already
        open, this is a no-op. Subsequent explicit calls after
        `finalize` re-initialize to defaults.
        """
        return handle_init()

    @mcp.tool()
    def set_param(name: str, value: float) -> str:
        """Set a tr parameter by name.

        Use ``NAME[i]`` (1-origin) for array elements, e.g. ``PN[1]``.
        For string parameters (``KNAMEQ`` etc.) use ``set_param_str``
        instead. See `describe_parameters` for the full registry.
        """
        return handle_set_param(name, value)

    @mcp.tool()
    def set_param_str(name: str, value: str) -> str:
        """Set a tr string-valued parameter (``KNAMEQ`` etc.).

        Requires a ``libtrapi.so`` built with the L-6 registry
        extension (``make -C tr libtrapi.so``); older builds raise a
        clear "rebuild the shared library" error.
        """
        return handle_set_param_str(name, value)

    @mcp.tool()
    def set_params(params: Dict[str, Any]) -> str:
        """Bulk-set tr parameters.

        ``params`` values may be:
        * a number (scalar)
        * a list/tuple (1-origin array, all elements applied)
        * a dict ``{index: value}`` (1-origin sparse array)
        * a string (for KNAMEQ and similar string-valued parameters)

        Every number must be finite: NaN and the infinities are refused,
        also as a string in a list or a dict (``"nan"``, ``"1e309"``).

        **Non-transactional**: keys are applied in iteration order and
        a failure on key ``N`` leaves keys ``0..N-1`` already written
        to the underlying Fortran library. There is no automatic
        rollback in this PR — pre-validate with ``describe_parameters``
        if a clean rollback matters. (Two-pass dry-run + apply is
        tracked as a follow-up task.)
        """
        return handle_set_params(params)

    @mcp.tool()
    def run(ntmax: int = 1) -> str:
        """Advance the simulation by ``ntmax`` time steps.

        ``ntmax=0`` is a valid no-op (useful as a smoke test).
        """
        return handle_run(ntmax)

    @mcp.tool()
    def get_state() -> Dict[str, Any]:
        """Return the current simulation state.

        Returns a dict with ``NT``, ``NRMAX``, ``NSMAX``, ``scalars``
        (the 31 named global results, units in `describe_state_schema`),
        and ``profile`` (radial profile array).
        Schema also available via `describe_state_schema`.
        """
        return handle_get_state()

    @mcp.tool()
    def finalize() -> str:
        """Release tr library resources.

        Safe to call multiple times. After finalize, any data-returning
        tool will auto-reinitialize the library.
        """
        return handle_finalize()

    @mcp.tool()
    def describe_parameters() -> Dict[str, Any]:
        """Return the list of supported tr parameters.

        Each entry exposes ``type``, ``group``, and ``description``.
        Use this to discover valid parameter names before set_param.
        """
        return handle_describe_parameters()

    @mcp.tool()
    def describe_state_schema() -> Dict[str, Any]:
        """Return a JSON schema describing `get_state` output."""
        return handle_describe_state_schema()

    @mcp.tool()
    def get_history(names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Return the run's time history without cutting the run.

        ``names`` selects columns (``T`` is the time; `describe_history_schema`
        lists every column with its unit); omit it for all. One row is
        recorded every NGTSTP steps, the state at t = 0 first, up to 10001
        rows (``full`` says when they are used up; raise NGTSTP for a longer
        run). Returns ``rows``, ``full`` and ``columns``.
        """
        return handle_get_history(names)

    @mcp.tool()
    def describe_history_schema() -> Dict[str, Any]:
        """Return the columns `get_history` can return, with units."""
        return handle_describe_history_schema()

    @mcp.tool()
    def run_and_get_state(
        params: Optional[Dict[str, Any]] = None,
        ntmax: int = 1,
    ) -> Dict[str, Any]:
        """Convenience: init + set_params + run + get_state in one call.

        Equivalent to::

            init()
            set_params(params)
            run(ntmax)
            return get_state()
        """
        return handle_run_and_get_state(params, ntmax)

    return mcp


def main(argv: Optional[List[str]] = None) -> int:
    """Console-script entry point.

    Runs the FastMCP stdio server. Exits cleanly on SIGINT.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(
            "tr-mcp — Model Context Protocol server for TASK/TR\n"
            "\n"
            "Usage:\n"
            "  python -m tr_mcp.server    # run over stdio (default)\n"
            "  tr-mcp                     # same, via installed script\n"
            "  tr-mcp --help              # show this help\n"
            "  tr-mcp --print-tools       # list registered tools\n"
            "\n"
            "Environment:\n"
            "  TRLIB_PATH   override path to libtrapi.so\n"
            "  PYTHONPATH   must include the repo's python/ directory\n"
            "               (set automatically when running in-tree)\n"
        )
        return 0

    if "--print-tools" in argv:
        for tool in sorted(
            [
                "init",
                "set_param",
                "set_param_str",
                "set_params",
                "run",
                "get_state",
                "finalize",
                "describe_parameters",
                "describe_state_schema",
                "get_history",
                "describe_history_schema",
                "run_and_get_state",
            ]
        ):
            sys.stdout.write(tool + "\n")
        return 0

    if not MCP_AVAILABLE:
        sys.stderr.write(
            "error: Python MCP SDK (`mcp`) is not installed.\n"
            "       pip install 'mcp>=1.2,<2'\n"
        )
        return 2

    # Install the fd isolation now -- NOT at import time (#227 item 1).
    # Everything above this point (--help, --print-tools, the MCP-missing
    # error path) returns before we touch the host process's fds.
    _fd_isolation.install()

    server = build_server()
    # FastMCP >=1.2 exposes .run() for stdio transport by default.
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
