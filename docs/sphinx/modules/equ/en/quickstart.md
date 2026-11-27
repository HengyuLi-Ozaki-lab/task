# Quick start

## Build

```bash
make -C equ libequapi.so          # from the TASK checkout, bpsd beside it
export PYTHONPATH=$PWD/python
```

## Run an example

The examples are in `equ/example`. A namelist names its coil file in
`KNAMCOIL`, relative to the working directory: `equparm.quest` names `coildata`.

```python
import os, shutil, tempfile
from equlib import Equ

work = tempfile.mkdtemp()
shutil.copy("equ/example/equparm.quest", f"{work}/equparm")
shutil.copy("equ/example/coildata.quest", f"{work}/coildata")
os.chdir(work)

with Equ() as equ:
    equ.read_parm("equparm")          # the &EQU namelist
    assert equ.validate() == []       # every check of the inputs
    equ.run()                         # mode 1: the program's R
    st = equ.get_state()
    print(st.ip, st.q_axis, st.raxis, st.fct_converged)
    equ.write_geqdsk("quest.geqdsk")  # the program's E
```

`python python/equlib/examples/quickstart.py` does the same.

## Change an input

```python
with Equ() as equ:
    equ.read_parm("equparm")
    equ.set_param("TCUR", 0.28)        # MA
    equ.set_param("CVACST[3]", -0.25)  # a coil group's target current
    equ.run()
```

Each run starts from the inputs as set: a `set_param` after a run changes the
input, not the value the solver left in it.

## Errors

| Exception | When |
|---|---|
| `EqulibInvalidParamError` | an unknown name, a value the registry refuses, a check of `validate`, a run before an equilibrium for `get_state` |
| `EqulibCalculationFailedError` | the solve failed (e.g. a contour that finds no starting point); the handle stays usable |
| `EqulibNotImplementedError` | `run(mode)` above 1 |

`equ.last_error()` gives the library's reason; the exceptions carry it.
