# Library application examples (Python wrappers)

`Eq` is usable on its own, but wrapping it in a thin Python layer makes
it considerably more practical. This page shows three typical patterns.

```{admonition} Where this page fits
:class: note

What you see here are **application patterns for using `eqlib` from
Python**. For scenarios that drive `eq` from an LLM client in natural
language, see the "Usage scenarios" section of {doc}`mcp`.
```

---

## 1. Auto mode-selection wrapper

`eq.run()` has two paths (see {doc}`hello-world`):

- `mode=0`: analytic Grad-Shafranov solve (`MODELG=2`, no EQDSK needed)
- `mode=1`: load an EQDSK file (`MODELG ∈ {3, 5, 8}` + `KNAMEQ`)

A wrapper that switches automatically depending on whether the user
passed an EQDSK file path.

```python
from pathlib import Path
from eqlib import Eq


def smart_run(eq: Eq, *, eqdsk_file: str | None = None) -> None:
    """Switch between mode=0 and mode=1 based on whether an EQDSK file is given.

    If eqdsk_file is provided, load the file (mode=1);
    otherwise, run the analytic solve (mode=0).
    """
    if eqdsk_file is None:
        # Analytic G-S solve: just confirm MODELG=2 (the default)
        eq.set_param("MODELG", 2)
        eq.run(mode=0)
    else:
        # EQDSK load: check file exists + MODELG=3 + KNAMEQ
        if not Path(eqdsk_file).exists():
            raise FileNotFoundError(f"EQDSK file not found: {eqdsk_file}")
        eq.set_param("MODELG", 3)
        eq.set_param_str("KNAMEQ", eqdsk_file)
        eq.run(mode=1)


# Usage example (analytic solve)
with Eq() as eq:
    eq.set_params(RR=3.0, RA=1.0, BB=3.0, RIP=1.5)
    smart_run(eq)
    s = eq.get_state().scalars
    print(f"raxis={s['raxis']:.4f}  qaxis={s['qaxis']:.4f}")
```

Expected output:

```text
raxis=3.0709  qaxis=0.9918
```

If you want to pass an EQDSK file:

```python
with Eq() as eq:
    eq.set_params(RR=6.2, RA=2.0, BB=5.3, RIP=15.0)
    smart_run(eq, eqdsk_file="eqdata.ITER01")
    ...
```

### Possible extensions

- Add reverse-direction logic that infers `MODELG` from `KNAMEQ`
  (e.g. `.eqdsk` extension -> 3, `.vmec` -> 7).
- When `eqdsk_file=None`, add a lightweight preflight that checks
  whether the given device parameters can be solved stably by the
  analytic path (e.g. that kappa and delta are not extreme).

---

## 2. Parameter-sweep wrapper

Performs a grid scan such as `RR x BB` and aggregates results into a
list of dicts. Because each point uses the analytic G-S solve
(`mode=0`), it runs quickly (~50 ms per point).

```python
import itertools
from typing import List, Dict
from eqlib import Eq


def sweep(
    *,
    rr_values: List[float],
    bb_values: List[float],
    fixed_params: Dict | None = None,
) -> List[Dict]:
    """Grid scan over RR x BB. Each point runs eq in an independent session.

    Returns
    -------
    A list of dicts, each containing {RR, BB, raxis, qaxis, qsurf, betap, error}.
    """
    fixed = fixed_params or {"RA": 1.0, "RIP": 1.5}
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with Eq() as eq:
                eq.set_params(RR=rr, BB=bb, **fixed)
                eq.run(mode=0)
                state = eq.get_state()
            row.update(
                raxis=state.scalars["raxis"],
                qaxis=state.scalars["qaxis"],
                qsurf=state.scalars["qsurf"],
                betap=state.scalars["betap"],
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
)
for r in results:
    if r.get("error"):
        print(f"  RR={r['RR']}, BB={r['BB']} -> ERROR")
    else:
        print(f"  RR={r['RR']}, BB={r['BB']}: "
              f"qaxis={r['qaxis']:.3f}, qsurf={r['qsurf']:.3f}")
```

Expected output (excerpt):

```text
  RR=3.0, BB=3.0: qaxis=0.992, qsurf=3.767
  RR=3.0, BB=7.0: qaxis=2.269, qsurf=8.789
  RR=5.0, BB=5.0: qaxis=1.003, qsurf=3.437
  RR=6.5, BB=3.0: qaxis=0.473, qsurf=1.555
  RR=6.5, BB=7.0: qaxis=1.082, qsurf=3.628
```

The combination of `qaxis` and `qsurf` can be used, for example, to
filter out the region where `qaxis > 1` (no classical sawtooth
instability).

### Possible extensions

- Pipe results into a `pandas.DataFrame` and render a heatmap.
- Sweep `RKAP x RDLT` (elongation x triangularity) for shape
  optimisation.
- Parallelise across multiple processes with `multiprocessing.Pool`
  (per the singleton constraint in {doc}`faq` Q6, parallelisation
  works because **each process has its own independent `Eq`
  instance**).

---

## 3. validate-driven setup

A function that watches the output of `validate()` to automatically
detect and auto-fill common mistakes. Use it to "sanitise" user input
before calling `run()`.

```python
from eqlib import Eq, EqDiagCode


# Device presets.
# eq solves the time-averaged equilibrium, so RIP is given as a single value.
# (For tr the current is time-dependent and is given as the RIPS / RIPE pair.)
DEVICE_PRESETS = {
    "ITER":  dict(RR=6.2,  RA=2.0,  BB=5.3, RIP=15.0, RKAP=1.7, RDLT=0.5),
    "JET":   dict(RR=2.96, RA=1.0,  BB=3.4, RIP=4.0,  RKAP=1.6, RDLT=0.3),
    "DIIID": dict(RR=1.67, RA=0.67, BB=2.1, RIP=2.0,  RKAP=1.8, RDLT=0.4),
}


def auto_setup(
    device: str = "ITER",
    extra_params: Dict | None = None,
    eq_file: str | None = None,
) -> Eq:
    """Initialise eq from a device preset and self-check via validate.

    Returns
    -------
    An Eq instance that has already been init + set_params + validated
    (the caller is responsible for closing it via `with` or try/finally).
    """
    eq = Eq()
    try:
        eq.__enter__()
        # 1. Apply the preset
        params = DEVICE_PRESETS[device].copy()
        # RB (wall radius) must be larger than RA. If left at the default
        # RB=1.2, raising RA will make EQMAGS PAUSE.
        params.setdefault("RB", params["RA"] * 1.2)
        params.update(extra_params or {})
        eq.set_params(**params)

        # 2. If routed via EQDSK, set KNAMEQ as required.
        #    If eq_file is None, set KNAMEQ explicitly to the empty string
        #    so that validate's FILE_MISSING check picks it up.
        if params.get("MODELG") in (3, 5, 8):
            eq.set_param_str("KNAMEQ", eq_file or "")

        # 3. Check via validate
        diags = eq.validate()
        if diags:
            print(f"Detected issues ({len(diags)} item(s)):")
            for d in diags:
                code = EqDiagCode(d.code).name
                print(f"  [{code}] {d.param}: {d.message}")
            blocking = [d for d in diags
                        if d.code in (EqDiagCode.FILE_MISSING,
                                      EqDiagCode.MISSING_REQUIRED)]
            if blocking:
                raise RuntimeError(
                    f"{len(blocking)} blocking issue(s) remain to be fixed"
                )
        return eq
    except Exception:
        eq.__exit__(None, None, None)
        raise


# Usage example
with auto_setup("ITER") as eq:
    eq.run(mode=0)
    s = eq.get_state().scalars
    print(f"raxis={s['raxis']:.3f}  qaxis={s['qaxis']:.3f}  qsurf={s['qsurf']:.3f}")
```

Expected output (ITER preset):

```text
raxis=6.249  qaxis=0.596  qsurf=3.565
```

When `MODELG=3` is specified but `eq_file=None`:

```text
Detected issues (1 item(s)):
  [FILE_MISSING] KNAMEQ: MODELG=3/5/8 requires non-blank KNAMEQ (eqdata file)
RuntimeError: 1 blocking issue(s) remain to be fixed
```

When a value exceeds the compile-time limit, e.g. `extra_params={"NRMAX": 9999}`:

```text
Detected issues (1 item(s)):
  [OUT_OF_RANGE] NRMAX: value 9999 exceeds compile-time maximum 1001
```

(`OUT_OF_RANGE` is not blocking, so it is treated as a warning only.
If you want to block on it, add it to the `blocking` predicate.)

### Possible extensions

- Read the presets from an external file such as `iter_baseline.toml`.
- Auto-clamp on `OUT_OF_RANGE` (e.g. round `NRMAX=9999` down to
  `NRMAX=1001`).
- When called from an LLM, pass the `validate` output straight to the
  LLM and you will get a corrective suggestion back (see "Usage
  scenarios" in {doc}`mcp`).

---

## Combination patterns

The three patterns can be used individually or in combination:

| Combination | Effect |
|---|---|
| **mode auto-select + auto_setup** | `auto_setup` applies the device preset; `smart_run` then auto-switches mode |
| **sweep + auto_setup** | Sweep `RR x BB` or `RKAP x RDLT` on top of a preset baseline |
| **All three** | Analytic shape scan starting from a device preset. The standard pattern for design studies |

The same patterns apply to the other modules (`tr`, `ti`, `fp`, `wr`,
`wrx`, `tot`); just substitute the relevant physical quantities and
error types (`TrlibRunError`, `WrlibRunError`, etc.).
