# Prerequisites and Build

## Build the library

```bash
cd /path/to/task                     # root of the TASK repository
make -C lib  libs_pic                # PIC versions of the lower-level libraries
make -C pl   libs_pic                # plasma common module
make -C eq   libs_pic                # equilibrium module
make -C mtxp libs_pic                # sparse-matrix solver
make -C bpsd libs_pic                # BPSD data bridge
make -C ti   libtiapi.so             # the ti shared library itself
```

Success means the file `ti/libtiapi.so` has been produced.

## Verify the exported functions

`ti` exports the same **5 functions** as `tr` (the standard pattern from
the [Common Architecture](../../../portal/en/common/architecture.md) chapter).

```bash
$ nm -D ti/libtiapi.so | grep ' T ti_'
... T ti_finalize
... T ti_get_state
... T ti_init
... T ti_run
... T ti_set_param
```

The `T` column lists "exported functions".

## Make `tilib` visible to Python

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

After this, `import tilib` works.
