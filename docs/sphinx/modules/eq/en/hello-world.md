# Minimal hello-world

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_param("RR", 6.5)                    # (1) major radius [m]
    eq.set_param("BB", 5.3)                    # (2) field [T]
    eq.set_param("RIP", 1.5)                   # (3) current [MA]
    eq.set_param("MODELG", 3)                  # (4) select EQDSK path
    eq.set_param_str("KNAMEQ", "eqdata.ITER")  # (5) filename (dedicated API)
    eq.run()                                   # (6) solve equilibrium with mode=1
    st = eq.get_state()                        # (7) get the state (type EqState)
print(f"raxis={st.scalars['raxis']:.4f}  qaxis={st.scalars['qaxis']:.4f}")
```

## Line-by-line explanation

- **(1)–(3)**: Specify the device geometry and operating point. `RR`
  (major radius), `BB` (toroidal field), and `RIP` (plasma current) are
  required for any EQ calculation.
- **(4) `MODELG=3`**: Select the mode that loads the equilibrium data
  from an EQDSK file. With `MODELG=2` (analytic, the default) `KNAMEQ`
  is not needed.
- **(5) `set_param_str`**: String parameters require the **dedicated
  API**. They cannot be passed through the regular `set_param`
  (see {doc}`parameter-setting`, method C).
- **(6) `eq.run()`**: With no argument it runs `mode=1` (the standard
  flow that reads an EQDSK file and builds the equilibrium). Unlike
  `tr`, it **does not advance time**.
- **(7) `eq.get_state()`**: Copies the result into an `EqState`
  dataclass. Details in {doc}`state`.

## Expected output

```bash
raxis=6.4321  qaxis=0.9876
```

For a fully runnable notebook, see {doc}`quickstart`.

## Differences from `tr`

- **No time evolution**: `eq.run()` does not advance time steps; it
  takes a `mode` argument. `mode=1` is the default (see {doc}`faq`).
- **6th C ABI**: `eq_set_param_str` accepts string parameters. `tr`
  added one recently as well, but EQ has needed it from the very
  beginning to handle EQDSK filenames.
