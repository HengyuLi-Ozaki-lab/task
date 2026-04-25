# Prerequisites and Build

## Building the library

```bash
cd /path/to/task                     # TASK repository root
make -C lib  libs_pic                # PIC versions of lower-level libraries
make -C pl   libs_pic                # plasma common module
make -C eq   libs_pic                # equilibrium module
make -C mtxp libs_pic                # sparse-matrix solver
make -C bpsd libs_pic                # BPSD data bridge
make -C tr   libtrapi.so             # the tr-module shared library itself
```

If `tr/libtrapi.so` exists at the end, the build succeeded.

```bash
$ ls -lh tr/libtrapi.so
-rwxr-xr-x 1 user user 8.2M Apr 23 14:00 tr/libtrapi.so
```

The exact file size depends on the environment, but is typically
5–10 MB.

## Verifying the exported functions

```bash
$ nm -D tr/libtrapi.so | grep ' T tr_'
000000000005a1b0 T tr_finalize
000000000005a090 T tr_get_state
0000000000059e10 T tr_init
0000000000059f80 T tr_run
0000000000059d30 T tr_set_param
0000000000059ca0 T tr_set_param_str
00000000000?????? T tr_validate            # PR #172 and later
```

A `T` in the second column marks an exported function.

## Making it visible to Python

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

After that, `import trlib` works.
