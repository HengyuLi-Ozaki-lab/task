# Library applications (Python wrappers)

Using `Tilib` raw is fine, but wrapping a thin layer on top makes it
much more practical. Below are three typical patterns.

```{admonition} Where this page fits
:class: note

What this page covers is **application patterns for using `tilib` from
Python**. For scenarios where an LLM client drives it via natural
language, see {doc}`mcp`.
```

```{admonition} Runtime prerequisite (ADPOST / ADF11 data)
:class: warning

`ti.run()` internally references ``../adpost/ADPOST-DATA`` and
``./ADF11-bin.data``. When running from somewhere other than the
repository root, follow the pattern in ``case ti)`` of
``test_run/run_tests.sh`` or in ``TiDataCwdMixin`` from
{doc}`testing`: symlink ``adpost/ADPOST-DATA`` next to the working
directory and ``ADF11-bin.data`` into the current directory. The
sample outputs below were captured with this layout.
```

---

## 1. Auto-stabilizing wrapper

A wrapper that retries with `DT` halved when `run()` returns a
`TilibRunError` (internal ``ierr=3``). Useful as a safety net for
large parameter sweeps where a few combinations fail to converge.

```python
from tilib import TiLib
from tilib.errors import TilibRunError


class StableTiRunner:
    """Wraps `TiLib` with `with` and retries with DT halved when run() fails.

    Parameters
    ----------
    max_retries : int
        Maximum number of attempts to shrink DT (DT is halved on each attempt).
    dt_floor : float
        Give up and raise RuntimeError when DT falls below this value.
    """

    def __init__(self, *, max_retries: int = 5, dt_floor: float = 1.0e-5):
        self._ti = TiLib()
        self._ti.__enter__()
        self.dt = 0.01           # same as ti's default DT
        self.max_retries = max_retries
        self.dt_floor = dt_floor
        self.retries = 0

    def __enter__(self) -> "StableTiRunner":
        return self

    def __exit__(self, *args) -> None:
        self._ti.__exit__(*args)

    def configure(self, **params) -> None:
        """`set_params`-compatible. Remember DT."""
        self._ti.set_params(**params)
        if "DT" in params:
            self.dt = float(params["DT"])

    def run(self, ntmax: int):
        """Halve DT and retry on failure. Returns a TiState in the end."""
        for attempt in range(self.max_retries):
            try:
                self._ti.run(ntmax=ntmax)
                return self._ti.get_state()
            except TilibRunError as e:
                if self.dt <= self.dt_floor:
                    raise RuntimeError(
                        f"Did not stabilize even after shrinking DT to {self.dt}: {e}"
                    ) from e
                self.dt /= 2
                self._ti.set_param("DT", self.dt)
                self.retries += 1
                print(
                    f"  [retry] {e!r} -> retry with DT={self.dt:.2e} "
                    f"({attempt + 1}/{self.max_retries})"
                )
        raise RuntimeError(
            f"Did not stabilize after {self.max_retries} attempts (final DT={self.dt})"
        )


# Example usage
with StableTiRunner() as runner:
    runner.configure(RR=3.0, BB=3.0, NSMAX=2, DT=0.01)
    state = runner.run(ntmax=10)
    print(f"finished: T={state.T:.3f}s, "
          f"T0={state.RTA[0][0]:.3f}keV, "
          f"retries={runner.retries}")
```

Expected output (the parameters above are stable, so no retries fire):

```
finished: T=0.100s, T0=4.999keV, retries=0
```

For combinations prone to numerical divergence (e.g. extremely small
`BB`, large `DT`), `[retry]` log lines appear and `retries` becomes 1
or more:

```
[retry] TilibRunError(...) -> retry with DT=5.00e-03 (1/5)
finished: T=..., T0=..., retries=1
```

### Possible extensions

- Loosen / increase `EPSLOOP` and `MAXLOOP` together
- Split `NTMAX` and restore `DT` once the unstable region is past
- Accumulate failure history into `failures: List[Dict]` for later analysis

---

## 2. Parameter-sweep wrapper

Performs a grid scan such as `RR x BB` and aggregates the results into
a list of dictionaries. With `NSMAX=2` left as is, the default
``PA / PZ / PN / PT`` seeds work, so no extra setup is required. Combine
with `StableTiRunner` to dodge the occasional failure case automatically.

```python
import itertools
from typing import List, Dict
from tilib import TiLib


def sweep(
    *,
    rr_values: List[float],
    bb_values: List[float],
    ntmax: int = 10,
    fixed_params: Dict | None = None,
) -> List[Dict]:
    """RR x BB grid scan. Each point runs TI in an independent session.

    Returns
    -------
    List of {RR, BB, T, T0, n0, residual, iters, error} per point
    (T0 = central electron temperature RTA[0][0], n0 = central electron density RNA[0][0])
    """
    fixed = fixed_params or {"NSMAX": 2}
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with TiLib() as ti:
                ti.set_params(RR=rr, BB=bb, **fixed)
                ti.run(ntmax=ntmax)
                state = ti.get_state()
            row.update(
                T=state.T,
                T0=state.RTA[0][0] if state.RTA else None,
                n0=state.RNA[0][0] if state.RNA else None,
                residual=state.residual_loop_max,
                iters=state.icount_loop_max,
                error=None,
            )
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
    return results


# Example usage
results = sweep(
    rr_values=[3.0, 5.0, 6.5],
    bb_values=[3.0, 5.0, 7.0],
    ntmax=10,
)
for r in results:
    print(r)
```

Expected output (excerpt; `T` is in s, `T0` in keV, `n0` in 10^20 m^-3):

```text
{'RR': 3.0, 'BB': 3.0, 'T': 0.1, 'T0': 4.9995, 'n0': 0.9986, 'residual': 0.0, 'iters': 0, ...}
{'RR': 5.0, 'BB': 5.0, 'T': 0.1, 'T0': 4.9995, 'n0': 0.9986, 'residual': 0.0, 'iters': 0, ...}
{'RR': 6.5, 'BB': 7.0, 'T': 0.1, 'T0': 4.9995, 'n0': 0.9986, 'residual': 0.0, 'iters': 0, ...}
```

```{admonition} Note: RR / BB sensitivity is small with default settings
:class: tip

With the minimal `NSMAX=2` set, heating, current drive and
neoclassical transport all run with ``MODEL_*=0`` (off), so central
``T0/n0`` barely depend on ``RR`` or ``BB``. To exercise the physical
sensitivity, enable ``MODEL_NB``, ``MODEL_NC`` etc., or switch to a
heavy-impurity setup such as ``ti_ar`` (see {doc}`parameters`).
```

### Possible extensions

- Pipe the results into a `pandas.DataFrame` and plot a heatmap
- Parallelize across processes with `multiprocessing.Pool`
  (per the singleton constraint in {doc}`faq`, **each process gets its
  own independent `TiLib` instance**, so parallelization works)
- Use `StableTiRunner` inside to handle failures automatically

---

## 3. Validate-driven setup + multi-species helper

`ti` does not yet have a native `validate()` like `tr` / `eq`. So we
build a hand-rolled checker on the Python side, and on top of that we
add a **species-dict-to-array expander helper** so callers do not have
to remember the 1-origin arrays ``PA[i] / PZ[i] / PN[i] / PT[i]``.

```python
from typing import Dict, List, Tuple
from tilib import TiLib


# Device presets (ti has no equilibrium solver, so RIP-family params are unnecessary).
DEVICE_PRESETS = {
    "ITER":  dict(RR=6.2,  BB=5.3),
    "JET":   dict(RR=2.96, BB=3.4),
    "DIIID": dict(RR=1.67, BB=2.1),
}


# Species presets. Keys are 1-origin NS numbers.
# 1: electron, 2: main ion, 3+: impurities.
# (n in 10^20 m^-3, T in keV)
SPECIES_PRESETS = {
    "DD": {
        1: {"A": 0.0005486, "Z": -1.0, "n": 1.0,  "T": 5.0},   # e
        2: {"A": 2.0,       "Z":  1.0, "n": 1.0,  "T": 5.0},   # D
    },
    "DT_with_C": {
        1: {"A": 0.0005486, "Z": -1.0, "n": 1.0,    "T": 5.0},  # e
        2: {"A": 2.5,       "Z":  1.0, "n": 0.475,  "T": 5.0},  # D+T average
        3: {"A": 12.0,      "Z":  6.0, "n": 0.05/6, "T": 5.0},  # C
    },
}


def _apply_species(ti: TiLib, species: Dict[int, Dict[str, float]]) -> None:
    """Expand a ``{ns: {'A','Z','n','T'}}`` dict into the 1-origin arrays
    ``PA[i]/PZ[i]/PN[i]/PT[i]`` and feed them to TiLib.

    Helper that hides the 1-origin subscript syntax (``PA[1]`` = electron,
    ``PA[2]`` = main ion) from the caller. ``set_params(**kwargs)`` cannot
    accept ``PA[1]`` because of Python identifier rules, so we call
    ``set_param`` one at a time.
    """
    for ns, sp in species.items():
        ti.set_param(f"PA[{ns}]", sp["A"])
        ti.set_param(f"PZ[{ns}]", sp["Z"])
        ti.set_param(f"PN[{ns}]", sp["n"])
        ti.set_param(f"PT[{ns}]", sp["T"])


def hand_validate(
    species: Dict[int, Dict[str, float]],
    nsmax: int,
) -> List[Tuple[str, str]]:
    """Since ``ti`` has no native validate, check common mistakes on the Python side.

    Returns a list of ``(target, message)`` tuples. Empty means no problems.

    Checks:
      * ``NSMAX >= 1``
      * ``len(species) == NSMAX``
      * Each species dict has all of ``A / Z / n / T``
      * Species numbers are 1-origin and contiguous (1, 2, ..., NSMAX)
    """
    diags: List[Tuple[str, str]] = []
    if nsmax < 1:
        diags.append(("NSMAX", f"NSMAX={nsmax} is less than 1"))
    if len(species) != nsmax:
        diags.append(
            ("species",
             f"species count ({len(species)}) does not match NSMAX ({nsmax})")
        )
    expected_keys = set(range(1, nsmax + 1))
    if set(species.keys()) != expected_keys:
        diags.append(
            ("species",
             f"expected species keys {sorted(expected_keys)} "
             f"(1-origin contiguous); actual: {sorted(species.keys())}")
        )
    for ns, sp in species.items():
        for k in ("A", "Z", "n", "T"):
            if k not in sp:
                diags.append((f"species[{ns}]", f"required key {k!r} is missing"))
    return diags


def auto_setup(
    device: str = "ITER",
    species_preset: str = "DD",
    extra_params: Dict | None = None,
) -> TiLib:
    """Initialize TI with a device preset + species preset and self-check
    via the hand-rolled validate.

    Returns
    -------
    A TiLib instance that is already init + set_params + validate done
    (the caller wraps it in `with` or `try/finally` for shutdown).
    """
    ti = TiLib()
    try:
        ti.__enter__()
        # 1. Apply preset (device scalars)
        params = DEVICE_PRESETS[device].copy()
        species = SPECIES_PRESETS[species_preset]
        params["NSMAX"] = len(species)
        params.update(extra_params or {})
        ti.set_params(**params)

        # 2. Expand species arrays (1-origin)
        _apply_species(ti, species)

        # 3. hand-rolled validate
        diags = hand_validate(species, params["NSMAX"])
        if diags:
            print(f"Detected problems ({len(diags)}):")
            for who, msg in diags:
                print(f"  [{who}] {msg}")
            raise RuntimeError(
                f"{len(diags)} problem(s) need to be fixed"
            )
        return ti
    except Exception:
        ti.__exit__(None, None, None)
        raise


# Example usage
with auto_setup("ITER", species_preset="DD") as ti:
    ti.run(ntmax=10)
    s = ti.get_state()
    print(f"T={s.T:.3f}s  T0={s.RTA[0][0]:.3f}keV  n0={s.RNA[0][0]:.4f}")
```

Expected output (ITER + DD preset, `ntmax=10`):

```text
T=0.100s  T0=4.999keV  n0=0.9986
```

Choosing `species_preset="DT_with_C"` gives a 3-species mix (e + D/T + C):

```text
T=0.050s  T0=4.999keV  n0=0.9997
```

If the `species` dict has gaps in its keys (e.g. ``{1: {...}, 3: {...}}``),
validate flags it:

```text
Detected problems (1):
  [species] expected species keys [1, 2] (1-origin contiguous); actual: [1, 3]
RuntimeError: 1 problem(s) need to be fixed
```

### Possible extensions

- Load presets from an external file such as `iter_baseline.toml`
- Promote switch groups like ``MODEL_NB`` / ``MODEL_NC`` into presets too
- For impurity sets, extend ``_apply_species`` to cover ``NPA[i] / ID_NS[i] /
  NZMIN_NS[i] / NZMAX_NS[i]`` as well (see ``examples/parameter_sweep.py``
  for an Ar setup)
- When called from an LLM, hand the validate output straight to the LLM
  and it will suggest fixes (see {doc}`mcp`)

---

## Combination patterns

The three are useful individually and in combination:

| Combination | Effect |
|---|---|
| **Sweep + stabilizer** | Use `StableTiRunner` inside `sweep()` to dodge numerically diverging points automatically |
| **auto_setup + sweep** | Establish a base configuration with `auto_setup`, then scan `RR x BB` etc. |
| **All three** | Stable sweeps anchored on a device preset. The standard pattern for large-scale analyses |

The same pattern applies to every other module (`tr`, `eq`, `fp`, `wr`,
`wrx`, `tot`). Just substitute the physics quantities and the
corresponding error types (`TrlibRunError`, `WrlibRunError`,
`EqlibInvalidParamError`, etc.).
