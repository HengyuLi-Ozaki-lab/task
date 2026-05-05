# Library applications (Python wrappers)

`Wrlib` is usable as-is, but wrapping it in a thin layer makes it much
more practical. Three typical patterns are shown below.

```{admonition} Where this page fits
:class: note

What follows are **application patterns for using `wrlib` from Python**.
For natural-language scenarios driving the library from an LLM client,
see {doc}`mcp`.

Note that, unlike `tr`, `wr` has **no continuous parameter such as the
time step `DT`**, so when `run()` returns `WrlibRunError(ierr=3)` there
is no natural axis along which to "halve and retry". Most failures are
**incident-geometry mistakes** (`RPI/ZPI` outside the plasma, the sign
or magnitude of `RKR0`, `RF` outside the resonance band, insufficient
`NSMAX`, etc.), so here we present `safe_run` as a wrapper that
**diagnoses which parameters look suspicious on failure**.
```

---

## 1. Diagnostic `safe_run` wrapper

A wrapper that, when `run()` raises `WrlibRunError`, checks the
parameters that were passed in and **lists the suspicious values**.
Geometry-induced `ierr=3` is a geometric-condition issue, so "where to
fix" information is more valuable than retrying.

```python
from wrlib import Wrlib
from wrlib.errors import WrlibRunError


def safe_run(wr, *, nray_request=0, params_for_diag=None):
    """Wrap `wr.run()` in try/except and report suspicious parameters on failure.

    Parameters
    ----------
    wr : Wrlib
        A Wrlib instance that has already been init + set_params'd.
    nray_request : int
        Number of rays to pass to wr.run() (0 keeps NRAYMAX).
    params_for_diag : dict or None
        Parameters to diagnose. e.g. ``{"RR": 6.2, "RA": 2.0, "RPI": 8.0,
        "RKR0": 1.0, "RF": 5.0e9, "NSMAX": 2}``.

    Returns
    -------
    A tuple (state, error_msg). On success: (WrState, None);
    on failure: (None, "...diagnostic message...").
    """
    pd = params_for_diag or {}
    try:
        wr.run(nray_request=nray_request)
        return wr.get_state(), None
    except WrlibRunError as e:
        notes = []
        rf = pd.get("RF")
        if rf is not None and not (1.0e9 <= rf <= 3.0e11):
            notes.append(f"RF={rf:g} Hz is outside the 1 GHz - 300 GHz band")
        rkr0 = pd.get("RKR0")
        if rkr0 is not None and abs(rkr0) < 1.0e-3:
            notes.append(f"RKR0={rkr0} is too close to 0 (initial wavenumber will not establish)")
        rpi = pd.get("RPI")
        rr = pd.get("RR")
        ra = pd.get("RA")
        if rpi is not None and rr is not None and ra is not None:
            if not (rr - ra <= rpi <= rr + ra):
                notes.append(
                    f"RPI={rpi} is outside the plasma range [{rr - ra}, {rr + ra}]"
                )
        nsmax = pd.get("NSMAX")
        if nsmax is not None and nsmax < 1:
            notes.append(f"NSMAX={nsmax} must be at least 1")
        msg = f"WrlibRunError: {e}"
        if notes:
            msg += "\n  Likely causes:\n    - " + "\n    - ".join(notes)
        return None, msg


# Usage example 1: healthy parameters (ITER LHCD fixture)
from wrlib.tests.fixtures import wr_iter_lhcd_params as base
with Wrlib() as wr:
    base.apply(wr)
    wr.set_param("NRAYMAX", 1)
    state, err = safe_run(
        wr, nray_request=0,
        params_for_diag={"RR": 6.2, "RA": 2.0,
                         "RPI": 8.0, "RKR0": 1.0,
                         "NSMAX": 2},
    )
    if err:
        print(err)
    else:
        print(f"OK pos_pwrmax_rl={state.scalars['pos_pwrmax_rl']:.4f}, "
              f"nstp_end={state.nstp_end}")
```

Expected output:

```text
OK pos_pwrmax_rl=4.2002, nstp_end=[100]
```

A case where the launch point is outside the device range (`RPI=10.0`
but `RR=3.0, RA=1.0`):

```python
with Wrlib() as wr:
    wr.set_params(RR=3.0, BB=3.0, RA=1.0, NSMAX=1)
    wr.set_param("RF", 170.0e9)
    wr.set_param("RPI", 10.0)   # outside device: RR-RA=2, RR+RA=4
    wr.set_param("ZPI", 0.0)
    wr.set_param("RKR0", 1.0)
    state, err = safe_run(
        wr, nray_request=1,
        params_for_diag={"RR": 3.0, "RA": 1.0,
                         "RPI": 10.0, "RKR0": 1.0,
                         "RF": 170e9, "NSMAX": 1},
    )
    print(err if err else f"OK pos_pwrmax_rl={state.scalars['pos_pwrmax_rl']}")
```

Expected output:

```text
WrlibRunError: wr_run(1): ierr=3
  Likely causes:
    - RPI=10.0 is outside the plasma range [2.0, 4.0]
```

```{admonition} Why the `pwrmax` scalars are 0
:class: note

In the current `wr` Layer-2 stage, the post-processing pipeline for
power absorption is not wired up, so `pwrmax_rs` / `pwrmax_rl` are
**always 0.0**. On the other hand, **`pos_pwrmax_*` (positions)** and
**`nstp_end` (integration-end step)** are meaningful values obtained
from the actual ray tracing. If you need an absorption profile, refer
to the `wrx` module.
```

### Possible extensions

- Accumulate a failure history in `failures: List[Dict]` for later
  analysis
- Trap `WrlibParamError` (`ierr=1`) the same way to report names not
  in the registry as typos
- A variant that flips the sign of `RKR0` and retries (for
  lower-hybrid the launch direction is sometimes opposite)

---

## 2. Parameter-sweep wrapper

Performs a grid scan such as `RFIN x ANGPHIN` (frequency x toroidal
launch angle) and aggregates the results into a list of dictionaries.
This has the same shape as the 3x3 grid pattern in
`python/wrlib/tests/test_sweep.py`.

```python
import itertools
from typing import List, Dict
from wrlib import Wrlib
from wrlib.tests.fixtures import wr_iter_lhcd_params as base


def sweep(
    *,
    rfin_values: List[float],
    angphin_values: List[float],
    fixed_params: Dict | None = None,
) -> List[Dict]:
    """Grid scan of RFIN x ANGPHIN. Each point runs wr in an independent session.

    At each point we start from the ITER-LHCD fixture, shrink to NRAYMAX=1,
    and vary only ``RFIN[1]`` (LH frequency, MHz) and ``ANGPHIN[1]``
    (toroidal launch angle, degrees).

    Returns
    -------
    A list of {RFIN[1], ANGPHIN[1], pwrmax_rs, pos_pwrmax_rs,
              pwrmax_rl, pos_pwrmax_rl, nstp_end, error} per point
    """
    fixed = fixed_params or {}
    results = []
    for rf, ang in itertools.product(rfin_values, angphin_values):
        row = {"RFIN[1]": rf, "ANGPHIN[1]": ang}
        try:
            with Wrlib() as wr:
                base.apply(wr)
                wr.set_param("NRAYMAX", 1)
                for k, v in fixed.items():
                    wr.set_param(k, v)
                wr.set_param("RFIN[1]", float(rf))
                wr.set_param("ANGPHIN[1]", float(ang))
                wr.run(0)
                state = wr.get_state()
            row.update(
                pwrmax_rs=state.scalars["pwrmax_rs"],
                pos_pwrmax_rs=state.scalars["pos_pwrmax_rs"],
                pwrmax_rl=state.scalars["pwrmax_rl"],
                pos_pwrmax_rl=state.scalars["pos_pwrmax_rl"],
                nstp_end=state.nstp_end[0],
                error=None,
            )
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
    return results


# Usage example: around ITER LHCD (LH frequency 4-6 GHz, toroidal launch angle 25-35 deg)
results = sweep(
    rfin_values=[4.0e3, 5.0e3, 6.0e3],   # MHz (= 4-6 GHz)
    angphin_values=[25.0, 30.0, 35.0],   # degrees
)
for r in results:
    if r.get("error"):
        print(f"  RFIN={r['RFIN[1]']}, ANGPHIN={r['ANGPHIN[1]']} -> {r['error']}")
    else:
        print(
            f"  RFIN={r['RFIN[1]']:>5}, ANGPHIN={r['ANGPHIN[1]']:>4}: "
            f"pos_pwrmax_rl={r['pos_pwrmax_rl']:.4f}, "
            f"nstp_end={r['nstp_end']}"
        )
```

Expected output:

```text
  RFIN=4000.0, ANGPHIN=25.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=4000.0, ANGPHIN=30.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=4000.0, ANGPHIN=35.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=5000.0, ANGPHIN=25.0: pos_pwrmax_rl=4.2002, nstp_end=98
  RFIN=5000.0, ANGPHIN=30.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=5000.0, ANGPHIN=35.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=6000.0, ANGPHIN=25.0: pos_pwrmax_rl=4.2002, nstp_end=97
  RFIN=6000.0, ANGPHIN=30.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=6000.0, ANGPHIN=35.0: pos_pwrmax_rl=4.2002, nstp_end=100
```

Points where `nstp_end` is below the integration upper limit (=100,
limited for the ITER fixture by `SMAX=5.0` / `DELS=0.05` = 100 steps;
see `wrexecr.f90:505` `NSTPLIM=MIN(INT(SMAX/DELS),NSTPMAX)`) mean that
**the integration terminated early** (e.g. the ray exited the plasma,
resonant absorption, etc.). In this sweep, `RFIN=5000, ANGPHIN=25` and
`RFIN=6000, ANGPHIN=25` finished at 98 / 97 steps respectively.

### Possible extensions

- Pipe the results into a `pandas.DataFrame` and plot a heat map
- Parallelise across processes with `multiprocessing.Pool`
  (per the singleton constraint in {doc}`faq` Q4, **each process gets
  its own independent `Wrlib` instance**, so parallelisation works)
- Use `safe_run` inside to skip failures automatically

---

## 3. Preflight-driven setup (`auto_setup`)

`wr` has no native `validate()` like `tr` / `eq`, so we **provide our
own preflight function** in the wrapper. The pattern is to start from
a device preset and check the physical reasonableness of the launch
geometry / frequency before any `set_param` call.

```python
from typing import Dict, List
from wrlib import Wrlib


# Device presets (derived from real fixtures).
# Units: RFIN is MHz (omega = 2.D6 * PI * RFIN(nray) in wr/wrexecr.f90),
#        RPIN/ZPIN are m, ANGZIN/ANGPHIN are degrees, BB is T, RR/RA are m.
DEVICE_PRESETS = {
    "ITER_LHCD": dict(
        scalars=dict(MODELG=2, RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33,
                     BB=5.3, RIP=15.0, NSMAX=2,
                     PROFN1=2.0, PROFN2=2.0, PROFT1=2.0, PROFT2=1.0,
                     NRAYMAX=1, NSTPMAX=2000, NRSMAX=50, NRLMAX=100,
                     MDLWRI=101, MDLWRQ=0, MDLWRW=0,
                     SMAX=5.0, DELS=0.05),
        arrays=dict(PA=[2.0, 1.0], PZ=[1.0, -1.0],
                    PN=[1.0, 1.0], PNS=[0.1, 0.1],
                    PTPR=[10.0, 10.0], PTPP=[10.0, 10.0],
                    PTS=[0.5, 0.5], MODELP=[4, 4],
                    RFIN=[5.0e3], RPIN=[8.0], ZPIN=[0.0],
                    PHIIN=[0.0], ANGZIN=[0.0], ANGPHIN=[30.0],
                    UUIN=[1.0], MODEWIN=[1]),
    ),
    "TST2_EC": dict(
        scalars=dict(MODELG=2, RR=0.38, RA=0.16, RKAP=1.0, RDLT=0.0,
                     BB=0.3, RIP=0.2, NSMAX=2,
                     PROFN1=2.0, PROFN2=2.0,
                     NRAYMAX=1, NSTPMAX=2000, NRSMAX=30, NRLMAX=60,
                     MDLWRI=101, MDLWRQ=0, MDLWRW=0,
                     SMAX=1.0, DELS=0.005),
        arrays=dict(PA=[2.0, 1.0], PZ=[1.0, -1.0],
                    PN=[0.5, 0.5], PNS=[0.05, 0.05],
                    PTPR=[0.5, 0.5], PTPP=[0.5, 0.5],
                    PTS=[0.05, 0.05], MODELP=[4, 4],
                    RFIN=[8.2e3], RPIN=[0.5], ZPIN=[0.0],
                    PHIIN=[0.0], ANGZIN=[0.0], ANGPHIN=[0.0],
                    UUIN=[1.0], MODEWIN=[1]),
    ),
}


def preflight(scalars: Dict, arrays: Dict) -> List[str]:
    """In-house validate for `wr`. Returns the list of issues (empty means healthy).

    Reproduces the equivalent of the `tr` / `eq` `validate()` on the
    Python side. The intended treatment is `[REQUIRED]` and
    `[ARRAY_LEN]` as blocking, `[OUT_OF_RANGE]` as a warning.
    """
    issues = []
    # Required scalars
    if scalars.get("NSMAX", 0) < 1:
        issues.append(f"[REQUIRED] NSMAX={scalars.get('NSMAX')} must be at least 1")
    if scalars.get("RR", 0) <= 0:
        issues.append(f"[REQUIRED] RR={scalars.get('RR')} must be positive")
    if scalars.get("BB", 0) == 0:
        issues.append("[REQUIRED] BB=0 is not allowed (zero magnetic field)")
    nraymax = scalars.get("NRAYMAX", 1)
    if nraymax < 1:
        issues.append(f"[REQUIRED] NRAYMAX={nraymax} must be at least 1")

    # Length check on per-ray arrays (must hold NRAYMAX entries)
    rfin = arrays.get("RFIN", [])
    if len(rfin) < nraymax:
        issues.append(
            f"[ARRAY_LEN] RFIN needs {nraymax} elements (currently {len(rfin)})"
        )
    rpin = arrays.get("RPIN", [])
    if len(rpin) < nraymax:
        issues.append(
            f"[ARRAY_LEN] RPIN needs {nraymax} elements (currently {len(rpin)})"
        )

    # Physical reasonableness (warning level)
    rr = scalars.get("RR")
    ra = scalars.get("RA")
    for i, rp in enumerate(rpin[:nraymax], start=1):
        if rp <= 0:
            issues.append(f"[OUT_OF_RANGE] RPIN[{i}]={rp} must be positive")
        if rr is not None and ra is not None:
            if not (rr - ra <= rp <= rr + ra * 4):  # launch point may be outside
                issues.append(
                    f"[OUT_OF_RANGE] RPIN[{i}]={rp} is too far from the plasma"
                    f" (expected {rr - ra} to {rr + ra * 4})"
                )
    for i, rf in enumerate(rfin[:nraymax], start=1):
        if not (1.0 <= rf <= 3.0e5):  # MHz: 1 MHz - 300 GHz
            issues.append(
                f"[OUT_OF_RANGE] RFIN[{i}]={rf} MHz is outside the 1 MHz - 300 GHz band"
            )
    return issues


def auto_setup(device: str = "ITER_LHCD", *, extra_scalars=None) -> Wrlib:
    """Initialise wrlib from a device preset and self-check via preflight.

    Returns
    -------
    A Wrlib instance that has already been init + set_params'd
    (the caller terminates it with `with` or `try/finally`).
    """
    preset = DEVICE_PRESETS[device]
    scalars = dict(preset["scalars"])
    arrays = {k: list(v) for k, v in preset["arrays"].items()}
    scalars.update(extra_scalars or {})

    # 1. preflight (check before set_param)
    issues = preflight(scalars, arrays)
    if issues:
        print(f"Issues detected ({len(issues)}):")
        for msg in issues:
            print(f"  {msg}")
        blocking = [m for m in issues if "[REQUIRED]" in m or "[ARRAY_LEN]" in m]
        if blocking:
            raise RuntimeError(
                f"{len(blocking)} blocking issue(s) remain to be fixed"
            )

    # 2. Apply
    wr = Wrlib()
    try:
        for k, v in scalars.items():
            wr.set_param(k, float(v))
        for name, arr in arrays.items():
            for i, v in enumerate(arr, start=1):
                wr.set_param(f"{name}[{i}]", float(v))
        return wr
    except Exception:
        wr.close()
        raise


# Usage example 1: ITER LHCD preset
with auto_setup("ITER_LHCD") as wr:
    wr.run(0)
    s = wr.get_state()
    print(f"ITER_LHCD: pos_pwrmax_rl={s.scalars['pos_pwrmax_rl']:.4f}, "
          f"nstp_end={s.nstp_end[0]}")

# Usage example 2: TST-2 EC preset
with auto_setup("TST2_EC") as wr:
    wr.run(0)
    s = wr.get_state()
    print(f"TST2_EC:   pos_pwrmax_rl={s.scalars['pos_pwrmax_rl']:.4f}, "
          f"nstp_end={s.nstp_end[0]}")
```

Expected output:

```text
ITER_LHCD: pos_pwrmax_rl=4.2002, nstp_end=100
TST2_EC:   pos_pwrmax_rl=0.2200, nstp_end=200
```

If you pass a blocking-level invalid value, e.g. `extra_scalars={"NSMAX": 0}`:

```python
try:
    with auto_setup("ITER_LHCD", extra_scalars={"NSMAX": 0}) as wr:
        wr.run(0)
except RuntimeError as e:
    print(f"RuntimeError: {e}")
```

Expected output:

```text
Issues detected (1):
  [REQUIRED] NSMAX=0 must be at least 1
RuntimeError: 1 blocking issue(s) remain to be fixed
```

### Possible extensions

- Read presets from external files such as `iter_lhcd.toml`
- Auto-clamping of `[OUT_OF_RANGE]` (e.g. round `RFIN=0.1` MHz up to
  `RFIN=1.0`)
- Once native `validate()` is implemented in `wr`, replace
  `preflight()` with `wr.validate()` (see issue #143's batch
  validation)
- When called from an LLM, you can hand the preflight output straight
  to the LLM and it will return a fix proposal (see {doc}`mcp`)

---

## Combination patterns

The three are usable individually or in combination:

| Combination | Effect |
|---|---|
| **safe_run + sweep** | Use `safe_run` inside `sweep()` to attach a diagnostic message at every failure point |
| **auto_setup + sweep** | Vary `RFIN x ANGPHIN` from a preset baseline (typical heating-parameter optimisation) |
| **All three** | Stable sweeps starting from a device preset, with failure diagnostics. The standard pattern for ECRH/LH design studies |

The same patterns apply to every module (`tr`, `eq`, `ti`, `fp`,
`wrx`, `tot`). Substitute the appropriate physical quantities and
error types (`TrlibRunError`, `EqlibRunError`, `WrxlibRunError`,
etc.).
