# Tutorials

```{admonition} Where this page fits
:class: tip

Two end-to-end worked examples, building on what
{doc}`hello-world`, {doc}`parameter-setting`, and
{doc}`applications` cover. **D1** of the multi-scenario
tutorials series ships:

- **T1** — single ITER-like run with the
  `eqdata.ITER01` fixture
- **T3** — a `PT[1] × PN[1]` parameter sweep
  visualised as a heatmap

The remaining four scenarios (T2 JET-like, T4 `tr2`
equivalence at 1e-10, T5 `tot`-coupled run, T6
numerical-blow-up debugging) are reserved for D2.
```

## T1 — ITER-like single-run scenario

**Goal.** Walk through one 100-step run using the
shipped `eqdata.ITER01` equilibrium fixture (TASK/EQ
binary format, loaded under `MODELG=3` via the `EQRTSK`
reader), then read the resulting `TrState`.

**Set-up.** The fixture lives at
`python/eqlib/tests/fixtures/eqdata.ITER01`. The C ABI's
`KNAMEQ` parameter has an 80-byte limit (see
{doc}`input-files`), so absolute paths usually do not
fit; the standard pattern is to `chdir` into the
directory holding the file and pass a bare filename:

```python
import os
os.chdir("python/eqlib/tests/fixtures")
```

**The script.** All non-geometry knobs come from the
shipped fixture
`python/trlib/tests/fixtures/tr_iter01_params.py`,
which sets `MODELG=3`, `NSMAX=4`,
`KNAMEQ="eqdata.ITER01"`, `RIPS`/`RIPE`, the plasma
profile arrays `PN`/`PNS`/`PT`/`PTS`, and heating-source
scalars. Geometry (`RR`, `RA`, `RKAP`, `RDLT`, `BB`) is
loaded from the TASK/EQ binary file at the start of the
first `tr.run(...)` call (the chain is
`tr_run → tr_prep → tr_set_metric → eq_load + tr_bpsd_get`),
so the script does **not** set geometry explicitly.

```python
import os
from trlib import Trlib
from trlib.tests.fixtures import tr_iter01_params

os.chdir("python/eqlib/tests/fixtures")  # KNAMEQ is 80 bytes

with Trlib() as tr:
    tr_iter01_params.apply(tr)
    tr.validate()
    tr.run(ntmax=100)
    state = tr.get_state()

print(f"WPT   = {state.scalars['WPT']}")
print(f"BETAN = {state.scalars['BETAN']}")
print(f"Q0    = {state.scalars['Q0']}")
print(f"TAUE1 = {state.scalars['TAUE1']}")
```

**Expected output.** Concrete values depend on the build
configuration and may drift; run the script locally to
populate them:

```text
WPT   = ...
BETAN = ...
Q0    = ...
TAUE1 = ...
```

**Extensions.**

- Vary `PT[1]` (axis ion temperature) over
  `{0.7, 1.0, 1.5}` keV as a single-axis warm-up before
  T3 (which extends this to a 2-axis `PT[1] × PN[1]`
  sweep). `RIPS` looks like an obvious alternative
  single-axis knob, but the BPSD broker silently
  overwrites it — see T3's gotcha section below.
- Compare against a `MODELG=2` analytic equilibrium
  (no eqdata file needed). `MODELG=2` is the only mode
  in which user-set geometry knobs survive into the
  transport loop.

## T3 — `PT[1] × PN[1]` parameter sweep with heatmap

**Goal.** Run a 3×3 grid over axis ion temperature ×
axis ion density, then plot the resulting `WPT` field as
a heatmap. The pattern follows {doc}`applications` §2
(the `sweep()` wrapper) but is inlined here because the
array-element subscript syntax (`PT[1]`, `PN[1]`) does
not pass through `set_params(**kwargs)`.

**Why these axes — explicit gotcha.** Two intuitive
sweep axes a reader might try first both fail silently
under the ITER01 fixture's `MODELG=3`:

- **`RR × BB`** (geometry sweep). The BPSD broker pull
  overwrites `RR`/`RA`/`BB`/`RIP`/`RKAP`/`RDLT` from the
  loaded equilibrium device on the first `tr.run(...)`
  call, clobbering any user `set_param("RR", ...)`.
- **`RIPS × RIPE`** (plasma-current ramp sweep). The
  same BPSD pull recalibrates `RIPS`/`RIPE` from the
  metric-derived current; user overrides are
  overwritten.

`PT[1]` and `PN[1]` survive: `tr_prof` reads `PN`/`PT`
to build the radial profile arrays `RN`/`RT`; the BPSD
plasma pull writes only `RN`/`RT` (not `PN`/`PT`); and
`tr_set_metric` does not touch the profile parameter
arrays. `WPT` is the total stored plasma energy:
`WPT = Σ_s ∫(3/2) n_s T_s dV  +  WTAILT` — the bulk
sum runs over all species (electrons + ions) and
`WTAILT` is the fast-particle tail energy. In this
fixture `MDLUF=0`, so `WTAILT = 0` and the heatmap
reflects pure bulk stored energy with a clean physical
interpretation.

**Array-element subscript syntax.** `tr.set_param("PT[1]", 1.0)`
is the canonical form for setting array element 1 of
`PT`. The `[idx]` part is parsed by the registry helper
`parse_array_subscript` and routed to the right Fortran
`CASE` block. The same applies to `PN`, `PNS`, `PTS`,
and the other registered array parameters.

```python
import os
from trlib import Trlib
from trlib.tests.fixtures import tr_iter01_params

# Same cwd requirement as T1: KNAMEQ is bare "eqdata.ITER01"
# inside the fixture (80-byte limit), so we must run from the
# directory that holds the binary file.
os.chdir("python/eqlib/tests/fixtures")

PT1_VALUES = [0.7, 1.0, 1.5]   # keV — axis ion temperature
PN1_VALUES = [0.5, 0.7, 1.0]   # 10^20 m^-3 — axis ion density

# 3x3 grid: outer index runs PT[1], inner runs PN[1].
results: list[dict] = []
for pt1 in PT1_VALUES:
    for pn1 in PN1_VALUES:
        with Trlib() as tr:
            tr_iter01_params.apply(tr)
            tr.set_param("PT[1]", pt1)
            tr.set_param("PN[1]", pn1)
            tr.run(ntmax=20)
            state = tr.get_state()
        results.append({
            "PT1": pt1,
            "PN1": pn1,
            "WPT": state.scalars["WPT"],
        })
```

**Plot.** matplotlib is an optional dependency
(`pip install matplotlib`). The script gracefully
degrades to a printed table if matplotlib is
unavailable:

```python
import numpy as np

wpt_grid = np.array([r["WPT"] for r in results]).reshape(
    len(PT1_VALUES), len(PN1_VALUES)
)

try:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    im = ax.imshow(wpt_grid, origin="lower", aspect="auto")
    ax.set_xticks(range(len(PN1_VALUES)))
    ax.set_xticklabels([f"{v:.2f}" for v in PN1_VALUES])
    ax.set_yticks(range(len(PT1_VALUES)))
    ax.set_yticklabels([f"{v:.2f}" for v in PT1_VALUES])
    ax.set_xlabel("PN[1] (10^20 m^-3)")
    ax.set_ylabel("PT[1] (keV)")
    fig.colorbar(im, label="WPT (MJ)")
    fig.savefig("tr_pt1_pn1_sweep.png")
    print("Saved tr_pt1_pn1_sweep.png")
except ImportError:
    print("matplotlib not available; printing table instead.")
    print(f"WPT shape: {wpt_grid.shape}")
    header = "  ".join(f"PN[1]={v:5.2f}" for v in PN1_VALUES)
    print(f"            {header}")
    for i, pt1 in enumerate(PT1_VALUES):
        row = "  ".join(f"{v:9.3f}" for v in wpt_grid[i])
        print(f"PT[1]={pt1:5.2f}  {row}")
```

**Expected output.** Concrete `WPT` values depend on the
build configuration; run locally to populate:

```text
WPT shape: (3, 3); values placeholder — run locally to populate
```

**Extensions.**

- Pipe results into a `pandas.DataFrame` for richer
  tabular post-processing.
- Parallelise with `multiprocessing.Pool` (per the
  singleton constraint in {doc}`faq` Q4, parallelisation
  works because each process gets its own independent
  `Trlib` instance).
- For shape-optimisation studies (`RKAP × RDLT` or
  `RR × BB`), switch to `MODELG=2` (analytic
  equilibrium) so geometry knobs survive — under
  `MODELG=3` the BPSD pull would clobber them. NBI
  total power is now driven via `set_param("PNBTOT",
  <MW>)` (registered as of this PR).

## What's next

- **T2 (JET-like)** is deferred — no `eqdata.JET`
  fixture ships with the repo. D2 will revisit using
  either an analytic-equilibrium JET-shape setup
  (`MODELG=2`) or a new fixture.
- **T4** (Python wrapper ↔ `tr2` equivalence at 1e-10),
  **T5** (`tot`-coupled run), and **T6** (numerical
  blow-up debugging) are reserved for D2.
- For an executable end-to-end form of T1, see the
  `tr-quickstart.ipynb` notebook in the chapter's
  shared notebooks.
