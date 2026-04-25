# Prerequisites and Build

## Build the library

```bash
cd /path/to/task                     # TASK repository root
make -C lib   libs_pic
make -C pl    libs_pic
make -C bpsd  libs_pic
make -C mtxp  libs_pic
make -C eq    libeqapi.so
```

If `eq/libeqapi.so` is produced, the build succeeded.

## Check the exported functions

`nm` should show **six** symbols (only `eq` has six; the other modules
have five):

```bash
$ nm -D eq/libeqapi.so | grep ' T eq_'
... T eq_finalize
... T eq_get_state
... T eq_init
... T eq_run
... T eq_set_param
... T eq_set_param_str       # <-- the 6th: EQ-specific (for string parameters)
... T eq_validate            # PR #164 and later
```

The `T` column lists the exported functions. The 6th, `eq_set_param_str`,
is a dedicated API that accepts `CHARACTER(LEN=80)` string parameters
such as `KNAMEQ` (an extension of the 5-function ABI described in
{ref}`Common Architecture <portal:common-architecture>`).

## Make it visible to Python

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

After this, `import eqlib` works.
