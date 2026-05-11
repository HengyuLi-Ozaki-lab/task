# Prerequisites and Build

## Building the library

```bash
cd /path/to/task                     # TASK repository root
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic
make -C fp   libfpapi.so
```

If `fp/libfpapi.so` exists at the end, the build succeeded.

## Verifying the exported functions

`fp` uses the same **6-function** ABI as `eq` (5 functions plus
`fp_set_param_str`).

```bash
$ nm -D fp/libfpapi.so | grep ' T fp_'
... T fp_finalize
... T fp_get_state
... T fp_init
... T fp_run
... T fp_set_param
... T fp_set_param_str       # <-- 6th: string parameter (KNAMEQ)
```

`fp_set_param_str` exists so that the `KNAMEQ` (equilibrium-data file
name) inherited from the `pl_*` modules can be overridden.

## Making it visible to Python

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

After that, `import fplib` works.
