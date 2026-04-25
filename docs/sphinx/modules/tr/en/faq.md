# FAQ / Common Pitfalls

## Q1. I get `FileNotFoundError: libtrapi.so not found ...`

Either it has not been built yet, or it is in a different location.
Try the following:

1. Check that `ls tr/libtrapi.so` exists.
2. If not, run `make -C tr libtrapi.so`.
3. If you really want to keep it elsewhere,
   `export TRLIB_PATH=/path/to/libtrapi.so`.

## Q2. I get `TrlibParamError: ierr=1`

You either passed a parameter name that does not exist, or an array
index out of range. Check the `SELECT CASE` block in
`tr/tr_param_registry.f90` to see what is registered. Adding a new
parameter is just a one-line change on the Fortran side (followed by
a rebuild).

## Q3. I wrote `set_params(PN__1=1.0)` by accident

Keys containing `__` (two underscores) are explicitly rejected as
likely typos for the array syntax. The correct form is
`tr.set_param("PN[1]", 1.0)`.

## Q4. Can I create two `Trlib()` instances in the same process?

**No, you cannot.** Since #171, `Trlib` enforces the singleton
boundary explicitly via a weakref. The second `Trlib()` raises
`TrlibStateError`. If you need multi-instance behaviour, use
`multiprocessing` to isolate by process.

## Q5. The result does not match `tr2` (the CLI version)

Run the regression test `trlib_equivalence` and check the diff
against the Phase 0 baseline.

```bash
bash test_run/run_tests.sh trlib_equivalence
```

The tolerance is `1e-10`. If you drift beyond that, you have most
likely missed a registered parameter.

## Q6. Do I need NumPy?

**No.** `TrState` exposes plain Python `list`s. If you want NumPy,
convert with `import numpy as np; np.array(state.RT)`.
