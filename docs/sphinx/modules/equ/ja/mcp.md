# MCP サーバ

`python/mcp-servers/equ_mcp` は `equlib` の上の stdio MCP サーバ (FastMCP, `task-equ`).

```bash
PYTHONPATH=python:python/mcp-servers python -m equ_mcp.server
```

ネームリストとコイルファイルのあるディレクトリで起動すること. `read_parm`, `KNAMCOIL`,
`write_geqdsk` のパスはそこからの相対パス.

| ツール | すること |
|---|---|
| `init` | EQU の既定値で新しく始める |
| `read_parm(path)` | `&EQU` ネームリストファイルを読む |
| `set_param`, `set_param_str`, `set_params` | パラメータ. `set_params` ではリストは配列の下限から埋め, 辞書 `{index: value}` は要素を設定する |
| `validate` | 入力のすべての検査 |
| `run(mode=1)` | mode 1 はプログラムの `R`, mode 0 はその最初の段階 |
| `get_state`, `get_psi_rz` | 結果 |
| `write_geqdsk(path, overwrite=false)` | プログラムの G-EQDSK ファイル |
| `describe_parameters`, `describe_state_schema` | 名前・型・グループ・既定値, 状態のスキーマ |
| `run_and_get_state(params, mode, parm_file)` | 以上を一度に |

ソルバは進行状況を unit 6 に書く. サーバは通信の開始前に fd 1 を stderr に向けるので, それは
クライアントのログに出る.
