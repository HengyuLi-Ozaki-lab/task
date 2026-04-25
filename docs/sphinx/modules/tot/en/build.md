# Prerequisites and Build

## Building the library

```bash
cd /path/to/task                     # root of the TASK repository

# PIC archives for every sub-module
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C tr   libs_pic
make -C ti   libs_pic
make -C fp   libs_pic
make -C wr   libs_pic
make -C wrx  libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic

# tot itself
make -C tot  libtotapi.so
```

`tot` is a final binary that **statically links** all of the other
modules (eq, tr, ti, fp, wr, wrx). **All sub-modules must be built
first.**

## Checking the exported symbols

`tot` has a **6-function** ABI (the same extended set as `eq` and `fp`).

```bash
$ nm -D tot/libtotapi.so | grep ' T tot_'
... T tot_finalize
... T tot_get_state
... T tot_init
... T tot_run
... T tot_set_param
... T tot_set_param_str       # <-- 6th function: for prefixed string parameters
```

## Making the library visible to Python

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

After this, `import totlib` will work.
