"""FastMCP server exposing TASK/EQU, the free-boundary equilibrium code.

Entry point: ``python -m equ_mcp.server`` or the ``equ-mcp`` script.
Design: ``docs/superpowers/specs/2026-11-22-equ-library-design.md``, section 12.

* One ``Equ`` per server process (EQU's state is one set of Fortran
  modules); ``init`` closes it and opens a fresh one.
* The library writes the solver's progress on unit 6: ``main`` moves fd 1
  to stderr (``python/_fd_isolation.py``) before the stdio transport starts.
* File names (``read_parm``'s path, ``KNAMCOIL``, ``write_geqdsk``'s path)
  are relative to the server's working directory.
* Errors of equlib come back as ``ToolError`` with the library's reason.
"""
from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict, List, Optional, Union

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

from equlib import (  # noqa: E402
    Equ, EqulibCalculationFailedError, EqulibError, EqulibInitError,
    EqulibInvalidParamError, EqulibNotImplementedError, EqulibNotInitializedError,
)
import _fd_isolation  # noqa: E402

# =====================================================================
# Parameter metadata: one entry per name of equ/equ_param_registry.f90
# (python/mcp-servers/equ_mcp/tests/test_server.py holds the two to each
# other). Defaults are eqinit's (equ/equinit.f90), the JT-60U case.
# Arrays: NAME[i] with Fortran's index.
# =====================================================================
SupportedValue = Union[float, int, str, List[float], Dict[int, float]]


def _p(type_: str, group: str, default: Any, description: str) -> Dict[str, Any]:
    return {"type": type_, "group": group, "default": default, "description": description}


PARAMETER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "DEVICE": _p("str[8]", "device", "JT60U", "device name"),
    "DEVNAM": _p("str[8]", "device", "JT60U", "device name kept by the run (eqflin sets it to DEVICE)"),
    "TITLE": _p("str[70]", "device", "", "job title (not used in the output)"),
    "NR": _p("int", "mesh", 257, "grid points in R: 2**k+1 in 5..257 (the Buneman solver)"),
    "NZ": _p("int", "mesh", 257, "grid points in Z: 2**k+1 in 5..257 (the Buneman solver)"),
    "NV": _p("int", "mesh", 101, "flux surfaces, 3..101 (4.. with |ICP[1]| = 9)"),
    "NSUMAX": _p("int", "mesh", 101, "most plasma-surface points the boundary routine eqbnd uses, "
                 "3..1542; not the G-EQDSK file's count (the traced contour, nsu)"),
    "IUDSYM": _p("int", "mesh", 0, "up-down symmetry: 1 symmetric, 0 not"),
    "RWMN": _p("float", "mesh", 1.90, "R of the box's inner edge [m] (eqchek may lower it)"),
    "RWMX": _p("float", "mesh", 4.20, "R of the box's outer edge [m] (eqchek may raise it)"),
    "ZWMX": _p("float", "mesh", 1.20, "half height of the box, |Z| < ZWMX [m] (eqchek may raise it)"),
    "BTV": _p("float", "plasma", 13.5, "R*B_t [T m]"),
    "TCUR": _p("float", "plasma", 2.0, "plasma current I_p [MA]"),
    "RMAJ": _p("float", "plasma", 3.05, "major radius [m]; derived from the markers when MSFX < 0"),
    "RPLA": _p("float", "plasma", 0.9, "minor radius [m]; derived from the markers when MSFX < 0"),
    "ZPLA": _p("float", "plasma", 0.0, "Z of the plasma centre [m]"),
    "ELIP": _p("float", "plasma", 1.0, "elongation"),
    "TRIG": _p("float", "plasma", 0.0, "triangularity"),
    "ELIPUP": _p("float", "plasma", 1.0, "elongation of the upper half"),
    "TRIGUP": _p("float", "plasma", 0.0, "triangularity of the upper half"),
    "YH": _p("float", "plasma", 0.5, "half height (shape of generated markers)"),
    "YD": _p("float", "plasma", 0.995, "edge height (shape of generated markers)"),
    "QAXI": _p("float", "plasma", 1.0, "q on axis used in the printed setup error only"),
    "QSUR": _p("float", "plasma", 3.0, "q at the surface used in the printed setup error only"),
    "XXLI": _p("float", "plasma", 1.0, "li used in the printed setup error only"),
    "ICP": _p("int[1..10]", "profile", [1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
              "profile options: ICP[1] the p' and FF' forms (|ICP[1]| = 1, 2, 9, 11); "
              "ICP[2] 0 trace only, >0 scale p' to beta_J = CP[1], 1 adjust F for <J/R>, "
              "2 adjust F for <J.B>"),
    "CP": _p("float[1..10]", "profile", [0.1, 1.0, 1.0, 0, 0, 0, 0, 0, 0, 0.05],
             "profile coefficients: CP[1] the beta_J target, CP[2..10] the exponents of ICP[1]'s form"),
    "KNAMCOIL": _p("str[80]", "coils", "init",
                   "coil file (relative to the working directory); 'done' uses the coils in "
                   "memory: after init only the JT-60U groups 1..4 with 70, 78, 26, 10 "
                   "filaments, so NCOIL above those, or > 0 for groups 5..18, is refused "
                   "(a run's coil file is not kept)"),
    "IVAC": _p("int[0..18]", "coils", [0, 1, 2] + [-1] * 16,
               "coil group mode: < 0 fixed current, >= 0 fitted; IVAC[0] the surface flux"),
    "NCOIL": _p("int[0..18]", "coils", [0, 70, 78, 26, 10] + [0] * 14,
                "filaments of each coil group in the coil file, 0..100"),
    "CVAC": _p("float[0..18]", "coils", [0.0] * 19, "coil currents [MA turn]; CVAC[0] the surface flux"),
    "CVACST": _p("float[0..18]", "coils", [0.0] * 19, "target coil currents of the fit [MA turn]"),
    "CVACWG": _p("float[0..18]", "coils", [0.0] * 19, "weights of the targets in the fit"),
    "CVACT": _p("float[0..18]", "coils", [0.0] * 19,
                "d CVAC / dt: used only by the menu's C, which the library does not run"),
    "ISVAC": _p("int", "coils", 0, "vacuum field: 0 through the grid, 1 direct Green's function"),
    "MSFX": _p("int", "boundary", 9,
               "marker points: < 0 given by RVAC/ZVAC (|MSFX| <= 29), > 0 generated from the shape (eqchek lowers it to 17, or 9 when symmetric)"),
    "RVAC": _p("float[0..30]", "boundary", [0.0] * 31, "R of the marker points [m]"),
    "ZVAC": _p("float[0..30]", "boundary", [0.0] * 31, "Z of the marker points [m]"),
    "ISEP": _p("int", "boundary", 2, "X point: 0 none, 1 lower, 2 outer, 3 upper, 4 inner (-4..4: the sign is used)"),
    "DSEP": _p("float", "boundary", 0.001, "separation between the X point and the last closed surface"),
    "ILIMT": _p("int", "boundary", 0, "limiter points in the coil file: must be 0 in the library (eqlim's limiter branch reads unset variables)"),
    "IVBND": _p("int", "boundary", 0,
                "must be 0: the vacuum boundary points it would count (RVBND, ZVBND) are not inputs"),
    "RLOOP": _p("float", "boundary", 2.786, "R of the flux-loop diagnostic point [m]"),
    "ZLOOP": _p("float", "boundary", 0.952, "Z of the flux-loop diagnostic point [m]"),
    "MSETUP": _p("int", "convergence", 20, "steps of the setup loop at most"),
    "ESETUP": _p("float", "convergence", 1e-3, "convergence of the setup loop"),
    "IEQMAX": _p("int", "convergence", 20, "steps of the FCT loop at most"),
    "EEQMAX": _p("float", "convergence", 1e-3, "convergence of the FCT loop"),
    "IODMAX": _p("int", "convergence", 10, "steps of the ODE iteration at most, >= 1"),
    "EODMAX": _p("float", "convergence", 1e-5, "convergence of the ODE iteration, < 1"),
    "IADMAX": _p("int", "convergence", 1, "steps of the vacuum fit at most"),
    "EADMAX": _p("float", "convergence", 1e-4, "convergence of the vacuum fit"),
    "BAVMAX": _p("float", "convergence", 0.8, "FCT relaxation, upper bound"),
    "BAVMIN": _p("float", "convergence", 0.2, "FCT relaxation, lower bound"),
    "IEQOUT": _p("int[1..10]", "output", [5, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                 "printing on unit 6: IEQOUT[2] >= 2 one line per step, IEQOUT[3] >= 1 the summary"),
    "IEQRD": _p("int", "output", 0, "must be 0"),
}

_STATE_SCALARS = {
    "MODE": "mode of the run (0 or 1)",
    "FCT_STEPS": "steps of the last FCT loop",
    "FCT_CONVERGED": "1 when the last FCT loop met EEQMAX",
    "XPOINT_STATUS": "> 0 an X point was found",
    "ERREQ": "error of the last FCT loop",
    "RAXIS": "R of the magnetic axis [m]", "ZAXIS": "Z of the magnetic axis [m]",
    "PSI_AXIS": "poloidal flux on axis", "RSEP": "R of the X point [m]",
    "ZSEP": "Z of the X point [m]", "PSI_SEP": "flux at the separatrix",
    "IP": "computed plasma current [MA]", "IP_TARGET": "TCUR [MA]", "RBT": "R*B_t [T m]",
    "BETA_T": "toroidal beta [%]", "BETA_S": "beta* [%]", "BETA_J": "beta_J", "LI": "li",
    "Q_AXIS": "q on axis", "Q_SURF": "q at the surface", "Q95": "q95", "QQJ": "q_J",
    "RMAJ": "major radius [m]", "RPLA": "minor radius [m]", "ELIP": "elongation",
    "TRIG": "triangularity", "EL95": "elongation at 95 %", "VOLUME": "plasma volume [m^3]",
}
STATE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "NR": {"type": "integer"}, "NZ": {"type": "integer"},
        "NV": {"type": "integer", "description": "flux surfaces (1 = axis)"},
        "NSU": {"type": "integer", "description": "points of the plasma boundary"},
        "scalars": {"type": "object",
                    "properties": {k: {"type": "number", "description": v}
                                   for k, v in _STATE_SCALARS.items()}},
        "CVAC": {"type": "array", "description": "coil currents of groups 0..18"},
        "RG": {"type": "array", "description": "R of the grid [m]"},
        "ZG": {"type": "array", "description": "Z of the grid [m]"},
        "profiles": {"type": "object", "properties": {
            "PSI": {"type": "array", "description": "poloidal flux"},
            "PSIT": {"type": "array", "description": "toroidal flux"},
            "PRESSURE": {"type": "array", "description": "pressure [Pa]"},
            "Q": {"type": "array"}, "F": {"type": "array", "description": "R*B_t [T m]"},
            "VOL": {"type": "array", "description": "volume [m^3]"},
            "RMINOR": {"type": "array"}, "RCENTRE": {"type": "array"},
            "KAPPA": {"type": "array"}, "DELTA": {"type": "array"}}},
        "RSU": {"type": "array", "description": "R of the boundary (open polygon)"},
        "ZSU": {"type": "array"},
    },
}


class _ServerState:
    def __init__(self) -> None:
        self.equ: Optional[Equ] = None

    def ensure_open(self) -> Equ:
        if self.equ is None or self.equ.closed:
            self.equ = Equ()
        return self.equ

    def close(self) -> None:
        if self.equ is not None and not self.equ.closed:
            self.equ.close()
        self.equ = None


STATE = _ServerState()


def _number(key: str, value: Any) -> float:
    if isinstance(value, bool):
        raise EqulibInvalidParamError(f"'{key}': a bool is no number (use 0 or 1)")
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EqulibInvalidParamError(f"invalid numeric value for '{key}': {value!r}") from exc
    if not math.isfinite(v):
        raise EqulibInvalidParamError(f"invalid numeric value for '{key}': {value!r} (not finite)")
    return v


def _array_lower(name: str) -> Optional[int]:
    t = PARAMETER_REGISTRY.get(name, {}).get("type", "")
    if "[" in t and ".." in t:
        return int(t[t.index("[") + 1: t.index("..")])
    return None


def _apply_bulk_params(equ: Equ, params: Dict[str, SupportedValue]) -> List[str]:
    """A list fills an array from its lower bound (0 for the coil arrays);
    a dict {index: value} sets those elements; a str goes to set_param_str."""
    applied: List[str] = []
    for name, value in params.items():
        if isinstance(value, (list, tuple)):
            lo = _array_lower(name)
            if lo is None:
                raise EqulibInvalidParamError(f"'{name}' is not an array")
            for i, v in enumerate(value, start=lo):
                key = f"{name}[{i}]"
                equ.set_param(key, _number(key, v))
                applied.append(key)
        elif isinstance(value, dict):
            for idx, v in value.items():
                key = f"{name}[{int(idx)}]"
                equ.set_param(key, _number(key, v))
                applied.append(key)
        elif isinstance(value, str):
            equ.set_param_str(name, value)
            applied.append(name)
        else:
            equ.set_param(name, _number(name, value))
            applied.append(name)
    return applied


def _wrap(exc: Exception) -> "ToolError":  # noqa: F821
    if isinstance(exc, EqulibInvalidParamError):
        msg = f"invalid parameter or call: {exc}"
    elif isinstance(exc, EqulibNotInitializedError):
        msg = f"library not initialized (call init first): {exc}"
    elif isinstance(exc, EqulibCalculationFailedError):
        msg = f"calculation failed: {exc}"
    elif isinstance(exc, EqulibNotImplementedError):
        msg = f"not implemented (run takes mode 0 or 1): {exc}"
    elif isinstance(exc, EqulibInitError):
        msg = f"equ_init failed: {exc}"
    elif isinstance(exc, EqulibError):
        msg = f"equlib error: {exc}"
    elif isinstance(exc, FileNotFoundError):
        msg = f"libequapi.so not found (build it with `make -C equ libequapi.so` or set EQULIB_PATH): {exc}"
    else:
        msg = f"{type(exc).__name__}: {exc}"
    return ToolError(msg)  # type: ignore[call-arg]


# --- handlers (plain functions; the tools below call them) -------------
def handle_init() -> str:
    try:
        STATE.close()
        STATE.ensure_open()
        return "equ library initialized"
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_read_parm(path: str) -> str:
    try:
        STATE.ensure_open().read_parm(path)
        return f"read the &EQU namelist of {path}"
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_set_param(name: str, value: float) -> str:
    try:
        STATE.ensure_open().set_param(name, _number(name, value))
        return f"set {name} = {value}"
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_set_param_str(name: str, value: str) -> str:
    try:
        STATE.ensure_open().set_param_str(name, str(value))
        return f"set {name} = {value!r}"
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_set_params(params: Dict[str, SupportedValue]) -> Dict[str, Any]:
    try:
        return {"applied": _apply_bulk_params(STATE.ensure_open(), params)}
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_validate() -> List[Dict[str, Any]]:
    try:
        return [{"param": d.param, "code": d.code, "message": d.message}
                for d in STATE.ensure_open().validate()]
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_run(mode: int = 1) -> str:
    try:
        STATE.ensure_open().run(mode)
        return f"run(mode={mode}) completed"
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_get_state() -> Dict[str, Any]:
    try:
        return STATE.ensure_open().get_state().to_dict()
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_get_psi_rz() -> Dict[str, Any]:
    try:
        equ = STATE.ensure_open()
        psi = equ.get_psi_rz()
        st = equ.get_state()
        return {"nr": st.nr, "nz": st.nz, "rg": st.rg, "zg": st.zg, "psi_rz": psi.tolist()}
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_write_geqdsk(path: str, overwrite: bool = False) -> str:
    try:
        STATE.ensure_open().write_geqdsk(path, overwrite=overwrite)
        return f"wrote G-EQDSK {path}"
    except Exception as exc:
        raise _wrap(exc) from exc


def handle_finalize() -> str:
    STATE.close()
    return "equ library finalized"


def handle_describe_parameters() -> Dict[str, Any]:
    return {"module": "equ", "count": len(PARAMETER_REGISTRY),
            "array_syntax": "NAME[i], i as Fortran declares it (IVAC, NCOIL, CVAC*, 0..18; "
                            "RVAC, ZVAC 0..30; ICP, CP, IEQOUT 1..10)",
            "parameters": PARAMETER_REGISTRY}


def handle_describe_state_schema() -> Dict[str, Any]:
    return STATE_SCHEMA


def handle_run_and_get_state(params: Optional[Dict[str, Any]] = None, mode: int = 1,
                             parm_file: Optional[str] = None) -> Dict[str, Any]:
    handle_init()
    if parm_file:
        handle_read_parm(parm_file)
    if params:
        handle_set_params(params)
    handle_run(mode)
    return handle_get_state()


TOOLS = ["init", "read_parm", "set_param", "set_param_str", "set_params", "validate", "run",
         "get_state", "get_psi_rz", "write_geqdsk", "finalize", "describe_parameters",
         "describe_state_schema", "run_and_get_state"]


def build_server() -> "FastMCP":  # noqa: F821
    if not MCP_AVAILABLE:  # pragma: no cover
        raise RuntimeError("the MCP SDK (mcp) is not installed")
    mcp = FastMCP("task-equ")

    @mcp.tool()
    def init() -> str:
        """Start a fresh EQU library at its defaults (closes the previous one)."""
        return handle_init()

    @mcp.tool()
    def read_parm(path: str) -> str:
        """Read an &EQU namelist file (relative to the server's working directory)."""
        return handle_read_parm(path)

    @mcp.tool()
    def set_param(name: str, value: float) -> str:
        """Set a numeric parameter: NAME or NAME[i] (see describe_parameters)."""
        return handle_set_param(name, value)

    @mcp.tool()
    def set_param_str(name: str, value: str) -> str:
        """Set DEVICE, DEVNAM, TITLE or KNAMCOIL (the coil file)."""
        return handle_set_param_str(name, value)

    @mcp.tool()
    def set_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Set several parameters; not transactional. A list fills an array
        from its lower bound, a dict {index: value} sets elements."""
        return handle_set_params(params)

    @mcp.tool()
    def validate() -> List[Dict[str, Any]]:
        """Every check of the inputs in one batch; [] when the run may start."""
        return handle_validate()

    @mcp.tool()
    def run(mode: int = 1) -> str:
        """Compute the equilibrium: mode 1 the program's R command, mode 0 its first step."""
        return handle_run(mode)

    @mcp.tool()
    def get_state() -> Dict[str, Any]:
        """The result of the last run (see describe_state_schema)."""
        return handle_get_state()

    @mcp.tool()
    def get_psi_rz() -> Dict[str, Any]:
        """psi(R, Z) on the grid, with the R and Z vectors."""
        return handle_get_psi_rz()

    @mcp.tool()
    def write_geqdsk(path: str, overwrite: bool = False) -> str:
        """Write the last run's equilibrium as G-EQDSK (EQU's writer; pressure in MPa as EQU writes it)."""
        return handle_write_geqdsk(path, overwrite)

    @mcp.tool()
    def finalize() -> str:
        """Close the library."""
        return handle_finalize()

    @mcp.tool()
    def describe_parameters() -> Dict[str, Any]:
        """The parameter names, types, groups, defaults and descriptions."""
        return handle_describe_parameters()

    @mcp.tool()
    def describe_state_schema() -> Dict[str, Any]:
        """A JSON schema of get_state's result."""
        return handle_describe_state_schema()

    @mcp.tool()
    def run_and_get_state(params: Optional[Dict[str, Any]] = None, mode: int = 1,
                          parm_file: Optional[str] = None) -> Dict[str, Any]:
        """init, read_parm(parm_file) if given, set_params(params), run(mode), get_state."""
        return handle_run_and_get_state(params, mode, parm_file)

    return mcp


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(
            "equ-mcp -- Model Context Protocol server for TASK/EQU\n\n"
            "Usage:\n"
            "  python -m equ_mcp.server    # run over stdio\n"
            "  equ-mcp --print-tools       # list the tools\n\n"
            "Environment:\n"
            "  EQULIB_PATH  path to libequapi.so\n"
            "  PYTHONPATH   must include the repo's python/ and python/mcp-servers/\n")
        return 0
    if "--print-tools" in argv:
        for tool in sorted(TOOLS):
            sys.stdout.write(tool + "\n")
        return 0
    if not MCP_AVAILABLE:
        sys.stderr.write("error: the Python MCP SDK (mcp) is not installed\n")
        return 2
    _fd_isolation.install()
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
