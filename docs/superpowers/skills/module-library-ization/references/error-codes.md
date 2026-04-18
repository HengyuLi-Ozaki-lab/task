# Standard C ABI error codes

Every TASK module's C ABI uses the same five error codes. Do **not**
add new codes per-module — extending the enum breaks the
"copy `tr_mcp` and search-replace" pattern that makes adding a new
module's MCP server take an afternoon instead of a week.

| Code | C name (`<MOD>_*`)        | Returned when |
|------|---------------------------|---------------|
| 0    | `OK`                      | success |
| 1    | `ERR_INVALID`             | unknown parameter name, malformed array subscript, value out of range |
| 2    | `ERR_NOT_INIT`            | any function called before `<module>_init` |
| 3    | `ERR_CALC_FAILED`         | numerical kernel returned a non-zero status (allocate, prep, loop) |
| 4    | `ERR_NOT_IMPL`            | L-2 stub return; no real body wired yet (should disappear by end of L-3) |

## Ordering rules (for the Fortran side)

When multiple conditions hold, return the **lowest** matching code,
with one exception: `NOT_INIT` (=2) wins over `INVALID` (=1). Rationale:
without init you can't validate the parameter name anyway, and the
caller's recovery action ("call init first") is the same as for
NOT_INIT alone. The user-facing error message is also more useful.

Example:

```fortran
FUNCTION <MODULE>_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="<MODULE>_set_param")
  ...
  IF (.NOT. g_initialized) THEN
     ierr = <MOD>_ERR_NOT_INIT     ! NOT_INIT precedes INVALID
     RETURN
  END IF
  ! ... convert name from C string ...
  ierr = <MODULE>_param_set(fname(1:n), value)
  IF (ierr /= 0) ierr = <MOD>_ERR_INVALID
END FUNCTION
```

## Python wrapper mapping

```python
def raise_for_rc(rc: int, context: str) -> None:
    if rc == 0:
        return
    if rc == 1: raise <Module>libParamError(f"{context}: invalid parameter")
    if rc == 2: raise <Module>libInitError(f"{context}: <module>_init not called")
    if rc == 3: raise <Module>libRunError(f"{context}: calculation failed")
    if rc == 4: raise <Module>libNotImplementedError(f"{context}: not implemented yet")
    raise <Module>libError(f"{context}: unknown rc={rc}")
```

## MCP server mapping

`<Module>libError` subclasses are caught in `server.py` and re-raised as
`mcp.server.fastmcp.exceptions.ToolError(str(e))`. The LLM sees a
human-readable message and can usually recover (e.g., "you forgot to
call `init` first").
