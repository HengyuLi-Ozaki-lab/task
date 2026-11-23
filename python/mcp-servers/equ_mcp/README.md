# equ_mcp: an MCP server for TASK/EQU

A stdio MCP server (FastMCP, name `task-equ`) over `python/equlib`, the wrapper of
`equ/libequapi.so`. Pattern of `eq_mcp`. Design:
`docs/superpowers/specs/2026-11-22-equ-library-design.md`, section 12.

## Run

```bash
make -C equ libequapi.so
PYTHONPATH=python:python/mcp-servers python -m equ_mcp.server
```

From an MCP client (Claude Desktop, Claude Code), in the directory that holds the
namelist and coil files:

```json
{"mcpServers": {"task-equ": {
  "command": "python", "args": ["-m", "equ_mcp.server"],
  "cwd": "/path/to/the/case",
  "env": {"PYTHONPATH": "/path/to/task/python:/path/to/task/python/mcp-servers",
          "EQULIB_PATH": "/path/to/task/equ/libequapi.so"}}}}
```

File names (`read_parm`, `KNAMCOIL`, `write_geqdsk`) are relative to that directory.

## Tools

| Tool | What it does |
|---|---|
| `init` | a fresh library at EQU's defaults |
| `read_parm(path)` | read an `&EQU` namelist file |
| `set_param(name, value)`, `set_param_str(name, value)` | one parameter |
| `set_params(params)` | several; a list fills an array from its lower bound, a dict `{index: value}` sets elements |
| `validate` | every check of the inputs; `[]` when the run may start |
| `run(mode=1)` | mode 1 the program's `R`, mode 0 its first step |
| `get_state`, `get_psi_rz` | the results |
| `write_geqdsk(path, overwrite=false)` | the program's G-EQDSK (pressure in MPa, as EQU writes it) |
| `finalize` | close |
| `describe_parameters`, `describe_state_schema` | names, types, defaults; the state's schema |
| `run_and_get_state(params, mode, parm_file)` | `init`, `read_parm`, `set_params`, `run`, `get_state` |

## Logs

The solver prints its progress on unit 6. `main()` moves fd 1 to stderr before the
transport starts (`python/_fd_isolation.py`), so the progress goes to the client's
log and never into the JSON-RPC stream.
