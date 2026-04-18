"""Visualization layer for :mod:`trlib`.

Reference implementation of the "declarative plot(varname)" API described
in ``project_visualization_followup.md``. Other modules (ti / wr / wrx /
fp / eq) will copy this file and adjust their ``VARIABLE_INFO`` +
``_extract_series`` when they reach Phase L+viz.

Design points:

* :func:`plot_available` returns the list of variable names that have
  registered metadata in :data:`VARIABLE_INFO`. Callers (human or LLM via
  MCP) can check support before asking for a plot.
* :func:`plot` takes a :class:`~trlib.state.TrState` snapshot and draws a
  1D profile (or a species-stacked profile for 2D fields like ``RN`` /
  ``RT``).
* ``output="window"`` shows an interactive figure (``plt.show``);
  ``output="file"`` saves to disk and returns the :class:`pathlib.Path`;
  ``output="return"`` returns the :class:`matplotlib.figure.Figure` so
  notebook callers can embed it in their cell output.
* :func:`plot_sweep` runs an ad-hoc parameter sweep over a single
  scalar and plots the resulting scalar quantity. It creates and
  destroys a :class:`~trlib.Trlib` context internally.

matplotlib is an **optional** dependency. If it is missing, importing
:mod:`trlib.plot` raises :class:`ImportError` with an actionable
message; ``trlib`` itself stays importable either way.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

try:
    import matplotlib  # type: ignore[import-not-found]
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]
    from matplotlib.figure import Figure  # type: ignore[import-not-found]
    HAS_MATPLOTLIB = True
except ImportError as _mpl_err:  # pragma: no cover - exercised in env without mpl
    raise ImportError(
        "trlib.plot requires matplotlib. Install it via "
        "`pip install matplotlib` or mark the feature as optional by "
        "not importing trlib.plot."
    ) from _mpl_err

from .state import TrState


# =====================================================================
# Variable metadata (labels, axis info, units).
#
# Hard-coded dict is a deliberate short-term choice — keeping it in
# Python is easier to edit and review than pulling from JSON/YAML.
# Future revisions may move this to a schema file shared with the MCP
# `describe_state_schema` tool.
# =====================================================================
_PROFILE_XAXIS = {"label": "rg (minor radius, normalised)", "unit": ""}


VARIABLE_INFO: Dict[str, Dict[str, Any]] = {
    # --- 1D radial profiles (length nrmax) --------------------------
    "AJ": {
        "label": "AJ (current density profile)",
        "ylabel": "AJ [MA/m^2]",
        "xaxis": "rg",
        "kind": "profile_1d",
        "dim": 1,
    },
    "QP": {
        "label": "QP (safety factor profile)",
        "ylabel": "q",
        "xaxis": "rg",
        "kind": "profile_1d",
        "dim": 1,
    },
    # --- 2D species-stacked profiles (nrmax x nsmax) ----------------
    "RN": {
        "label": "RN (density profile per species)",
        "ylabel": "n [10^20 m^-3]",
        "xaxis": "rg",
        "kind": "profile_2d",
        "dim": 2,
    },
    "RT": {
        "label": "RT (temperature profile per species)",
        "ylabel": "T [keV]",
        "xaxis": "rg",
        "kind": "profile_2d",
        "dim": 2,
    },
    # --- Aliases matching the diagnostic-plot naming used in
    # the Fortran GSAF screens (RNT = density-like, RWT = temperature-
    # like). Keeping both aliases and canonical names means a TOML
    # author can write either. ----------------------------------------
    "RNT": {
        "label": "RNT (density profile, species-stacked)",
        "ylabel": "n [10^20 m^-3]",
        "xaxis": "rg",
        "kind": "profile_2d",
        "dim": 2,
        "alias_of": "RN",
    },
    "RWT": {
        "label": "RWT (temperature profile, species-stacked)",
        "ylabel": "T [keV]",
        "xaxis": "rg",
        "kind": "profile_2d",
        "dim": 2,
        "alias_of": "RT",
    },
    # --- Scalar-over-sweep plots are handled via plot_sweep(); these
    # live in the same registry so plot_available() can surface them.
    "T": {
        "label": "T (time)",
        "ylabel": "t [s]",
        "kind": "scalar",
        "dim": 0,
    },
    "WPT": {
        "label": "WPT (stored energy)",
        "ylabel": "W [MJ]",
        "kind": "scalar",
        "dim": 0,
    },
    "AJT": {
        "label": "AJT (total plasma current)",
        "ylabel": "Ip [MA]",
        "kind": "scalar",
        "dim": 0,
    },
    "Q0": {
        "label": "Q0 (on-axis safety factor)",
        "ylabel": "q(0)",
        "kind": "scalar",
        "dim": 0,
    },
    "BETA0": {"label": "BETA0", "ylabel": "beta_0", "kind": "scalar", "dim": 0},
    "BETAP0": {"label": "BETAP0", "ylabel": "beta_p0", "kind": "scalar", "dim": 0},
    "BETAA": {"label": "BETAA", "ylabel": "beta_a", "kind": "scalar", "dim": 0},
    "BETAN": {"label": "BETAN", "ylabel": "beta_N", "kind": "scalar", "dim": 0},
    "TAUE1": {"label": "TAUE1 (confinement time)", "ylabel": "tau_E1 [s]", "kind": "scalar", "dim": 0},
    "TAUE2": {"label": "TAUE2 (confinement time)", "ylabel": "tau_E2 [s]", "kind": "scalar", "dim": 0},
    "ZEFF0": {"label": "ZEFF0 (effective charge)", "ylabel": "Z_eff(0)", "kind": "scalar", "dim": 0},
    "ALI": {"label": "ALI (internal inductance)", "ylabel": "l_i", "kind": "scalar", "dim": 0},
    "RQ1": {"label": "RQ1 (q=1 surface radius)", "ylabel": "r(q=1)", "kind": "scalar", "dim": 0},
}


# =====================================================================
# Public API
# =====================================================================
def plot_available() -> List[str]:
    """Return the canonical list of variables that have plot support.

    The list is sorted alphabetically so automated callers (MCP /
    doctests) get a stable ordering.
    """
    return sorted(VARIABLE_INFO.keys())


def _resolve_varname(varname: str) -> Tuple[str, Dict[str, Any]]:
    """Translate aliases and return (canonical_name, info_dict)."""
    if varname not in VARIABLE_INFO:
        raise KeyError(
            f"variable {varname!r} has no plot support. "
            f"Use trlib.plot.plot_available() to list supported variables."
        )
    info = VARIABLE_INFO[varname]
    canonical = info.get("alias_of", varname)
    return canonical, info


def _profile_xaxis(n: int) -> List[float]:
    """Return ``[0, 1/(n-1), ..., 1]`` as a normalised radial axis."""
    if n <= 0:
        return []
    if n == 1:
        return [0.0]
    return [i / (n - 1) for i in range(n)]


def _in_notebook() -> bool:
    """Return True when called from within an IPython / Jupyter kernel."""
    try:
        from IPython import get_ipython  # type: ignore[import-not-found]
    except Exception:
        return False
    ip = get_ipython()
    if ip is None:
        return False
    # ZMQInteractiveShell = notebook / qtconsole; TerminalInteractiveShell = plain ipython
    return "ZMQInteractive" in type(ip).__name__


def _draw_profile(
    fig: "Figure",
    varname: str,
    info: Dict[str, Any],
    state: TrState,
    *,
    overlay: bool,
    title: Optional[str],
) -> None:
    """Populate ``fig`` with a 1D or 2D profile plot."""
    ax = fig.gca()
    kind = info.get("kind")

    if kind == "profile_1d":
        data: List[float] = list(getattr(state, varname))
        x = _profile_xaxis(len(data))
        ax.plot(x, data, marker=".", linewidth=1.0, label=varname)
    elif kind == "profile_2d":
        data2d: List[List[float]] = list(getattr(state, varname))
        x = _profile_xaxis(len(data2d))
        nsmax = state.nsmax
        for j in range(nsmax):
            series = [row[j] for row in data2d]
            ax.plot(x, series, marker=".", linewidth=1.0,
                    label=f"{varname}[*,{j + 1}]")
        ax.legend(loc="best", fontsize="small")
    elif kind == "scalar":
        # A scalar cannot be plotted from a single snapshot. Instead we
        # draw a trivial bar so the caller still gets a figure — this
        # also exercises the same code path the sweep plot will use.
        value = state.scalars.get(varname, 0.0)
        ax.bar([varname], [value])
        ax.set_ylabel(info.get("ylabel", varname))
    else:  # pragma: no cover - exhaustive guard
        raise ValueError(f"unknown plot kind: {kind!r} for {varname}")

    ax.set_xlabel(info.get("xaxis", "rg"))
    if kind in ("profile_1d", "profile_2d"):
        ax.set_ylabel(info.get("ylabel", varname))
    ax.set_title(title or info.get("label", varname))
    ax.grid(True, alpha=0.3)
    # overlay=True means "caller will add more curves"; leave the axes alone.
    if not overlay:
        fig.tight_layout()


def plot(
    varname: str,
    *,
    state: Optional[TrState] = None,
    output: str = "window",
    format: str = "png",
    path: Optional[Union[str, Path]] = None,
    title: Optional[str] = None,
    overlay: bool = False,
    figure: Optional["Figure"] = None,
    **kwargs: Any,
) -> Union["Figure", Path, None]:
    """Plot a variable from a :class:`TrState`.

    Parameters
    ----------
    varname:
        Key into :data:`VARIABLE_INFO`. Raises :class:`KeyError` if unknown.
    state:
        The :class:`TrState` to draw from. If None, callers must pass a
        ``figure`` already populated with data — useful for the ``overlay``
        code path used by :class:`Trlib.plot`.
    output:
        ``"window"`` (default, interactive), ``"file"`` (save and return
        Path), or ``"return"`` (return :class:`Figure`).
    format:
        When ``output="file"``: file extension (png / pdf / svg / jpg / eps).
    path:
        Output path (only for ``output="file"``). Derived from ``varname``
        and ``format`` when omitted.
    title:
        Figure title. Defaults to the ``"label"`` field in ``VARIABLE_INFO``.
    overlay:
        Reserved for future multi-variable overlays. Currently forwarded
        to the drawing routine, which skips the final ``tight_layout``
        call so the caller can keep adding curves before finalising.
    figure:
        Optional existing :class:`Figure` to reuse (for overlays).

    Returns
    -------
    * :class:`pathlib.Path` when ``output="file"``
    * :class:`matplotlib.figure.Figure` when ``output="return"``
    * :obj:`None` when ``output="window"``
    """
    canonical, info = _resolve_varname(varname)
    if output not in ("window", "file", "return"):
        raise ValueError(
            f"output must be one of 'window' / 'file' / 'return', got {output!r}"
        )

    if state is None and figure is None:
        raise ValueError(
            "plot() needs either a TrState (state=...) or an existing "
            "figure to render into. Call Trlib.plot() for the common case."
        )

    fig = figure if figure is not None else plt.figure()
    if state is not None:
        _draw_profile(
            fig, canonical, info, state,
            overlay=overlay, title=title,
        )

    if output == "return":
        return fig
    if output == "file":
        out_path = Path(path) if path else Path(f"{canonical}.{format}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, format=format)
        plt.close(fig)
        return out_path

    # output == "window"
    if _in_notebook():
        plt.show(block=False)
    else:  # pragma: no cover - cannot drive a real window in tests
        plt.show(block=True)
    return None


# =====================================================================
# Sweep plotting
# =====================================================================
def plot_sweep(
    param: str,
    y: str,
    *,
    sweep_range: Tuple[float, float, int] = None,
    output: str = "window",
    format: str = "png",
    path: Optional[Union[str, Path]] = None,
    title: Optional[str] = None,
    ntmax: int = 0,
    base_params: Optional[Dict[str, Any]] = None,
    range: Tuple[float, float, int] = None,  # backward-compat alias
    **kwargs: Any,
) -> Union["Figure", Path, None]:
    """Run a 1D scan over ``param`` and plot the scalar ``y`` on the y-axis.

    Parameters
    ----------
    param:
        Scalar parameter name passed to :meth:`Trlib.set_param`.
    y:
        Scalar key into :attr:`TrState.scalars`.
    sweep_range (or ``range`` for backward compat):
        ``(start, stop, n_samples)`` triple (inclusive endpoints).
    output / format / path / title:
        Same semantics as :func:`plot`.
    ntmax:
        Number of time-steps to advance per sample (default 0 to keep the
        scan fast; pass a positive number to exercise the real transport).
    base_params:
        Optional dict of scalars applied to every sample point before
        setting ``param``.
    """
    from .trlib import Trlib  # local import to avoid cycle

    # Accept the legacy keyword name `range` but prefer `sweep_range`.
    rng = sweep_range if sweep_range is not None else range
    if rng is None:
        raise TypeError("plot_sweep requires sweep_range=(start, stop, n)")

    if y not in VARIABLE_INFO:
        raise KeyError(
            f"y variable {y!r} has no plot support. See plot_available()."
        )
    start, stop, n = rng
    n = int(n)              # TOML may pass float; range() requires int
    if n < 2:
        raise ValueError("plot_sweep needs at least 2 samples")
    # Use the builtin via __builtins__ since `range` parameter shadows it.
    import builtins as _builtins
    xs = [float(start) + (float(stop) - float(start)) * i / (n - 1)
          for i in _builtins.range(n)]
    ys: List[float] = []

    # Sweep MUST own its own Trlib lifecycle: tr globals are shared, and
    # nesting `with Trlib()` inside an outer caller's instance would
    # double-finalize and corrupt state. _run_sweep_spec passes its outer
    # `tr` argument for documentation purposes only — we ignore it and
    # spin up a fresh, isolated Trlib here. A future refactor could share
    # one instance and just reset params per sample.
    with Trlib() as tr:
        for x in xs:
            if base_params:
                for k, v in base_params.items():
                    tr.set_param(k, float(v))
            tr.set_param(param, float(x))
            tr.run(ntmax=ntmax)
            state = tr.get_state()
            ys.append(float(state.scalars.get(y, 0.0)))

    fig = plt.figure()
    ax = fig.gca()
    ax.plot(xs, ys, marker="o", linewidth=1.0)
    ax.set_xlabel(param)
    ax.set_ylabel(VARIABLE_INFO[y].get("ylabel", y))
    ax.set_title(title or f"{y} vs {param} ({n} samples)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if output == "return":
        return fig
    if output == "file":
        out_path = Path(path) if path else Path(f"sweep_{param}_{y}.{format}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, format=format)
        plt.close(fig)
        return out_path
    if _in_notebook():
        plt.show(block=False)
    else:  # pragma: no cover
        plt.show(block=True)
    return None


__all__ = [
    "VARIABLE_INFO",
    "HAS_MATPLOTLIB",
    "plot",
    "plot_available",
    "plot_sweep",
]
