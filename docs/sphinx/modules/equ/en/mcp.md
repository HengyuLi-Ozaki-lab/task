# MCP server

`python/mcp-servers/equ_mcp` is a stdio MCP server (FastMCP, `task-equ`) over
`equlib`.

```bash
PYTHONPATH=python:python/mcp-servers python -m equ_mcp.server
```

Start it in the directory that holds the namelist and the coil file: `read_parm`,
`KNAMCOIL` and `write_geqdsk` take paths relative to it.

| Tool | What it does |
|---|---|
| `init` | a fresh library at EQU's defaults |
| `read_parm(path)` | read an `&EQU` namelist file |
| `set_param`, `set_param_str`, `set_params` | parameters; in `set_params` a list fills an array from its lower bound, a dict `{index: value}` sets elements |
| `validate` | every check of the inputs |
| `run(mode=1)` | mode 1 the program's `R`, mode 0 its first step |
| `get_state`, `get_psi_rz` | the results |
| `write_geqdsk(path, overwrite=false)` | the program's G-EQDSK file |
| `describe_parameters`, `describe_state_schema` | names, types, groups, defaults; the state's schema |
| `run_and_get_state(params, mode, parm_file)` | all of it in one call |

The solver prints its progress on unit 6; the server moves fd 1 to stderr before
the transport starts, so it goes to the client's log.
