# MCP サーバ (`wrx_mcp`)

`wrx_mcp` は TASK/WRX を **Claude Desktop / Claude Code / Cursor などの LLM
クライアント** から直接操作できるようにする, **Model Context Protocol
(MCP)** 対応のサーバです.

```{admonition} このページの位置付け
:class: note

入門者向けの完全ガイドは `python/mcp-servers/wrx_mcp/README.md` にあります.
本ページはその要約です. MCP プロトコル全般の解説は `tr` モジュールの
MCP サーバページ (`docs/sphinx/modules/tr/ja/mcp.md`) を参照.
```

## 前提条件

1. **Python 3.10 以上**
2. **`libwrxapi.so` がビルド済み** (`make -C wrx libwrxapi.so`)
3. **`mcp` パッケージ**

## インストール

```bash
cd python/mcp-servers/wrx_mcp
pip install -e .
```

## 動作確認

```bash
python -m wrx_mcp.server --help
python -m wrx_mcp.server --print-tools
wrx-mcp doctor
```

## LLM クライアントへの登録

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

または `wrx-mcp install --client claude-code --scope project`.

## 提供ツール一覧

`wrx_mcp` は **9 個** のツールを公開します (`wr_mcp` と同じ構成).

| ツール | 目的 | 主な引数 |
|---|---|---|
| `init` | ライブラリ初期化 | なし |
| `set_param` | パラメータ設定 | `name`, `value` |
| `set_params` | まとめて設定 | `params` |
| `run` | beam tracing 実行 | `nray_request` |
| `get_state` | 状態取得 | なし |
| `finalize` | リソース解放 | なし |
| `describe_parameters` | パラメータ一覧 (70 個) | なし |
| `describe_state_schema` | 戻り値 schema | なし |
| `run_and_get_state` | 一括実行 | `params`, `nray_request` |

## 使い方の例

### 例 1: 集束 ECRH ビームの吸収

> WRX を初期化して, RR=6.2, BB=5.3, RFIN[1]=170e9, RPIN[1]=8.5, ZPIN[1]=1.5,
> RCURVAIN[1]=200, RBRADAIN[1]=0.02 で beam tracing し, pwr_tot を教えて.

LLM は `run_and_get_state` を呼び `scalars.pwr_tot` を返します.

### 例 2: ビーム幅のスキャン

> RBRADAIN を 0.01, 0.02, 0.05 で走らせて, それぞれの pwr_tot を比較して.

LLM は 3 回 `run_and_get_state` を呼んで結果を表組みします.

### 例 3: 粒子種別吸収

> NSMAX=2 (電子 + 重水素) で ECRH 170 GHz を入射して, pwr_nsa で
> 電子とイオンそれぞれの吸収を比較して.

LLM は `run_and_get_state` 後に `state.pwr_nsa` を取得. ECRH なら電子が
ほぼ 100% 吸収するはずです.

## アーキテクチャ的な注意点

### `wr` との使い分け (LLM の判断材料)

- 「ビームが集束している」「focal length がある」 → `wrx_mcp`
- 「レイトレースの概算」「ピーク位置さえ分かれば良い」 → `wr_mcp`

### シングルトン制約

`wrx` は `pl_*` 状態を他モジュールと共有. 同一プロセスで `wr_mcp` と
同時起動不可.

### `run` 引数名

Python API は `run(nray_request=N)` ですが内部 C ABI は `nstpmax_arg`
(最大ステップ数上書き) 扱いの場合あり. LLM が挙動を正確に知りたいときは
`describe_state_schema` + 実行結果で確認.

## トラブルシューティング (要約)

| 症状 | 対処 |
|---|---|
| `libwrxapi.so not found` | `make -C wrx libwrxapi.so` |
| ビームが発散しすぎる | `RCURVAIN[i]` を集束方向 (正の大値) に変更 |
| 結果が `wr` と違う | beam tracing なので違うのが正常 ({doc}`faq` Q5) |
| 結果が `wrx2` と違う | `wrxlib_equivalence` で確認 |

## 参考資料

- **MCP 仕様**: <https://modelcontextprotocol.io/>
- **完全ガイド**: `python/mcp-servers/wrx_mcp/README.md`
- **`wrxlib` README**: `python/wrxlib/README.md`
