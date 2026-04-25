# Prerequisites and Build

## Build the library

```bash
cd /path/to/task                     # root of the TASK repository
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic
make -C wr   libwrapi.so
```

If `wr/libwrapi.so` is produced at the end, the build was successful.

## Verify the exported functions

`wr` exposes a **5-function** ABI (the same standard pattern as `tr`).

```bash
$ nm -D wr/libwrapi.so | grep ' T wr_'
... T wr_finalize
... T wr_get_state
... T wr_init
... T wr_run
... T wr_set_param
```

## Make it visible to Python

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

Then `import wrlib` will succeed.
