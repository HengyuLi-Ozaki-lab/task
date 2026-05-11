# Prerequisites and Build

## Build the library

```bash
cd /path/to/task                     # root of the TASK repository
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic
make -C wrx  libwrxapi.so
```

The build is successful once `wrx/libwrxapi.so` exists.

## Confirm the exported functions

`wrx` exposes a **5-function** ABI.

```bash
$ nm -D wrx/libwrxapi.so | grep ' T wrx_'
... T wrx_finalize
... T wrx_get_state
... T wrx_init
... T wrx_run
... T wrx_set_param
```

## Make it visible from Python

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

After this, `import wrxlib` will resolve.

## Differences from `wr`

`wrx` is the **eXtended** version of `wr` (geometric optics) and adds
**beam tracing**:

- **`wr`**: rays have no width (pencil beams); beam spread is approximated
  with many rays.
- **`wrx`**: each ray carries curvature and width information; the beam
  shape is developed analytically.

`wrx` is more accurate but more expensive than `wr`.

The codebase shares some sources with `wr`, but the two are built into
**separate `.so` files**.
