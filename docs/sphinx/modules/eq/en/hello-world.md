# Minimal hello-world

`eq` has two minimal forms — **solve the Grad-Shafranov equation (`mode=0`)** or
**load an equilibrium file (`mode=1`)**. Both are shown below.

## A. Solve the Grad-Shafranov equation (`mode=0`)

No file required. Solves the fixed-boundary Grad-Shafranov equation
numerically (`EQCALC` iterates to `EPSEQ`) from the device parameters
and the pressure / current profiles.

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_params(RR=3.0, RA=1.0, BB=3.0, RIP=1.5)  # (1) device parameters
    eq.run(mode=0)                                    # (2) Grad-Shafranov solve + post-process
    st = eq.get_state()                               # (3) fetch the state
print(f"raxis={st.scalars['raxis']:.4f}  qaxis={st.scalars['qaxis']:.4f}")
```

Expected output:

```text
raxis=3.0709  qaxis=0.9918
```

### Line-by-line explanation

- **(1) `set_params`**: Device geometry and operating point — `RR`
  (major radius), `RA` (minor radius), `BB` (toroidal field), `RIP`
  (plasma current). `MODELG=2` (toroidal geometry) is the default and need not
  be set explicitly.
- **(2) `eq.run(mode=0)`**: Runs `EQCALC` (the Grad-Shafranov solve) followed
  by `EQCALQ` (post-processing) in sequence. This corresponds to the
  `R` (Run) and then `F` (Fields) commands of the legacy `eqx2` CLI.
- **(3) `eq.get_state()`**: Copies the result into an `EqState`
  dataclass. Details in {doc}`state`.

## B. Load an equilibrium file (`mode=1`)

The standard pattern when the equilibrium already exists as a file
(here a TASK/EQ file, `MODELG=3`).

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_param("RR", 6.5)                    # (1) major radius [m]
    eq.set_param("BB", 5.3)                    # (2) field [T]
    eq.set_param("RIP", 1.5)                   # (3) current [MA]
    eq.set_param("MODELG", 3)                  # (4) 3: a TASK/EQ file
    eq.set_param_str("KNAMEQ", "eqdata.ITER01")  # (5) filename (dedicated API)
    eq.run()                                   # (6) mode=1 (default) loads the file
    st = eq.get_state()                        # (7) fetch the state
print(f"raxis={st.scalars['raxis']:.4f}  qaxis={st.scalars['qaxis']:.4f}")
```

### Line-by-line explanation

- **(1)–(3)**: Device parameters. A TASK/EQ file holds its own: the load
  reads `RR`, `BB`, `RIP` (and `RA`, `RKAP`, `RDLT`, `RB`) from the file.
- **(4) `MODELG=3`**: Selects the file format: 3 (and 9) a TASK/EQ file,
  5 (and 25) a G-EQDSK file, each named by `KNAMEQ`; 8 a QST/JAEA pair
  (`KNAMEQ`, `KNAMEQ2`); 15 the fixed file `eqdb.dat`. `mode=1` needs one
  of these and fails with the default `MODELG=2`.
- **(5) `set_param_str`**: String parameters require the **dedicated
  API** (see {doc}`parameter-setting`, method C).
- **(6) `eq.run()`**: With no argument it runs `mode=1` (the file load).
  This corresponds to the `L` (Load) command of the legacy `eqx2` CLI.

## Picking the mode (flowchart)

```text
Is the equilibrium in a file?
  |- No  -> mode=0 (MODELG=2, the default): solve it from the profiles
  `- Yes -> mode=1 (MODELG in {3, 5, 8, 9, 25} with KNAMEQ set, or 15)
```

For a fully runnable notebook, see {doc}`quickstart`.

## Differences from `tr`

- **No time evolution**: `eq.run()` does not advance time steps; it
  takes a `mode` (operating-mode) argument. The default is `mode=1`
  (the file load), but for the Grad-Shafranov solve pass `mode=0` explicitly
  (see {doc}`faq` Q2).
- **6th C ABI**: `eq_set_param_str` accepts string parameters. `tr`
  added one recently as well, but EQ has needed it from the very
  beginning to handle equilibrium filenames (`KNAMEQ`).
