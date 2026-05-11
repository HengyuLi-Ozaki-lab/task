# Library application examples (Python wrappers)

`Wrxlib` is usable on its own, but layering a thin wrapper on top makes
it much more practical. This page presents three typical patterns.

```{admonition} Scope of this page
:class: note

What follows are **application patterns for using `wrxlib` from Python**.
For scenarios where an LLM client drives the library through natural
language, see {doc}`mcp`.
```

```{note}
`Wrxlib.run()` used to have a known issue where it would SEGV through
the `wrcalpwr -> libgrf::grd1d` path, requiring tests to set
`WRX_RUN_OK=1` explicitly. PR #123 fixed the root cause (`wrx_api_init`
now `setenv`s `WRX_NO_GRAPHICS`), and PR #166 made `WRX_RUN_OK=1` the
default. The samples on this page run without any special environment
variables.
```

---

## 1. Safe-execution wrapper (geometry preflight + safe_run)

As with the `wr` family, the leading cause of `run()` failure in `wrx`
is the **launch geometry** (`RPIN[i]` falling outside the plasma
boundary `RR ± (RA + RB)`, an extreme `ANGTIN[i]` that prevents the
trajectory from crossing the boundary, and so on). Because these are
not failures of numerical integration, **retries such as halving DT do
not help**. Instead, a `safe_run` that performs a lightweight per-ray
geometry check before execution and logs the failing ray indices and
suspect inputs is much more useful.

```python
from wrxlib import Wrxlib
from wrxlib.errors import WrxlibRunError


def _ray_sanity(ray: dict, *, rr: float, ra: float, rb: float) -> list[str]:
    """Lightly check one ray's inputs and return a list of issues."""
    issues: list[str] = []
    rpi = ray.get("RPI")
    if rpi is None:
        issues.append("RPI not specified")
    else:
        rmin, rmax = rr - (ra + rb), rr + (ra + rb)
        if not (rmin <= rpi <= rmax):
            issues.append(f"RPI={rpi} is outside plasma boundary [{rmin:.2f},{rmax:.2f}]")
    rf = ray.get("RF")
    if rf is None or rf <= 0.0:
        issues.append(f"RF={rf} is non-positive")
    angt = ray.get("ANGT", 0.0)
    if abs(angt) > 60.0:
        issues.append(f"ANGT={angt} exceeds +/-60 degrees")
    return issues


def safe_run(wrx: Wrxlib, rays: list[dict], *,
             rr: float, ra: float, rb: float) -> dict:
    """Run `wrx.run()`. On failure return a ray-launch sanity report."""
    # 1. preflight (pure Python; does not touch the library)
    report = {"preflight": [], "run_ok": False, "error": None}
    for i, ray in enumerate(rays, start=1):
        issues = _ray_sanity(ray, rr=rr, ra=ra, rb=rb)
        if issues:
            report["preflight"].append({"ray": i, "issues": issues})

    # 2. attempt the run anyway (preflight is warning-only)
    try:
        wrx.run(nray_request=0)
        report["run_ok"] = True
        report["state"] = wrx.get_state()
    except WrxlibRunError as e:
        report["error"] = repr(e)
        # On failure, surface the rays flagged by preflight as prime suspects
        suspects = [r["ray"] for r in report["preflight"]]
        if suspects:
            print(f"  [safe_run] WrxlibRunError: suspect ray indices = {suspects}")
            for r in report["preflight"]:
                print(f"    ray {r['ray']}: {', '.join(r['issues'])}")
        else:
            print(f"  [safe_run] WrxlibRunError: slipped past preflight "
                  f"({e!r}); re-check the ANGTIN/MODELP combination")
    return report


# Example
BASE = dict(MODELG=2, MODELQ=0, RR=6.2, RA=2.0, RB=2.2, BB=5.3,
            Q0=1.0, QA=3.5, PROFJ=1.0, NSMAX=2, NSTPMAX=2000,
            MDLWRI=2, MDLWRQ=1, MDLWRG=1, MDLWRP=1, MDLWRW=0,
            pne_threshold=1.0e-6, SMAX=2.0, DELS=1.0e-3)
SPECIES = [("PA[1]", 2.0), ("PA[2]", 5.4462e-4),
           ("PZ[1]", 1.0), ("PZ[2]", -1.0),
           ("PN[1]", 1.0), ("PN[2]", 1.0),
           ("PNS[1]", 0.05), ("PNS[2]", 0.05),
           ("PTPR[1]", 10.0), ("PTPP[1]", 10.0),
           ("PTPR[2]", 10.0), ("PTPP[2]", 10.0),
           ("PTS[1]", 0.5), ("PTS[2]", 0.5),
           ("PROFN1[1]", 2.0), ("PROFN1[2]", 2.0),
           ("PROFN2[1]", 1.0), ("PROFN2[2]", 1.0),
           ("PROFT1[1]", 2.0), ("PROFT1[2]", 2.0),
           ("PROFT2[1]", 1.0), ("PROFT2[2]", 1.0),
           ("MODELP[1]", 206), ("MODELP[2]", 206),
           ("MODELV[1]", 3), ("MODELV[2]", 0),
           ("NCMIN[1]", -3), ("NCMIN[2]", -3),
           ("NCMAX[1]", 3),  ("NCMAX[2]", 3)]

bad_rays = [{"RF": 170.0e3, "RPI": 1.0, "ZPI": 0.0, "ANGT": 10.0}]  # RPI is outside the boundary
with Wrxlib() as wrx:
    wrx.set_params(NRAYMAX=1, **BASE)
    for n, v in SPECIES:
        wrx.set_param(n, v)
    for i, r in enumerate(bad_rays, start=1):
        wrx.set_param(f"RFIN[{i}]", r["RF"])
        wrx.set_param(f"RPIN[{i}]", r["RPI"])
        wrx.set_param(f"ZPIN[{i}]", r["ZPI"])
        wrx.set_param(f"PHIIN[{i}]", 0.0)
        wrx.set_param(f"ANGPIN[{i}]", 0.0)
        wrx.set_param(f"ANGTIN[{i}]", r["ANGT"])
        wrx.set_param(f"UUIN[{i}]", 1.0)
        wrx.set_param(f"MODEWIN[{i}]", 1)
    rep = safe_run(wrx, bad_rays, rr=6.2, ra=2.0, rb=2.2)
    print(f"run_ok = {rep['run_ok']}, error = {rep['error']}")
```

Expected output (`RPI=1.0` is below `RR-(RA+RB)=2.0`, so preflight
flags it and the library returns `WrxlibRunError(ierr=3)`):

```text
  [safe_run] WrxlibRunError: suspect ray indices = [1]
    ray 1: RPI=1.0 is outside plasma boundary [2.00,10.40]
run_ok = False, error = "WrxlibRunError('wrx_run(0): ierr=3')"
```

For a healthy launch (e.g. `RPI=8.0, ANGT=10.0`) `preflight` is an
empty list, `run_ok=True`, and `state.scalars["pwr_tot"] ~ 0.78`.

### Possible extensions

- Have preflight also check the consistency of `MODELP[i]`, `NCMIN[i]`,
  and `NCMAX[i]` (e.g. `MODELP=206` (relativistic) with `NCMAX < 1`
  yields zero absorption).
- Accumulate failure history in `failures: list[dict]` for later analysis.
- For large fans where only a single ray fails, add logic that
  **excludes that ray and retries** (`NRAYMAX -= 1`, repack the ray
  array).

---

## 2. Multi-ray fan sweep

Vary `ANGTIN[i]` (toroidal launch angle) to fire **multiple rays in
one session**, then aggregate per-ray absorbed power and per-species
absorption. Factoring the ray-array assembly into an `_apply_rays`
helper makes the code reusable when only the ray count changes.

```python
from wrxlib import Wrxlib


def _apply_rays(wrx: Wrxlib, rays: list[dict]) -> None:
    """Write list-of-dict rays into the 1-origin array elements.

    Each key (RF, RPI, ZPI, ANGPHI, ANGT, MODEW, UU) of `rays[k]`
    becomes `RFIN[k+1]`, `RPIN[k+1]`, ... Missing keys get defaults.
    NRAYMAX must be set by the caller via `set_params(NRAYMAX=len(rays))`.
    """
    DEFAULTS = {"PHII": 0.0, "ANGPHI": 0.0, "ANGT": 10.0,
                "UU": 1.0, "MODEW": 1, "ZPI": 0.0}
    for i, ray in enumerate(rays, start=1):
        merged = {**DEFAULTS, **ray}
        wrx.set_param(f"RFIN[{i}]",   float(merged["RF"]))
        wrx.set_param(f"RPIN[{i}]",   float(merged["RPI"]))
        wrx.set_param(f"ZPIN[{i}]",   float(merged["ZPI"]))
        wrx.set_param(f"PHIIN[{i}]",  float(merged["PHII"]))
        wrx.set_param(f"ANGPIN[{i}]", float(merged["ANGPHI"]))
        wrx.set_param(f"ANGTIN[{i}]", float(merged["ANGT"]))
        wrx.set_param(f"UUIN[{i}]",   float(merged["UU"]))
        wrx.set_param(f"MODEWIN[{i}]", float(merged["MODEW"]))


def fan_sweep(angles: list[float], *, base_params: dict,
              species_params: list, rpi: float = 8.0,
              freq_hz: float = 170.0e3) -> dict:
    """Single fan with ANGTIN swept over `angles`. Aggregates `pwr_tot` and `pwr_nsa`."""
    rays = [{"RF": freq_hz, "RPI": rpi, "ZPI": 0.0, "ANGT": a} for a in angles]
    with Wrxlib() as wrx:
        wrx.set_params(NRAYMAX=len(rays), **base_params)
        for n, v in species_params:
            wrx.set_param(n, v)
        _apply_rays(wrx, rays)
        wrx.run(nray_request=0)
        s = wrx.get_state()
    return {
        "angles": angles,
        "pwr_tot": s.scalars["pwr_tot"],
        "pwr_nsa": list(s.pwr_nsa),                 # per-species absorption (total)
        "pwr_nsa_nray": [list(r) for r in s.pwr_nsa_nray],  # ray x species
    }


# Example (BASE / SPECIES are the same as in section 1)
res = fan_sweep([8.0, 10.0, 12.0], base_params=BASE, species_params=SPECIES)
print(f"pwr_tot      = {res['pwr_tot']:.4f}")
print(f"pwr_nsa      = {res['pwr_nsa']}")
for i, row in enumerate(res["pwr_nsa_nray"], start=1):
    print(f"  ray {i} (ANGT={res['angles'][i-1]:+.1f}): {row}")
```

Expected output (`170 GHz`, ITER geometry, 3-ray fan at ANGTIN=8/10/12 deg):

```text
pwr_tot      = 1.9122
pwr_nsa      = [1.9122187578892103, 0.0]
  ray 1 (ANGT=+8.0): [0.1333348100650216, 0.0]
  ray 2 (ANGT=+10.0): [0.7839621620662179, 0.0]
  ray 3 (ANGT=+12.0): [0.9949217857579706, 0.0]
```

The mapping between ray index and launch angle is obvious at a glance,
which makes the angle-sweep sensitivity easy to read off. Note that
`pwr_nray[i]` always returns `0.0` in this build (a known limitation) —
to obtain per-ray absorption, sum `pwr_nsa_nray[i][isa]` instead.

### Possible extensions

- Pipe the results into a `pandas.DataFrame` and plot the angle-sweep
  curve.
- Parallelise across processes with `multiprocessing.Pool` (per the
  singleton constraint in {doc}`faq`, each process gets its **own
  independent `Wrxlib` instance**, so this parallelisation works).
- Use the `safe_run` from section 1 inside the loop so that the fan
  still aggregates a result even when some rays fail.

---

## 3. auto_setup with a hand-rolled validate + multi-ray preset

`wrx` does not expose a `validate()` API, so we substitute a
**hand-rolled preflight** plus **device presets**. A preset separates
"device geometry (RR/BB/...)" from "ray list" so that design-time
diffs stay manageable.

```python
from wrxlib import Wrxlib


REQUIRED_RAY_KEYS = ("RF", "RPI", "ZPI", "ANGT")


# Device presets. shape goes straight to set_params; rays go via _apply_rays.
DEVICE_PRESETS = {
    "ITER_LHCD_2ray": {
        "shape": dict(MODELG=2, MODELQ=0,
                      RR=6.2, RA=2.0, RB=2.2, BB=5.3,
                      Q0=1.0, QA=3.5, PROFJ=1.0,
                      NSMAX=2, NSTPMAX=2000,
                      MDLWRI=2, MDLWRQ=1, MDLWRG=1, MDLWRP=1, MDLWRW=0,
                      pne_threshold=1.0e-6, SMAX=2.0, DELS=1.0e-3),
        "rays": [
            {"RF": 170.0e3, "RPI": 8.0, "ZPI":  0.5, "ANGT": 10.0},
            {"RF": 170.0e3, "RPI": 8.0, "ZPI": -0.5, "ANGT": 10.0},
        ],
    },
}


def _hand_validate(shape: dict, rays: list[dict]) -> list[str]:
    """Stand-in `validate` for `wrx`. Returns a list of blocking issues."""
    diags: list[str] = []
    nsmax = int(shape.get("NSMAX", 0))
    if nsmax < 1:
        diags.append(f"[NSMAX] NSMAX={nsmax} must be >= 1")
    if not rays:
        diags.append("[NRAYMAX] rays is empty")
    for i, ray in enumerate(rays, start=1):
        missing = [k for k in REQUIRED_RAY_KEYS if k not in ray]
        if missing:
            diags.append(f"[ray {i}] missing required keys: {missing}")
    return diags


def auto_setup(device: str = "ITER_LHCD_2ray",
               extra_shape: dict | None = None,
               extra_rays: list[dict] | None = None) -> Wrxlib:
    """Initialise wrx from a device preset and self-check via the hand-rolled validate."""
    preset = DEVICE_PRESETS[device]
    shape = {**preset["shape"], **(extra_shape or {})}
    rays = list(preset["rays"]) + list(extra_rays or [])

    # 1. validate (pure Python check before init)
    diags = _hand_validate(shape, rays)
    if diags:
        print(f"Detected issues ({len(diags)}):")
        for d in diags:
            print(f"  {d}")
        raise RuntimeError(f"{len(diags)} issue(s) still need to be fixed")

    # 2. Set NRAYMAX from rays (alternatively the validator could enforce
    #    len(rays)==NRAYMAX, but auto-derive lets the user override NRAYMAX
    #    directly).
    shape["NRAYMAX"] = len(rays)

    wrx = Wrxlib()
    try:
        wrx.__enter__()
        wrx.set_params(**shape)
        # 3. Species parameters (this sample assumes species can be swapped in
        #    via extra_shape; here we reuse the SPECIES list from section 1).
        for n, v in SPECIES:
            wrx.set_param(n, v)
        _apply_rays(wrx, rays)
        return wrx
    except Exception:
        wrx.__exit__(None, None, None)
        raise


# Example
with auto_setup("ITER_LHCD_2ray") as wrx:
    wrx.run(nray_request=0)
    s = wrx.get_state()
    print(f"pwr_tot = {s.scalars['pwr_tot']:.4f}")
    print(f"pwr_nsa = {s.pwr_nsa}")
    print(f"per-ray per-species:")
    for i, row in enumerate(s.pwr_nsa_nray, start=1):
        print(f"  ray {i}: {row}")
```

Expected output (`ITER_LHCD_2ray`, 2-ray fan):

```text
pwr_tot = 1.0073
pwr_nsa = [1.0073080764455387, 0.0]
per-ray per-species:
  ray 1: [0.9990350770648171, 0.0]
  ray 2: [0.008272999380721565, 0.0]
```

When **required keys are missing**, e.g. `extra_rays=[{"RF": 170.0e3}]`:

```text
Detected issues (1):
  [ray 3] missing required keys: ['RPI', 'ZPI', 'ANGT']
RuntimeError: 1 issue(s) still need to be fixed
```

For `extra_shape={"NSMAX": 0}`:

```text
Detected issues (1):
  [NSMAX] NSMAX=0 must be >= 1
RuntimeError: 1 issue(s) still need to be fixed
```

### Possible extensions

- Load presets from external files such as `iter_lhcd_2ray.toml`.
- Carry `RBRADAIN[i]` / `RCURVAIN[i]` as additional keys in `rays[i]`
  so that beam-tracing-specific beam shapes can also be presetted.
- When invoked from an LLM, hand the output of `_hand_validate` straight
  to the LLM to receive correction suggestions (see {doc}`mcp`).

---

## Combination patterns

The three patterns work individually but compose naturally:

| Combination | Effect |
|---|---|
| **fan + safe_run** | Wrap `safe_run` inside `fan_sweep` so a single failing ray does not block `pwr_tot` for the rest |
| **auto_setup + fan** | Establish a base configuration with `auto_setup`, then sweep `ANGTIN` or `RPIN` with `fan_sweep` |
| **All three** | A device-preset-anchored, robust multi-ray scan — the standard pattern for ECCD/LHCD design studies |

The same patterns apply to every other module (`tr`, `eq`, `ti`, `fp`,
`wr`, `tot`); just substitute the relevant physical quantities and
error types (`TrlibRunError`, `EqlibInvalidParamError`,
`WrlibRunError`, etc.).
