# Library application examples (Python wrappers)

`Trlib` is usable on its own, but wrapping it in a thin Python layer
makes it considerably more practical. This page shows three typical
patterns.

```{admonition} Where this page fits
:class: note

What you see here are **application patterns for using `trlib` from
Python**. For scenarios that drive `tr` from an LLM client in natural
language, see the "Usage scenarios" section of {doc}`mcp`.
```

---

## 1. Auto-stabilizing wrapper

A wrapper that halves `DT` and retries when `run()` raises a
`TrlibRunError`. Useful as a safety net during large parameter sweeps
where some combinations fail to converge.

```python
from trlib import Trlib
from trlib.errors import TrlibRunError


class StableTrRunner:
    """Wraps `Trlib` in a `with` context and retries with halved DT
    on run() failure.

    Parameters
    ----------
    max_retries : int
        Maximum number of retries (DT is halved each attempt).
    dt_floor : float
        Give up with RuntimeError once DT drops below this floor.
    """

    def __init__(self, *, max_retries: int = 5, dt_floor: float = 1.0e-5):
        self._tr = Trlib()
        self._tr.__enter__()
        self.dt = 0.01
        self.max_retries = max_retries
        self.dt_floor = dt_floor
        self.retries = 0

    def __enter__(self) -> "StableTrRunner":
        return self

    def __exit__(self, *args) -> None:
        self._tr.__exit__(*args)

    def configure(self, **params) -> None:
        """`set_params`-compatible. Remembers DT for the retry loop."""
        self._tr.set_params(**params)
        if "DT" in params:
            self.dt = float(params["DT"])

    def run(self, ntmax: int):
        """Retry with halved DT on failure. Returns the final TrState."""
        for attempt in range(self.max_retries):
            try:
                self._tr.run(ntmax=ntmax)
                return self._tr.get_state()
            except TrlibRunError as e:
                if self.dt <= self.dt_floor:
                    raise RuntimeError(
                        f"Did not stabilize even at DT={self.dt}: {e}"
                    ) from e
                self.dt /= 2
                self._tr.set_param("DT", self.dt)
                self.retries += 1
                print(
                    f"  [retry] {e!r} -> shrink DT to {self.dt:.2e}, "
                    f"retry ({attempt + 1}/{self.max_retries})"
                )
        raise RuntimeError(
            f"Did not stabilize after {self.max_retries} retries "
            f"(final DT={self.dt})"
        )


# Usage example
with StableTrRunner() as runner:
    runner.configure(RR=3.0, BB=3.0, NSMAX=2, DT=0.01, NTMAX=100)
    state = runner.run(ntmax=100)
    print(f"completed: T={state.scalars['T']:.3f}s, "
          f"BETAN={state.scalars['BETAN']:.3f}, "
          f"retries={runner.retries}")
```

Expected output (the parameters above are stable, so no retry fires):

```
completed: T=1.000s, BETAN=0.283, retries=0
```

For combinations prone to numerical divergence (e.g. extreme `BB`,
large `DT`), `[retry]` lines appear in the log and `retries` will be
1 or more:

```
[retry] TrlibRunError(...) -> shrink DT to 5.00e-03, retry (1/5)
completed: T=..., BETAN=..., retries=1
```

### Possible extensions

- Loosen `EPSLTR` / raise `LMAXTR` together with halving `DT`.
- Split `NTMAX` into chunks; once past the unstable region, restore
  `DT` to its original value.
- Accumulate failure history into `failures: list[dict]` for
  postmortem analysis.

---

## 2. Parameter-sweep wrapper

Performs a grid scan such as `RR x BB` and aggregates the results
into a list of dicts. Combine with `StableTrRunner` to auto-skip
the points that fail.

```python
import itertools
from trlib import Trlib


def sweep(
    *,
    rr_values: list[float],
    bb_values: list[float],
    ntmax: int = 10,
    fixed_params: dict | None = None,
) -> list[dict]:
    """Grid scan over RR x BB. Each point runs tr in an independent session.

    Returns
    -------
    A list of dicts, each containing {RR, BB, T, WPT, BETAN, TAUE1, error}.
    """
    fixed = fixed_params or {"NSMAX": 2}
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with Trlib() as tr:
                tr.set_params(RR=rr, BB=bb, **fixed)
                tr.run(ntmax=ntmax)
                state = tr.get_state()
            row.update(
                T=state.scalars["T"],
                WPT=state.scalars["WPT"],
                BETAN=state.scalars["BETAN"],
                TAUE1=state.scalars["TAUE1"],
                error=None,
            )
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
    return results


# Usage example
results = sweep(
    rr_values=[3.0, 5.0, 6.5],
    bb_values=[3.0, 5.0, 7.0],
    ntmax=20,
)
for r in results:
    print(r)
```

Expected output (excerpt; `WPT` is in MJ):

```text
{'RR': 3.0, 'BB': 3.0, 'T': 0.2, 'WPT': 1.65, 'BETAN': 0.288, ...}
{'RR': 5.0, 'BB': 5.0, 'T': 0.2, 'WPT': 2.95, 'BETAN': 0.186, ...}
{'RR': 6.5, 'BB': 7.0, 'T': 0.2, 'WPT': 3.96, 'BETAN': 0.137, ...}
```

### Possible extensions

- Pipe results into a `pandas.DataFrame` and render a heatmap.
- Parallelise across multiple processes with `multiprocessing.Pool`
  (per the singleton constraint in {doc}`faq` Q4, parallelisation
  works because **each process has its own independent `Trlib`
  instance**).
- Use `StableTrRunner` inside the loop for automatic retry on failure.

---

## 3. validate-driven setup

A function that watches the output of `validate()` to automatically
detect and auto-fill common mistakes. Use it to "sanitise" user
input before calling `run()`.

```python
from trlib import Trlib, TrDiagCode


# Device presets.
# tr models a time-dependent current, so it takes the (RIPS, RIPE)
# pair (start / end). For steady-state analysis set them to the same
# value. (eq, by contrast, takes a single RIP.)
DEVICE_PRESETS = {
    "ITER":  dict(RR=6.2,  RA=2.0,  BB=5.3, RIPS=15.0, RIPE=15.0, RKAP=1.7, RDLT=0.5),
    "JET":   dict(RR=2.96, RA=1.0,  BB=3.4, RIPS=4.0,  RIPE=4.0,  RKAP=1.6, RDLT=0.3),
    "DIIID": dict(RR=1.67, RA=0.67, BB=2.1, RIPS=2.0,  RIPE=2.0,  RKAP=1.8, RDLT=0.4),
}


def auto_setup(
    device: str = "ITER",
    extra_params: dict | None = None,
    eq_file: str | None = None,
) -> Trlib:
    """Initialise tr from a device preset and self-check via validate.

    Returns
    -------
    A Trlib instance that has already been init + set_params + validated
    (the caller is responsible for closing it via `with` or try/finally).
    """
    tr = Trlib()
    try:
        tr.__enter__()
        # 1. Apply the preset
        params = DEVICE_PRESETS[device].copy()
        params.update(NSMAX=2, DT=0.01, NTMAX=100)
        params.update(extra_params or {})
        tr.set_params(**params)

        # 2. If routed via EQDSK, set KNAMEQ as required.
        #    If eq_file is None, set KNAMEQ explicitly to the empty
        #    string so that validate's FILE_MISSING check picks it up
        #    (leaving the default KNAMEQ='eqdata' would silently pass
        #    validate and then die at run time with ierr=3).
        if params.get("MODELG") in (3, 5, 7, 8):
            tr.set_param_str("KNAMEQ", eq_file or "")

        # 3. Check via validate
        diags = tr.validate()
        if diags:
            print(f"Detected issues ({len(diags)} item(s)):")
            for d in diags:
                code = TrDiagCode(d.code).name
                print(f"  [{code}] {d.param}: {d.message}")
            blocking = [d for d in diags
                        if d.code in (TrDiagCode.FILE_MISSING,
                                      TrDiagCode.MISSING_REQUIRED)]
            if blocking:
                raise RuntimeError(
                    f"{len(blocking)} blocking issue(s) remain to be fixed"
                )
        return tr
    except Exception:
        tr.__exit__(None, None, None)
        raise


# Usage example
with auto_setup("ITER") as tr:
    tr.run(ntmax=10)
    state = tr.get_state()
    print(f"BETAN = {state.scalars['BETAN']:.3f}")
```

Expected output (ITER preset, `ntmax=10`):

```text
BETAN = 0.074
```

When `MODELG=3` is specified but `eq_file=None`:

```text
Detected issues (1 item(s)):
  [FILE_MISSING] KNAMEQ: MODELG=3/5/7/8 requires non-blank KNAMEQ ...
RuntimeError: 1 blocking issue(s) remain to be fixed
```

### Possible extensions

- Read the presets from an external file such as `iter_baseline.toml`.
- Auto-clamp on `OUT_OF_RANGE` (e.g. round `NSMAX=10` down to
  `NSMAX=8`).
- When called from an LLM, pass the `validate` output straight to the
  LLM and you will get a corrective suggestion back (see "Usage
  scenarios" in {doc}`mcp`).

---

## Combination patterns

The three patterns can be used individually or in combination:

| Combination | Effect |
|---|---|
| **sweep + auto-stabilize** | Use `StableTrRunner` inside `sweep()` so the divergent points are auto-skipped |
| **validate setup + sweep** | Use `auto_setup` for the baseline, then sweep `RR x BB` etc. |
| **All three** | Stable sweep starting from a device preset. The standard pattern for large-scale analysis |

The same patterns apply to the other modules (`eq`, `ti`, `fp`, `wr`,
`wrx`, `tot`); just substitute the relevant physical quantities and
error types (`EqlibInvalidParamError`, `WrlibRunError`, etc.).
