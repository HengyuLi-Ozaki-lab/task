# MCP Server (`wrx_mcp`)

`wrx_mcp` is a **Model Context Protocol (MCP)** server that lets LLM
clients such as **Claude Desktop, Claude Code, and Cursor** drive
TASK/WRX directly.

```{admonition} Scope of this page
:class: note

The full beginner-friendly guide lives at
`python/mcp-servers/wrx_mcp/README.md`. This page is a curated summary.
For a general explanation of the MCP protocol, see also the MCP server
page of the `tr` module
(`docs/sphinx/modules/tr/en/mcp.md`).
```

## Prerequisites

1. **Python 3.10 or newer**
2. **`libwrxapi.so` already built** (`make -C wrx libwrxapi.so`)
3. The **`mcp` package**

## Installation

```bash
cd python/mcp-servers/wrx_mcp
pip install -e .
```

## Sanity check

```bash
python -m wrx_mcp.server --help
python -m wrx_mcp.server --print-tools
wrx-mcp doctor
```

## Registering with an LLM client

### Claude Desktop

```json
{
  "mcpServers": {
    "task-wrx": {
      "command": "python",
      "args": ["-m", "wrx_mcp.server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/task/python",
        "WRXLIB_PATH": "/absolute/path/to/task/wrx/libwrxapi.so"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add task-wrx \
  --env PYTHONPATH=/absolute/path/to/task/python \
  --env WRXLIB_PATH=/absolute/path/to/task/wrx/libwrxapi.so \
  -- python -m wrx_mcp.server
```

Or `wrx-mcp install --client claude-code --scope project`.

## Tools provided

`wrx_mcp` exposes **9** tools (the same lineup as `wr_mcp`).

| Tool | Purpose | Main arguments |
|---|---|---|
| `init` | Initialize the library | none |
| `set_param` | Set a parameter | `name`, `value` |
| `set_params` | Bulk set | `params` |
| `run` | Run beam tracing | `nray_request` |
| `get_state` | Get the state | none |
| `finalize` | Release resources | none |
| `describe_parameters` | List parameters (70 entries) | none |
| `describe_state_schema` | Return-value schema | none |
| `run_and_get_state` | One-shot run | `params`, `nray_request` |

## Usage examples

### Example 1: absorption of a focused ECRH beam

> Initialize WRX, run beam tracing with RR=6.2, BB=5.3, RFIN[1]=170e9,
> RPIN[1]=8.5, ZPIN[1]=1.5, RCURVAIN[1]=200, RBRADAIN[1]=0.02, and tell
> me pwr_tot.

The LLM calls `run_and_get_state` and returns `scalars.pwr_tot`.

### Example 2: scan over the beam width

> Run with RBRADAIN = 0.01, 0.02, 0.05 and compare the resulting pwr_tot.

The LLM calls `run_and_get_state` three times and tabulates the results.

### Example 3: species-resolved absorption

> Inject 170 GHz ECRH into a NSMAX=2 (electron + deuterium) plasma and
> compare the absorption on electrons and ions using pwr_nsa.

The LLM reads `state.pwr_nsa` after `run_and_get_state`. For ECRH the
electrons should absorb essentially 100%.

## Architectural notes

### Choosing between `wr` and `wrx` (cues for the LLM)

- "the beam is focused" / "there is a focal length" → `wrx_mcp`
- "rough ray-tracing estimate" / "peak position is enough" → `wr_mcp`

### Singleton constraint

`wrx` shares the `pl_*` state with other modules. It cannot be running
simultaneously with `wr_mcp` in the same process.

### Argument name of `run`

The Python API takes `run(nray_request=N)`, but inside the C ABI it may
be treated as `nstpmax_arg` (max-step-count override). When the LLM
needs to confirm exact behaviour, it can use `describe_state_schema`
together with the run results.

## Troubleshooting (summary)

| Symptom | Action |
|---|---|
| `libwrxapi.so not found` | `make -C wrx libwrxapi.so` |
| Beam diverges too quickly | Adjust `RCURVAIN[i]` toward focusing (a large positive value) |
| Result differs from `wr` | This is expected because `wrx` does beam tracing ({doc}`faq` Q5) |
| Result differs from `wrx2` | Check via `wrxlib_equivalence` |

## Further reading

- **MCP specification**: <https://modelcontextprotocol.io/>
- **Full guide**: `python/mcp-servers/wrx_mcp/README.md`
- **`wrxlib` README**: `python/wrxlib/README.md`
