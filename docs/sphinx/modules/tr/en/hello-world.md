# Minimal hello-world (5 lines)

```python
from trlib import Trlib            # (1) import
with Trlib() as tr:                # (2) initialize (= tr_init automatically)
    tr.set_params(RR=3.0, BB=3.0)  # (3) major radius 3 m, field 3 T
    tr.run(ntmax=10)               # (4) advance 10 time steps
    state = tr.get_state()         # (5) read state (type is TrState)
print(state.scalars["T"])          # final time (seconds)
```

## Line-by-line

- **(1) `from trlib import Trlib`** — imports the class `Trlib` from
  the `trlib` package. `Trlib` is a handle to the shared library.
- **(2) `with Trlib() as tr:`** — Python's context-manager feature.
  `__enter__` (= `tr_init`) runs on entry and `__exit__`
  (= `tr_finalize`) runs on exit, so cleanup is automatic and
  cannot be forgotten.
- **(3) `tr.set_params(RR=3.0, BB=3.0)`** — bulk-setter for scalar
  parameters. Keyword names match the Fortran `/TR/` namelist
  (`RR` = major radius, `BB` = toroidal field).
- **(4) `tr.run(ntmax=10)`** — advance the time evolution by 10 steps.
  The step size is `DT` (default 0.01 s).
- **(5) `state = tr.get_state()`** — copy the current state into a
  `TrState` dataclass. `state.scalars["T"]` gives the current time;
  `state.RT[i][j]` gives the temperature profile.

## Expected output

```bash
$ PYTHONPATH=python python3 examples/quickstart.py
NT=50  NRMAX=50  NSMAX=2
T    = 0.5
WPT  = 8.3e+05
Q0   = 0.96
BETAA= 0.42
```

Full executable notebook: {doc}`quickstart`.
