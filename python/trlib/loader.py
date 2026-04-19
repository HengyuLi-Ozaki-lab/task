"""TOML configuration loader for :mod:`trlib`.

The schema (mirrored from ``project_toml_sample_runner.md``)::

    [module]
    name = "tr"
    ntmax = 100            # overrides NTMAX scalar if present

    [scalars]
    RR = 3.0
    NSMAX = 4

    [arrays]
    PN = [0.7, 0.315, 0.315, 0.035]     # 1-origin list
    # PN = {1 = 0.7, 2 = 0.315}         # sparse dict form

    [strings]
    KNAMEQ = "eqdata.ITER"

    [[plots]]
    variable = "RNT"
    output = "file"                      # window | file | return
    format = "png"
    path = "./plots/rnt.png"
    title = "RNT profile"

    [plot]                               # singular form also accepted
    variable = "RT"
    output = "file"
    path = "./plots/rt.png"

The module exports three pure functions:

* :func:`load_config` — parse TOML into a structured dict.
* :func:`apply_config` — replay ``scalars``/``arrays``/``strings`` onto
  a live :class:`~trlib.Trlib` instance.
* :func:`run_plots` — execute all ``[plot]`` / ``[[plots]]`` specs.

``load_config`` never touches libtrapi.so, so tests can exercise TOML
parsing without the shared library present.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, IO, List, Mapping, Tuple, Union

# tomllib is stdlib since Python 3.11. Fall back to the third-party
# ``tomli`` package for older runtimes (matches the request in the
# design spec).
try:
    import tomllib as _toml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - 3.10 fallback
    try:
        import tomli as _toml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "trlib.loader requires Python 3.11+ (stdlib tomllib) or "
            "`pip install tomli` on 3.10 and earlier."
        ) from exc


PathLike = Union[str, "os.PathLike[str]"]
ConfigInput = Union[PathLike, IO[bytes], IO[str], bytes, str]


# =====================================================================
# Parsing
# =====================================================================
def _loads(raw: Union[bytes, str]) -> Dict[str, Any]:
    """Wrap ``tomllib.loads`` so both ``bytes`` and ``str`` inputs work."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return _toml.loads(raw)


def _read_stream(src: ConfigInput) -> Dict[str, Any]:
    """Read TOML data from a path, stream, or raw str/bytes.

    Accepted shapes:

    * :class:`os.PathLike` (e.g. :class:`pathlib.Path`) — read as binary file.
    * ``str`` / ``bytes`` — treated as a filesystem path if it looks like
      one, else as inline TOML text.
    * file-like with ``.read()`` returning ``str`` / ``bytes``.
    """
    # PathLike (Path, etc.) — always a path.
    if isinstance(src, os.PathLike):
        with open(src, "rb") as fh:
            return _toml.load(fh)
    if isinstance(src, (bytes, str)):
        if _looks_like_toml(src):
            return _loads(src)
        # Treat as path.
        with open(src, "rb") as fh:
            return _toml.load(fh)
    if hasattr(src, "read"):
        data = src.read()
        return _loads(data)
    raise TypeError(f"unsupported TOML source: {type(src).__name__}")


def _looks_like_toml(s: Union[bytes, str]) -> bool:
    """Heuristic: strings containing newlines or ``=`` are inline TOML,
    everything else is treated as a filesystem path."""
    text = s.decode("utf-8", errors="ignore") if isinstance(s, bytes) else s
    # An actual path does not contain '\n' or a top-level '=' sign or
    # square brackets. This is a small heuristic; callers that want
    # precise behaviour can wrap inline text in ``io.BytesIO``.
    return ("\n" in text) or ("=" in text and len(text) > 40) or ("[" in text and "]" in text and "=" in text)


def load_config(path_or_stream: ConfigInput) -> Dict[str, Any]:
    """Parse TOML config and return a structured dict.

    The result has a stable shape regardless of which sections the
    author supplied:

    ``{"module": {...}, "scalars": {...}, "arrays": {...},
       "strings": {...}, "plots": [...]}``

    Unknown keys are preserved under ``"raw"`` so future loader versions
    can read older configs.
    """
    data = _read_stream(path_or_stream)
    if not isinstance(data, Mapping):  # pragma: no cover - tomllib invariant
        raise ValueError("TOML root must be a table")

    module = dict(data.get("module", {})) if isinstance(data.get("module"), Mapping) else {}
    scalars = dict(data.get("scalars", {})) if isinstance(data.get("scalars"), Mapping) else {}
    arrays = dict(data.get("arrays", {})) if isinstance(data.get("arrays"), Mapping) else {}
    strings = dict(data.get("strings", {})) if isinstance(data.get("strings"), Mapping) else {}

    # Collect [plot] and [[plots]] into a single list. Order: singular
    # first, then array-of-tables, so authors can "pin" one default
    # plot before the declarative batch.
    plots: List[Dict[str, Any]] = []
    singular = data.get("plot")
    if isinstance(singular, Mapping):
        plots.append(dict(singular))
    multi = data.get("plots")
    if isinstance(multi, list):
        for entry in multi:
            if isinstance(entry, Mapping):
                plots.append(dict(entry))

    # Module-level ntmax propagates into scalars if the author did not
    # also set NTMAX explicitly. This matches the schema-spec precedent
    # that `[module] ntmax = 100` is a convenience alias.
    if "ntmax" in module and "NTMAX" not in scalars:
        scalars["NTMAX"] = int(module["ntmax"])

    return {
        "module": module,
        "scalars": scalars,
        "arrays": arrays,
        "strings": strings,
        "plots": plots,
        "raw": dict(data),
    }


# =====================================================================
# Application
# =====================================================================
# ``Any`` instead of ``Trlib`` on the annotation keeps this module
# importable without pulling in libtrapi.so (Trlib.__init__ loads the
# shared library eagerly).
def apply_config(tr: Any, cfg: Mapping[str, Any]) -> None:
    """Replay ``scalars`` / ``arrays`` / ``strings`` onto a live Trlib.

    Order of application: strings first (some strings, e.g. ``KNAMEQ``,
    are read inside tr_init's follow-up calls), then scalars, then
    arrays — matching the ``fixtures/tr_iter01_params.py::apply``
    precedent.
    """
    for name, value in cfg.get("strings", {}).items():
        tr.set_param_str(name, str(value))
    for name, value in cfg.get("scalars", {}).items():
        tr.set_param(name, float(value))
    for name, arr in cfg.get("arrays", {}).items():
        _apply_array(tr, name, arr)


def _apply_array(tr: Any, name: str, arr: Any) -> None:
    """Apply an ``arrays`` entry (list or ``{idx: val}`` dict)."""
    if isinstance(arr, Mapping):
        for k, v in arr.items():
            tr.set_param(f"{name}[{int(k)}]", float(v))
    elif isinstance(arr, (list, tuple)):
        for i, v in enumerate(arr, start=1):
            tr.set_param(f"{name}[{i}]", float(v))
    else:
        raise ValueError(
            f"[arrays] {name!r} must be a list or {{idx: val}} dict, "
            f"got {type(arr).__name__}"
        )


# =====================================================================
# Plot execution
# =====================================================================
def run_plots(tr: Any, cfg: Mapping[str, Any]) -> List[Tuple[str, Any]]:
    """Execute every state-dependent plot spec in ``cfg`` against a live
    :class:`Trlib`. **Sweep plots are skipped** here — they require their
    own isolated Trlib lifecycle (see :func:`run_sweep_plots`) because the
    Fortran COMMON-block backend is single-instance per process.

    Returns a list of ``(varname, output_descriptor)`` tuples where
    ``output_descriptor`` is the return value of :func:`trlib.plot.plot`
    (:class:`Path` when ``output="file"``, :class:`Figure` when
    ``output="return"``, :obj:`None` when ``output="window"``).
    """
    from . import plot as _plot_mod  # lazy: matplotlib is optional

    plots = cfg.get("plots", [])
    results: List[Tuple[str, Any]] = []
    if not plots:
        return results

    # Cache the state once per run so multiple plots don't re-run the
    # simulation backend.
    state = tr.get_state()
    for spec in plots:
        if not isinstance(spec, Mapping):
            continue
        # Sweep plots are deferred to run_sweep_plots() (own Trlib lifecycle).
        # Skip them here regardless of whether they also carry a `variable`
        # key, otherwise they would be processed twice.
        if spec.get("kind") == "sweep":
            continue
        varname = spec.get("variable")
        if not varname:
            continue
        kw = _plot_kwargs(spec)
        descriptor = _plot_mod.plot(varname, state=state, **kw)
        results.append((varname, descriptor))
    return results


def run_sweep_plots(cfg: Mapping[str, Any]) -> List[Tuple[str, Any]]:
    """Execute sweep / compare plot specs that need their own Trlib
    lifecycle. MUST be called AFTER any outer ``with Trlib()`` block has
    exited — sweeps open fresh Trlib instances internally and would
    collide with a still-live caller instance.
    """
    from . import plot as _plot_mod  # lazy

    plots = cfg.get("plots", [])
    results: List[Tuple[str, Any]] = []
    if not plots:
        return results
    for spec in plots:
        if not isinstance(spec, Mapping):
            continue
        kind = spec.get("kind")
        if kind == "sweep":
            results.append(_run_sweep_spec(spec, _plot_mod))
    return results


def _plot_kwargs(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """Translate a ``[[plots]]`` entry into :func:`trlib.plot.plot` kwargs."""
    kw: Dict[str, Any] = {}
    for key in ("output", "format", "path", "title", "overlay"):
        if key in spec:
            kw[key] = spec[key]
    return kw


def _run_sweep_spec(spec: Mapping[str, Any], plot_mod: Any) -> Tuple[str, Any]:
    """Helper for ``kind = "sweep"`` entries.

    No `tr` argument: plot_mod.plot_sweep manages its own per-sample
    Trlib lifecycle internally.
    """
    param = spec["param"]
    y = spec["y"]
    rng = tuple(spec["range"])
    if len(rng) != 3:
        raise ValueError(
            f"sweep 'range' must be [start, stop, n_samples]; got {rng!r}"
        )
    kw = _plot_kwargs(spec)
    # Sweep-specific kwargs that _plot_kwargs (shared with regular plots)
    # does not extract. Forward them only when the user supplied them.
    if "ntmax" in spec:
        kw["ntmax"] = spec["ntmax"]
    if "base_params" in spec:
        kw["base_params"] = spec["base_params"]
    descriptor = plot_mod.plot_sweep(param, y, range=rng, **kw)
    return (f"sweep:{param}->{y}", descriptor)


__all__ = [
    "load_config",
    "apply_config",
    "run_plots",
    "run_sweep_plots",
]
