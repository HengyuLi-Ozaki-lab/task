# Library application examples (Python wrapper)

`Tot` is the orchestrator that brings up the other 5 modules
(eq / tr / ti / fp / wr) inside a single process. This page shows three
typical patterns.

```{admonition} L-6 stage limitation
:class: warning

The current `Tot` (Phase L-6) **only actually time-evolves the transport
part (TR)**. `eq` / `ti` / `fp` / `wr` are initialized inside the same
process, but `tot.run()` does not invoke their calculations. In other
words:

- Namespaced settings such as `tot.set_param("eq:RR", 6.5)` are
  **distributed to all 5 modules**.
- `tot.run(ntmax)` **only calls `tr_api_run(ntmax)`**.
- `tot.get_state()` returns the **aggregated TR state**
  (`state.tr_present == 1`, `state.ti_present == 0`, ...).

Cross-module coupling such as `wr` -> `tr` (wave heating deposition) and
`fp` -> `tr` (current drive) is planned for the upcoming Phase L-7.
```

```{admonition} About this page
:class: note

What is shown here are **application patterns for using `totlib` from
Python**. For scenarios where an LLM client drives it via natural
language, see the "Usage scenarios" section of {doc}`mcp`.
```

---

## 1. Integrated init + namespaced setup

`Tot()` brings up four sub-modules (tr / ti / fp / wr) in a single
`__init__` call. Parameters for each module are distinguished by a
`<ns>:<name>`-style prefix:

```python
from totlib import Tot


with Tot() as tot:
    # Set the eq geometry (distributed to each sub-module)
    tot.set_param("eq:RR", 6.2)
    tot.set_param("eq:RA", 2.0)
    tot.set_param("eq:BB", 5.3)
    tot.set_param("eq:RIP", 15.0)

    # tr transport configuration
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    tot.set_param("tr:BB", 5.3)
    tot.set_param("tr:NSMAX", 2)
    tot.set_param("tr:DT", 0.01)
    tot.set_param("tr:NTMAX", 100)

    # Advance just one step and check the state
    tot.run(1)
    state = tot.get_state()
    print(f"tr_present={state.tr_present}, T={state.scalars['T']:.3f}s")
```

Expected output:

```text
tr_present=1, T=0.010s
```

Available prefixes:

| Prefix | Module | Notes |
|---|---|---|
| `eq:` | equilibrium | Geometry shared between analytic / EQDSK |
| `tr:` | transport | 1D diffusion equation |
| `ti:` | ion transport | Heavy-ion transport (only when used) |
| `fp:` | Fokker-Planck | Velocity-space distribution |
| `wr:` / `wrx:` | ray tracing | Wave propagation |

Per-namespace definitions can be enumerated via `describe_parameters` on
each module's MCP (see {doc}`mcp`).

### Extension ideas

- Bundle device presets (ITER / JET / DIIID) into a single dict and
  expand them in one shot via `_apply_namespaced(tot, preset)`
- If feeding the same `RR/RA/BB` to eq, tr, and wr feels redundant,
  build a `geometry_from(preset)` helper that expands them

---

## 2. Wrapping the transport advance

At the L-6 stage, `tot.run(ntmax)` advances **only the TR transport
calculation** for ntmax steps. The failure-handling pattern matches
`StableTrRunner` in the tr module's applications page
(`docs/sphinx/modules/tr/en/applications.md`).

```python
from totlib import Tot
from totlib.errors import TotlibCalculationFailedError


def transport_step(tot: Tot, *, ntmax: int = 100) -> dict:
    """Advance transport via tot and return the main scalars."""
    try:
        tot.run(ntmax)
        state = tot.get_state()
        return {
            "tr_present": bool(state.tr_present),
            "T":     state.scalars["T"],
            "WPT":   state.scalars["WPT"],
            "BETAN": state.scalars["BETAN"],
            "TAUE1": state.scalars["TAUE1"],
            "Q0":    state.scalars["Q0"],
        }
    except TotlibCalculationFailedError as e:
        return {"error": repr(e)}


with Tot() as tot:
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    tot.set_param("tr:BB", 5.3)
    tot.set_param("tr:NSMAX", 2)
    tot.set_param("tr:DT", 0.01)
    tot.set_param("tr:NTMAX", 100)
    out = transport_step(tot, ntmax=10)
    for k, v in out.items():
        if isinstance(v, float):
            print(f"  {k} = {v:.4g}")
        else:
            print(f"  {k} = {v}")
```

Expected output:

```text
  tr_present = True
  T = 0.1
  WPT = 10.01
  BETAN = 0.2872
  TAUE1 = 11.42
  Q0 = 2.519
```

### Extension ideas

- Extend the wrapper to return all 13 entries of `state.scalars`
  (`T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, TAUE1, TAUE2, ZEFF0,
  ALI, RQ1`)
- Accumulate `state.scalars` into a list at every ntmax for time-series
  analysis

---

## 3. Future coupling pipeline (planned for L-7)

In L-7, a pipeline that couples `wr` -> `tr` (RF heating deposition),
`fp` -> `tr` (RF current drive), `eq` -> `tr` (per-step equilibrium
update), etc. is envisaged. It is not implemented yet, but sketching
the client-side shape now will make the L-7 transition smoother.

```python
from totlib import Tot

# Note: the following is pseudo-code targeting the L-7 implementation.
# In the current state (L-6), `tot.run()` only advances TR transport.

def integrated_step(tot: Tot, *, ntmax: int = 1) -> dict:
    """Pipeline that intends to advance eq + wr + fp + tr in one cycle."""
    # 1. eq solve (update equilibrium from current plasma current/pressure)
    # tot.run_module("eq", mode=0)            # <- to be added in L-7

    # 2. wr ray-trace (compute RF deposition profile from current n/T)
    # tot.run_module("wr", nray=8)            # <- to be added in L-7

    # 3. fp Fokker-Planck (RF deposition -> current drive)
    # tot.run_module("fp", ntmax=10)          # <- to be added in L-7

    # 4. tr transport (advance one step using the sources above)
    tot.run(ntmax)                              # <- works in L-6 too

    return tot.get_state().scalars


# At present only (4) actually runs:
with Tot() as tot:
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    tot.set_param("tr:BB", 5.3)
    tot.set_param("tr:NSMAX", 2)
    tot.set_param("tr:DT", 0.01)
    tot.set_param("tr:NTMAX", 100)
    sc = integrated_step(tot, ntmax=10)
    print(f"T={sc['T']:.3f}s WPT={sc['WPT']:.3f}MJ BETAN={sc['BETAN']:.4f}")
```

Expected output (L-6 stage, TR only):

```text
T=0.100s WPT=10.007MJ BETAN=0.2872
```

### APIs planned for L-7 (draft)

| Added API | Role |
|---|---|
| `tot.run_module(name, **kwargs)` | Advance a single module only |
| `tot.run_pipeline(steps)` | Run multiple modules in a specified order for one cycle |
| `state.{eq,wr,fp,ti}_*` | Aggregated state for each module |
| `tot.couple(src, dst)` | Declare a source -> sink data flow |

The specification will be finalized when L-7 work begins.

---

## Combination patterns

| Combination | Effect |
|---|---|
| **namespaced setup + transport_step** | TR-based steady-state analysis using a single `Tot` (eq geometry is also initialized at the same time) |
| **transport_step + sweep** | Grid scan such as RR x BB to evaluate TR transport sensitivity |
| **L-7 pipeline placeholder** | Writing this now means the migration when L-7 ships can be done in one pass |

For per-sub-module application patterns, see each module's
`applications.md` (e.g. `docs/sphinx/modules/tr/en/applications.md`,
`docs/sphinx/modules/eq/en/applications.md`, etc.). The same prefixed
parameters can be used to set things up via `Tot` as well.
