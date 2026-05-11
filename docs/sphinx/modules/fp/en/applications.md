# Library application examples (Python wrappers)

Beyond using `Fplib` as-is, putting a thin wrapper on top of it makes
real-world use much more practical. This page presents three typical
patterns.

```{admonition} Where this page fits
:class: note

What follows are **application patterns for using `fplib` from Python**.
For scenarios that drive the library from an LLM client through natural
language, see {doc}`mcp`.
```

---

## 1. Auto-stabilizing wrapper

A wrapper that halves the time step `DELT` and retries when `run()` raises
`FplibCalcFailedError` (Fokker-Planck convergence failure / overflow;
`FplibOverflowError` is a synonymous alias). Useful as a safety net in
large parameter sweeps where some combinations refuse to converge.

```python
from fplib import Fplib
from fplib.errors import FplibCalcFailedError


class StableFpRunner:
    """Wrap `Fplib` with a `with` block; halve DELT and retry on run() failure.

    Parameters
    ----------
    max_retries : int
        Upper bound on the number of DELT-shrinking attempts (DELT is halved each time).
    delt_floor : float
        Give up with RuntimeError once DELT drops below this value.
    """

    def __init__(self, *, max_retries: int = 5, delt_floor: float = 1.0e-6):
        self._fp = Fplib()
        self._fp.__enter__()
        self.delt = 1.0e-3
        self.max_retries = max_retries
        self.delt_floor = delt_floor
        self.retries = 0

    def __enter__(self) -> "StableFpRunner":
        return self

    def __exit__(self, *args) -> None:
        self._fp.__exit__(*args)

    def configure(self, **params) -> None:
        """`set_params`-compatible. Remember DELT for retries."""
        self._fp.set_params(**params)
        if "DELT" in params:
            self.delt = float(params["DELT"])

    def run(self, ntmax: int):
        """If run() fails, halve DELT and retry. Return FpState in the end."""
        for attempt in range(self.max_retries):
            try:
                self._fp.run(ntmax=ntmax)
                return self._fp.get_state()
            except FplibCalcFailedError as e:
                if self.delt <= self.delt_floor:
                    raise RuntimeError(
                        f"Did not converge even after shrinking to DELT={self.delt}: {e}"
                    ) from e
                self.delt /= 2
                self._fp.set_param("DELT", self.delt)
                self.retries += 1
                print(
                    f"  [retry] {e!r} -> shrunk to DELT={self.delt:.2e}, retrying "
                    f"({attempt + 1}/{self.max_retries})"
                )
        raise RuntimeError(
            f"Did not converge after {self.max_retries} attempts (final DELT={self.delt})"
        )


# Usage
with StableFpRunner() as runner:
    runner.configure(RR=3.0, BB=3.0, NSMAX=1, NPMAX=50, NTHMAX=25, DELT=1.0e-3)
    state = runner.run(ntmax=5)
    print(
        f"Done: timefp={state.timefp:.4f}s, "
        f"RNT[0][0]={state.RNT[0][0]:.4f}, "
        f"RTT[0][0]={state.RTT[0][0]:.4f}, "
        f"retries={runner.retries}"
    )
```

Expected output (the parameters above are stable, so no retries are
needed):

```text
Done: timefp=0.0050s, RNT[0][0]=0.9546, RTT[0][0]=4.5545, retries=0
```

For combinations that tend to diverge numerically (for example, a large
`DELT` that makes the Fokker-Planck matrix transiently ill-conditioned),
`[retry]` lines appear and `retries` becomes 1 or more:

```text
  [retry] FplibCalcFailedError(...) -> shrunk to DELT=5.00e-04, retrying (1/5)
Done: timefp=..., RNT[0][0]=..., RTT[0][0]=..., retries=1
```

```{admonition} Why halve `DELT`
:class: note

`fp`'s `run()` is a nonlinear Fokker-Planck solver with `EPSFP` (the
convergence threshold) and `LMAXFP` (the iteration limit). When the time
step `DELT` is too large, the per-step change is too big and the
iteration fails to converge within `LMAXFP`. Halving `DELT` rescues most
cases. If the cause is an extremely coarse velocity-space mesh
(`NPMAX`/`NTHMAX`), refine the mesh instead.
```

### Possible extensions

- Also relax `EPSFP` or raise `LMAXFP` on retry
- Split `NTMAX`, restoring `DELT` once you re-enter a stable regime
- Accumulate failure history into `failures: list[dict]` for later
  analysis

---

## 2. Parameter-sweep wrapper

Run a grid scan such as `RR x BB` and collect the results into a list of
dictionaries. Combined with `StableFpRunner`, partially failing cases are
handled automatically. The model here is the 3x3 sweep in
`python/fplib/tests/test_sweep.py`.

```python
import itertools
from fplib import Fplib


def sweep(
    *,
    rr_values: list[float],
    bb_values: list[float],
    ntmax: int = 10,
    fixed_params: dict | None = None,
) -> list[dict]:
    """RR x BB grid scan. Each point runs fp in an independent session.

    Returns
    -------
    A list of {RR, BB, timefp, RNT0, RTT0, RWT_last, error} for each point.
    `RNT0` is the particle-number density at the centre (NR=1); `RWT_last`
    is the energy density at the edge (NR=NRMAX).
    """
    fixed = fixed_params or {
        "NSMAX": 1, "NRMAX": 10, "NPMAX": 30, "NTHMAX": 30, "DELT": 1.0e-3,
    }
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with Fplib() as fp:
                fp.set_params(RR=rr, BB=bb, **fixed)
                fp.run(ntmax=ntmax)
                state = fp.get_state()
            row.update(
                timefp=state.timefp,
                RNT0=state.RNT[0][0],
                RTT0=state.RTT[0][0],
                RWT_last=state.RWT[0][-1],
                error=None,
            )
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
    return results


# Usage
results = sweep(
    rr_values=[3.0, 5.0, 6.5],
    bb_values=[3.0, 5.0, 7.0],
    ntmax=10,
)
for r in results:
    if r.get("error"):
        print(f"  RR={r['RR']}, BB={r['BB']} -> ERROR")
    else:
        print(
            f"  RR={r['RR']}, BB={r['BB']}: "
            f"RNT[0]={r['RNT0']:.4f}, RWT[-1]={r['RWT_last']:.6f}"
        )
```

Expected output (excerpt):

```text
  RR=3.0, BB=3.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=3.0, BB=5.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=3.0, BB=7.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=5.0, BB=5.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=6.5, BB=7.0: RNT[0]=0.9985, RWT[-1]=0.105721
```

```{admonition} Why all 9 points return the same values
:class: tip

`fp` is a solver for the **Fokker-Planck equation in velocity space
(momentum and pitch angle)**, so it is rate-limited by the local
`(temperature, density)` and is not directly affected by the device size
`RR` or the field strength `BB`. Because the sweep above keeps `PTPR`
and `PN` fixed, all 9 points converge to the same thermal-equilibrium
distribution. To see the effect of RR/BB, either go **through the MHD
equilibrium** (pass an eqdsk with `MODELG=3`) or enable **bounce
averaging** (`MODEL_FOW=1`), or vary axes on the physics side (`PTPR`,
`PN`, `E0`, etc.).
```

### Possible extensions

- Switching to a `PTPR x PN` (temperature x density) sweep moves the
  Maxwellian moments immediately, which makes a useful smoke test for
  the sweep itself
- Pipe the results into a `pandas.DataFrame` and turn them into a
  heat map
- Parallelise over multiple processes with `multiprocessing.Pool`
  (per the singleton constraint in {doc}`faq`, **each process gets its
  own independent `Fplib` instance**, so process-level parallelism
  works)
- Use `StableFpRunner` inside the loop to bypass failures automatically

---

## 3. validate-driven setup

`fp` does not have a C-ABI `validate()` like `tr` / `eq`, so this is a
wrapper that performs a **hand-rolled preflight check**. Use it to
"sanitise" user input before `run()`. It ships with the device presets
ITER / JET / JT60SA.

```python
from fplib import Fplib


# Device presets.
# Because fp is a Fokker-Planck solver, RIP is specified as a single value.
# (For tr it would be the RIPS / RIPE pair, since the current is time-dependent.)
DEVICE_PRESETS = {
    "ITER":   dict(RR=6.2,  RA=2.0,  BB=5.3,  RIP=15.0, RKAP=1.7,  RDLT=0.5),
    "JET":    dict(RR=2.96, RA=1.0,  BB=3.4,  RIP=4.0,  RKAP=1.6,  RDLT=0.3),
    "JT60SA": dict(RR=2.97, RA=1.18, BB=2.25, RIP=5.5,  RKAP=1.95, RDLT=0.5),
}


def validate_fp_params(params: dict) -> list[tuple[str, str]]:
    """Preflight-check fp inputs and return a list of `(param, message)`.

    Since `fp` has no C-ABI `validate()`, we catch only the typical
    mistakes by hand:

    * `NSMAX >= 1` (with no species, fp_init STOPs)
    * `NPMAX > 5`, `NTHMAX > 5` (the Fokker-Planck operator is meaningless
      when the momentum/pitch-angle resolution is too low)
    * `NRMAX > 5` (the radial gradient of the distribution function cannot
      be resolved at low radial resolution)
    """
    diags: list[tuple[str, str]] = []
    nsmax = int(params.get("NSMAX", 1))
    if nsmax < 1:
        diags.append(("NSMAX", f"NSMAX={nsmax} must be >= 1"))
    npmax = int(params.get("NPMAX", 50))
    if npmax <= 5:
        diags.append(("NPMAX",
                      f"NPMAX={npmax}: recommend >= 6 (momentum-space resolution too low)"))
    nthmax = int(params.get("NTHMAX", 25))
    if nthmax <= 5:
        diags.append(("NTHMAX",
                      f"NTHMAX={nthmax}: recommend >= 6 (pitch-angle resolution too low)"))
    nrmax = int(params.get("NRMAX", 10))
    if nrmax <= 5:
        diags.append(("NRMAX",
                      f"NRMAX={nrmax}: recommend >= 6 (radial resolution too low)"))
    return diags


def auto_setup(
    device: str = "ITER",
    extra_params: dict | None = None,
) -> Fplib:
    """Initialise fp with a device preset and self-check via validate_fp_params.

    Returns
    -------
    An Fplib instance that has already been init'd and had set_params applied
    (the caller is responsible for cleanup via `with` or `try/finally`).
    """
    fp = Fplib()
    try:
        fp.__enter__()
        # 1. Apply preset + safe default mesh / time step for fp
        params = DEVICE_PRESETS[device].copy()
        params.update(NSMAX=1, NPMAX=30, NTHMAX=30, NRMAX=10, DELT=1.0e-3)
        params.update(extra_params or {})

        # 2. Hand-rolled preflight check
        diags = validate_fp_params(params)
        if diags:
            print(f"Issues detected ({len(diags)}):")
            for name, msg in diags:
                print(f"  [INVALID] {name}: {msg}")
            raise RuntimeError(
                f"{len(diags)} issue(s) need to be fixed"
            )

        # 3. Apply parameters (after preflight passes)
        fp.set_params(**params)
        return fp
    except Exception:
        fp.__exit__(None, None, None)
        raise


# Usage
with auto_setup("ITER") as fp:
    fp.run(ntmax=10)
    state = fp.get_state()
    print(
        f"timefp={state.timefp:.4f}s, "
        f"RNT[0][0]={state.RNT[0][0]:.4f}, "
        f"RTT[0][0]={state.RTT[0][0]:.4f}"
    )
```

Expected output (ITER preset, `ntmax=10`):

```text
timefp=0.0100s, RNT[0][0]=0.9985, RTT[0][0]=4.9807
```

When you pass an overly coarse velocity-space mesh such as `NPMAX=4`:

```text
Issues detected (1):
  [INVALID] NPMAX: NPMAX=4: recommend >= 6 (momentum-space resolution too low)
RuntimeError: 1 issue(s) need to be fixed
```

```{admonition} `fp`-specific preflight points
:class: warning

- **`NSMAX < 1`**: stops inside `fp_init` (a representative case of
  library-reachable `STOP`; CLAUDE.md issue #142). Always reject this in
  preflight.
- **`NPMAX/NTHMAX < 6`**: the library itself sometimes runs through, but
  the velocity-space integrals become meaningless and the moments
  diverge. Stopping at preflight is the safe choice.
- **The device's `BB`/`RR`/`RIP` pass through as values only**: because
  `fp` is a velocity-space solver, geometry dependence is weak (see the
  sweep example above), so `run()` itself succeeds even when the preset
  values are off.
```

### Possible extensions

- Read the presets from an external file such as `iter_baseline.toml`
- Reuse the `fp_iter01_params` fixture
  (`python/fplib/tests/fixtures/`) directly as the base of `auto_setup`
  to reproduce a realistic ITER01 physics case
- When called from an LLM, hand the output of `validate_fp_params`
  straight to the LLM and let it suggest fixes (see {doc}`mcp`)

---

## Combination patterns

The three can be used individually or combined:

| Combination | Effect |
|---|---|
| **Sweep + stabilisation** | Use `StableFpRunner` inside `sweep()` to bypass numerically-divergent points automatically |
| **validate-setup + sweep** | Use `auto_setup` for the base configuration, then vary `PTPR x PN` and so on |
| **All three** | A stabilised sweep starting from a device preset. The standard pattern for large-scale Fokker-Planck analyses |

The same patterns apply to the other modules (`tr`, `eq`, `ti`, `wr`,
`wrx`, `tot`). Substitute the appropriate physical quantities and error
types (`TrlibRunError`, `EqlibInvalidParamError`, etc.).
