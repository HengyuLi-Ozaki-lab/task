# L-7a Cross-Module Coupling — Design Spec

- 日付: 2026-04-28
- ブランチ: `chore/pre-push-hook-worktree-compat` (ベース `master`)
- 対象モジュール: `python/totlib/`, `python/mcp-servers/tot_mcp/`
- 関連 commit: 52481e9f (handoff)
- スコープ層: L-7a (incremental step toward L-7 cross-module coupling)
- 前提 spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md`

---

## 1. 目的と背景

TASK プラズマライブラリの `tot` orchestrator は現状 L-6 (TR-only). `python/totlib.Tot` および `tot_mcp` は `libtotapi.so` を介して TR の transport solver だけを advance する. 一方, legacy Fortran バイナリ `tot/totmain.f90` は `pl/eq/tr/dp/wr/wm/fp/ti` を全部 init し, COMMON ブロック + BPSD broker (`tr/trloop.f90:65-83`) で暗黙的に結合していた. その結合機構は現 ABI 表面 (Python/MCP) には露出していない.

**L-7 全体目標**: legacy 結合相当を Python/MCP クライアントから駆動可能な明示 API に移植する.

**L-7a スコープ (本 spec)**: Python-side scalar coupling pipeline の API 骨格を確立する. 第一歩として `fp → tr` の driven current (RJT volume integral → PNBCD scalar) 結合を実装する. profile 級 coupling と coordinate 変換 (rho_T ↔ psi) は L-7b 以降に温存.

## 2. ブレインストーミングで確定した設計方針

| 決定項目 | 選択 | 理由要旨 |
|---|---|---|
| Scope | (B) 段階的, 最小ペアから | 物理仕様の固まりきっていない段階で全結合を一気に詰めると stuck する確率高 |
| 実装層 | (β) Python-side | Fortran ABI 拡張ゼロ, 反復速い, lib*api.so への変更不要 |
| データ変換 | (III) Hybrid (scalar-only) | rho↔psi を numpy で再実装すると BPSD と乖離するリスク. profile/coord は L-7b で BPSD ABI に委譲 |
| Coupling pair (L-7a) | (a) `fp → tr` (driven current) | 物理的に scalar 結合が意味を持つ (RJT volume integral → PNBCD scalar) |
| API 表面 | (α) `TotPipeline.run_pipeline(steps)` のみ | 既存 `Tot.run` を変更しない最小表面. backwards compat 完全保持 |
| ファイル分離 | (新提案) `python/totlib/pipeline.py` を別ファイル新設 | legacy `Tot` (test/regression 用) と `TotPipeline` (新規ユーザ用) を完全独立化 |
| MCP | (A) `run_pipeline` を MCP tool として露出 | force-close pattern を踏襲して isolation 保証 |
| テスト | (I) Equivalence test (1e-10 tolerance) | CLAUDE.md "Equivalence tests at 1e-10 tolerance MUST pass" に整合 |

## 3. 非ゴール (L-7a で扱わない)

- Profile 級 coupling (`eq` の q/p, `wr` の deposition profile, `fp` の RJT profile)
- BPSD ABI 公開 (`<mod>_api_bpsd_sync()` 等の Fortran 側新 ABI)
- Coordinate 変換 (rho_T ↔ psi, ray-bin ↔ radial-bin)
- Declarative `tot.couple(src, dst)` API
- Per-module state aggregation (`Tot.get_state().fp_scalars` 等)
- Legacy `Tot.run(ntmax)` の挙動変更 (永久に変更しない)
- `wr/wrx/eq/ti` を含む coupling rule (L-7b 以降で同じパターン適用)

## 4. アーキテクチャ概観

### 4.1 ファイル構成

```
python/totlib/
  ├── totlib.py        既存. class Tot (legacy, libtotapi.so wrapper, L-6 TR-only)
  │                    用途: regression test / equivalence baseline / 既存 MCP tool
  │                          (init/run/get_state/...) のバッキング
  │                    L-7a で一切変更しない
  │
  ├── pipeline.py      新規. class TotPipeline (Python-side scalar coupler)
  │                    用途: 新規ユーザコード / L-7a の MCP tool (run_pipeline) のバッキング
  │                    既存 Eq/Trlib/Fplib/Wrlib/Wrxlib/Tilib wrapper を組み合わせる
  │                    薄い orchestrator. libtotapi.so には触れない
  │
  ├── __init__.py      `Tot` に加えて `TotPipeline` を export
  └── tests/
       ├── test_totlib.py        既存. 変更しない
       ├── test_pipeline.py      新規. mock-based unit test
       └── test_pipeline_equiv.py 新規. fp+tr equivalence test (lib*.so 必要)

python/mcp-servers/tot_mcp/
  └── server.py        既存 tools (init/run/...) は不変
                       新 tool: run_pipeline(steps, params)
                       既存 STATE (Tot) と独立した PIPELINE_STATE (TotPipeline) を持つ
```

### 4.2 ユーザから見た使い分け

| 用途 | import / クラス |
|---|---|
| TR 単独 transport (legacy 互換, regression) | `from totlib import Tot` |
| 多モジュール scalar coupling (L-7a 以降の主流) | `from totlib import TotPipeline` |
| 単一モジュールを直接叩く | 既存通り `from trlib import Trlib` 等 |

### 4.3 重要な不変条件

1. **シングルトン制約は per-module wrapper 側で enforce** — `TotPipeline` 自体は singleton 化しない. ただし内部で `Fplib()` を作るので, 同一プロセスで複数 `TotPipeline` を立てても fp/tr の wrapper-level singleton 制約に当たる.
2. **legacy `Tot` と `TotPipeline` の同一プロセス併用は禁止** — どちらも内部で `tr_init` を呼ぶ → COMMON 二重 init のリスク. README で明記し, MCP server level で gate (片方が live なら他方を force-close).
3. **`run_pipeline` 内の失敗時**: open 済 module wrapper は finalize しない. ユーザが `tot.close()` で明示解放. 失敗時の中間状態は debug 価値あり.

## 5. コンポーネント詳細

### 5.1 例外型階層 (`python/totlib/errors.py` に追加)

```python
class TotPipelineError(TotlibError):
    """Base for TotPipeline-only errors."""

class TotPipelineUnknownModuleError(TotPipelineError):
    """run_pipeline の steps に未知のモジュール名."""

class TotPipelineCouplingError(TotPipelineError):
    """Coupling rule 適用時の失敗 (source key 不在, transform 例外, 入力検証等)."""

class TotPipelineLifecycleError(TotPipelineError):
    """closed instance への operation."""

class TotPipelineRunError(TotPipelineError):
    """Pipeline 実行中に per-module run / coupling が失敗.

    Attributes:
        partial_result: PipelineResult with steps completed before failure
        failed_step_index: int
        failed_module: str
    """
    def __init__(self, message, partial_result, failed_step_index, failed_module):
        super().__init__(message)
        self.partial_result = partial_result
        self.failed_step_index = failed_step_index
        self.failed_module = failed_module
```

per-module 例外 (`FplibCalcFailedError`, `TrlibError` 等) の伝播ルール:

- `run_pipeline` の **for ループ内** (lazy open / coupling rule 適用 / `module.run` を含む): `TotPipelineRunError` で wrap して `partial_result` を渡す. 元例外は `__cause__` に残す.
- `set_param` 経由の `_ensure_module` 失敗 (= run_pipeline の外で初回 lazy open が失敗): wrap せずそのまま伝播.
- `close()` 中の per-module finalize 失敗: wrap せずそのまま伝播 (ただし全 module の close は試みる, 最初の例外のみ raise).

### 5.2 CouplingRule データクラス

```python
@dataclass(frozen=True)
class CouplingRule:
    src_state_key: str | Callable[[ModuleState], float]
        # str: prev_state.scalars[key] でルックアップ
        # callable: prev_state (per-module の State 型: FpState | TrState | ...)
        #          を引数に渡して float を返す. R2 の profile→scalar 変換用.
        # ModuleState は型エイリアス: ModuleState = Union[FpState, TrState, EqState,
        #                                                  WrState, WrxState, TiState]
    dst_param: str
    transform: Callable[[float], float] = lambda v: v
    doc: str = ""

COUPLING_RULES: dict[tuple[str, str], list[CouplingRule]] = {
    ("fp", "tr"): [
        CouplingRule(
            src_state_key=...,         # R2 で確定
            dst_param=...,             # R3 で確定 (e.g. "PNBCD")
            transform=...,             # R3 で確定 (e.g. lambda v: v * 1e-6 for A→MA)
            doc="fp driven current (RJT volume integral) -> tr <param>",
        ),
    ],
}
```

### 5.3 PipelineResult / PipelineStep

```python
@dataclass
class PipelineStep:
    module: str
    scalars: dict[str, float]
    coupling_applied: list[str]   # この step に適用された rule の doc

@dataclass
class PipelineResult:
    steps: list[PipelineStep]

    def last(self, module: str) -> PipelineStep:
        for s in reversed(self.steps):
            if s.module == module:
                return s
        raise KeyError(module)

    def to_dict(self) -> dict:
        out: dict[str, Any] = {}
        for step in self.steps:
            out[step.module] = step.scalars   # 後勝ち (同モジュール複数回時)
        out["_steps"] = [
            {"module": s.module, "scalars": s.scalars,
             "coupling_applied": s.coupling_applied}
            for s in self.steps
        ]
        return out
```

### 5.4 TotPipeline 主要メソッド

```python
class TotPipeline:
    def __init__(self):
        self._modules: dict[str, Any] = {}
        self._closed = False

    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def set_param(self, namespaced: str, value):
        """e.g. set_param('fp:NSAMAX', 2)."""

    def run_pipeline(self, steps: list[tuple[str, dict]]) -> PipelineResult:
        """順序付き steps で fp/tr/... を実行. 隣接 step 間で COUPLING_RULES を適用."""

    def close(self):
        """全 per-module wrapper を finalize. 冪等. 例外集約."""
```

### 5.5 内部ヘルパ

```python
_MODULE_REGISTRY = {
    "fp":  ("fplib",  "Fplib",  "FplibError"),
    "tr":  ("trlib",  "Trlib",  "TrlibError"),
    "eq":  ("eqlib",  "Eq",     "EqlibError"),
    "wr":  ("wrlib",  "Wrlib",  "WrlibError"),
    "wrx": ("wrxlib", "Wrxlib", "WrxlibError"),
    "ti":  ("tilib",  "Tilib",  "TilibError"),
}
# 3 番目のフィールドは各モジュールの **base error class 名**.
# 全 wrapper の errors.py に存在することを Codex review (#8/#13/#14) で確認済.

def _import_wrapper(name: str):
    """lazy: 該当モジュールがいま必要になった時点で import."""
    if name not in _MODULE_REGISTRY:
        raise TotPipelineUnknownModuleError(...)
    pkg, cls_name, _ = _MODULE_REGISTRY[name]
    return getattr(importlib.import_module(pkg), cls_name)

def _import_module_error(name: str) -> type[Exception]:
    """lazy: 該当モジュールの base error class を on-demand で resolve.
    _import_wrapper と同じく, 使われないモジュールの errors.py は import しない."""
    pkg, _, err_cls_name = _MODULE_REGISTRY[name]
    errors_mod = importlib.import_module(f"{pkg}.errors")
    return getattr(errors_mod, err_cls_name)
```

## 6. データフロー / Lifecycle

### 6.1 Per-module wrapper の lazy 生成

`__init__` では何も open しない. `set_param("fp:...")` または `run_pipeline([("fp",...), ...])` 内で `Fplib()` を生成 + `_open()`.

### 6.2 `run_pipeline` のフルフロー

```python
def run_pipeline(self, steps):
    if self._closed:
        raise TotPipelineLifecycleError(...)
    self._validate_steps(steps)   # fail-fast pre-flight (副作用なし)

    result_steps: list[PipelineStep] = []
    prev_name, prev_state = None, None

    # 例外 catch は **per-step に lazy resolve**: その step で使うモジュールの
    # base error class だけ import する. 各モジュールの errors.py を eager に
    # 全部 import すると section 5.5 の lazy 方針 (使わないモジュールの lib*.so を
    # load しない) に反するので, _import_module_error でその step だけ resolve する.
    # (Codex review #C で flag された lazy-import 整合性確保のため)

    for i, (name, kwargs) in enumerate(steps):
        # この step で catch すべき per-module 例外を lazy resolve
        base_err = _import_module_error(name)
        try:
            module = self._ensure_module(name)
            applied: list[str] = []

            if prev_name is not None:
                for rule in COUPLING_RULES.get((prev_name, name), []):
                    raw = self._extract_source(prev_state, rule)
                    transformed = rule.transform(raw)
                    module.set_param(rule.dst_param, transformed)
                    applied.append(rule.doc)

            module.run(**kwargs)
            cur_state = module.get_state()
            result_steps.append(PipelineStep(
                module=name,
                scalars=dict(cur_state.scalars),
                coupling_applied=applied,
            ))
            prev_name, prev_state = name, cur_state
        except (base_err, TotPipelineCouplingError) as e:
            raise TotPipelineRunError(
                f"step {i} ({name}) failed: {e}",
                partial_result=PipelineResult(steps=result_steps),
                failed_step_index=i,
                failed_module=name,
            ) from e

    return PipelineResult(steps=result_steps)
```

`_validate_steps` は dict lookup のみで副作用なし — `_ensure_module` を呼ばずに「未知 module 名」「不正 kwargs」「空 steps」を即時 reject.

### 6.3 `close()` lifecycle

```python
def close(self):
    if self._closed:
        return
    errors: list[Exception] = []
    for name, module in list(self._modules.items()):
        try:
            module.close()
        except Exception as e:
            errors.append(e)
    self._modules.clear()
    self._closed = True
    if errors:
        raise errors[0]
```

冪等. 1 module の close 失敗で他がスキップされない. 最初の例外を raise (root cause を見失わないため `__cause__` chain 維持より visibility 優先).

### 6.4 MCP server 側

```python
PIPELINE_STATE: TotPipeline | None = None

def _force_close_pipeline():
    global PIPELINE_STATE
    if PIPELINE_STATE is not None:
        try:
            PIPELINE_STATE.close()
        finally:
            PIPELINE_STATE = None

@tool
def run_pipeline(steps: list[dict], params: dict | None = None) -> dict:
    """Args:
        steps: [{"module": "fp", "kwargs": {"ntmax": 5}}, ...]
        params: {"fp:NSAMAX": 2, ...} optional
    Returns:
        PipelineResult.to_dict()
    """
    global STATE
    if STATE is not None:
        # legacy STATE が live なら force-close (section 4.3 不変条件 #2)
        STATE.close()
        STATE = None
    _force_close_pipeline()
    PIPELINE_STATE = TotPipeline()
    if params:
        for k, v in params.items():
            PIPELINE_STATE.set_param(k, v)
    normalized = [(s["module"], s.get("kwargs", {})) for s in steps]
    return PIPELINE_STATE.run_pipeline(normalized).to_dict()
```

既存 `tot_mcp/server.py:597` の `run_and_get_state` の force-close pattern (HIGH audit fix 2026-04-22) と同じ思想.

## 7. エラー処理

| 分類 | 発生タイミング | 例外型 / Wrap policy |
|---|---|---|
| 入力検証 | API 呼出時即時 | `TotPipelineCouplingError` / `TotPipelineUnknownModuleError` (raise 直接) |
| Lifecycle | API 呼出時即時 | `TotPipelineLifecycleError` (raise 直接) |
| Coupling rule | `run_pipeline` の step 開始直前 | `TotPipelineCouplingError` → `TotPipelineRunError` で wrap (`__cause__` chain) |
| Per-module run | `run_pipeline` 内の `module.run` | per-module 固有 → `TotPipelineRunError` で wrap |
| Per-module init via run_pipeline | `run_pipeline` 内の lazy `_ensure_module` | per-module 固有 → `TotPipelineRunError` で wrap |
| Per-module init via set_param | `set_param` 経由の `_ensure_module` (run_pipeline 外) | per-module 固有 (wrap しない) |
| Per-module finalize | `close()` 中 | per-module 固有 (wrap しない. 最初の例外のみ raise) |

## 8. Pre-flight Research (実装着手前ゲート)

以下 R1/R2/R3 が確定するまで実装に着手しない. plan ドキュメントに研究タスクを設け, 結果を本 spec の Research outcomes 節に追記してから実装フェーズへ移行する.

### R1. Singleton 共存性 + 再 init 状態リーク検証

**目的**: 以下 2 点を検証する.
- (R1-a) `Fplib()` と `Trlib()` が同一 Python プロセスで **同時 live** できる
- (R1-b) `Trlib()` を `close → 新規 open` で **再生成** したとき, 直前 instance の Fortran COMMON 状態が漏れない (CLAUDE.md "Module-level state doesn't fully reset between finalize and the next init" 警告への対処)

**手順 (R1-a 同時 live)**:

```python
from fplib import Fplib
from trlib import Trlib
fp = Fplib()
tr = Trlib()
fp.run(ntmax=1)        # 既存 fplib の最小動作 fixture
tr.run(ntmax=1)        # 既存 trlib の最小動作 fixture
fp_state = fp.get_state()
tr_state = tr.get_state()
fp.close()
tr.close()
```

**期待結果**: 例外なく完走. fp_state/tr_state の scalars がそれぞれ **単独 run の結果と 1e-10 tolerance で一致**.

**手順 (R1-b 再 init での状態リーク検証)**:

```python
# サイクル 1
tr1 = Trlib()
tr1.set_param("RR", 6.2); tr1.set_param("RA", 2.0)
tr1.run(ntmax=1)
state1 = dict(tr1.get_state().scalars)
tr1.close()

# サイクル 2: 異なる param で再 init
tr2 = Trlib()
tr2.set_param("RR", 1.7); tr2.set_param("RA", 0.5)   # ITER → small device
tr2.run(ntmax=1)
state2 = dict(tr2.get_state().scalars)
tr2.close()

# サイクル 3: サイクル 1 と同じ param に戻す
tr3 = Trlib()
tr3.set_param("RR", 6.2); tr3.set_param("RA", 2.0)
tr3.run(ntmax=1)
state3 = dict(tr3.get_state().scalars)
tr3.close()
```

**期待結果**: `state1 == state3` (1e-10 tolerance). 一致しなければ Fortran 側に状態リークあり → run_pipeline 内の各 cycle で **「全 module を close → 必要 module だけ再 open」の dance** が必須になる. これは TotPipeline 内部実装変更で API 表面は不変だが, パフォーマンス劣化を伴う.

**Fallback A (R1-a fail = 同時 live 不可)**: `TotPipeline._ensure_module` 内で「他 module が open 中なら一旦 close → 自 module を open → step 完了後 close」の dance を実装.

**Fallback B (R1-b fail = 再 init で状態リーク)**: pytest 自体は `--forked` で隔離されているのでテストは pass するが, ユーザが同一 process 内で 2 サイクル連続して `run_pipeline` を呼ぶケースは状態が混在する可能性. README で「`tot.close() → 新 TotPipeline()` を毎回作成」を強く推奨し, MCP 側は既に force-close pattern で隔離済 (section 6.4).

**両 fallback が必要な場合**: 設計の根幹見直し (singleton 制約を緩和するため Fortran 側に instance handle を導入) → spec に戻る.

### R2. `rjt_volint` 抽出方針

**目的**: fp の driven current (RJT の volume integral) を scalar として取得する手段を確定.

**確認項目**:
1. `python/fplib/fplib.py` の `FpState` (state.py 等) に既存 scalars として存在するか
2. 無ければ `RJT` profile + grid 情報から Python 側で integrate 可能か (TotPipeline 内 helper として)

**推奨方針**: fplib に変更を入れず, `TotPipeline._extract_source` で profile→scalar 変換ヘルパを持つ. CouplingRule の `src_state_key` を callable にして `lambda state: integrate_rjt(state)` のような形に.

**Research output**: 確定した変換コード snippet と単位 (A) を本 spec の Research outcomes 節に記録.

### R3. tr 側の driven current 注入 param 名

**目的**: tr に driven current を scalar として注入できる param 名を確定.

**確認方法**: `tr/tr_param_registry.f90` を grep:
```bash
grep -n -E "(PNBCD|PNBI|PRFCD|PCURRENT|PCD|driven)" tr/tr_param_registry.f90
```

`set_param` で書ける param のうち, transport equation の current source に効く scalar (典型的には MA 単位) を特定.

**Fallback (適切な param が無い場合)**: L-7a の coupling pair を変更 (例: `wr → tr` の `PRFCD` で RF heating power scalar) — 設計の根幹見直しが必要なので spec に戻る.

**Research output**: 確定した param 名, 単位, transform 係数を本 spec の Research outcomes 節に記録.

### Research outcomes (実装着手前に埋める)

> _この節は R1/R2/R3 完了後に追記する. 未確定状態では「TBD」と書かない — 確定するまで本 spec は完成しない._

- R1 結果: __未確定__
- R2 結果: __未確定__
- R3 結果: __未確定__

## 9. テスト戦略

### 9.1 unit test (`test_pipeline.py`, lib*.so 不要)

`Fplib` / `Trlib` を mock してロジックだけ検証.

| Test case | 検証内容 |
|---|---|
| `test_run_pipeline_empty_steps` | `run_pipeline([])` が `TotPipelineCouplingError` |
| `test_run_pipeline_unknown_module` | `[("xx", {})]` が `TotPipelineUnknownModuleError` |
| `test_run_pipeline_bad_kwargs` | `[("fp", "not_dict")]` が `TotPipelineCouplingError` |
| `test_set_param_no_namespace` | `set_param("nokoron", 1)` が `TotPipelineCouplingError` |
| `test_set_param_lazy_open` | 未使用 module は open されない |
| `test_run_pipeline_coupling_rule_applied` | rule 適用 → mock tr の `set_param` 呼出を assert |
| `test_run_pipeline_missing_source_state` | source key 不在 → `TotPipelineCouplingError` (with `__cause__`) |
| `test_run_pipeline_partial_failure` | step 2 失敗 → `TotPipelineRunError.partial_result.steps[0].module == "fp"` |
| `test_close_idempotent` | `close()` 2 回呼出で例外なし |
| `test_close_finalize_all_modules_even_on_error` | fp.close 例外でも tr.close 呼ばれる |
| `test_context_manager` | 正常終了で close 呼出 |
| `test_context_manager_exception` | 例外時にも close 呼出 |

### 9.2 equivalence test (`test_pipeline_equiv.py`, lib*.so 必要)

CLAUDE.md "Equivalence tests at 1e-10 tolerance MUST pass" に整合.

```python
@pytest.mark.skipif(not has_lib("fplib") or not has_lib("trlib"),
                    reason="requires libfpapi.so + libtrapi.so")
def test_fp_tr_pipeline_equiv():
    # 既存 fp/tr 単独テストの fixture を bare-name dict として用意
    fp_params = {"NSAMAX": 2, ...}      # fp の set_params(**fp_params) 用
    tr_params = {"RR": 6.2, "RA": 2.0, ...}   # tr の set_params(**tr_params) 用
    # TotPipeline 用は namespaced 化:
    pipeline_params = (
        {f"fp:{k}": v for k, v in fp_params.items()}
        | {f"tr:{k}": v for k, v in tr_params.items()}
    )

    # ----- パターン X: 手書き coupling (baseline)
    fp_x = Fplib(); fp_x.set_params(**fp_params); fp_x.run(ntmax=5)
    fp_state_x = fp_x.get_state()
    rjt_volint = compute_rjt_volint(fp_state_x)   # R2 で確定する helper
    fp_x.close()
    tr_x = Trlib(); tr_x.set_params(**tr_params)
    tr_x.set_param(R3_PARAM_NAME, rjt_volint * R3_TRANSFORM)
    tr_x.run(ntmax=1)
    tr_state_x = tr_x.get_state()
    tr_x.close()

    # ----- パターン Y: run_pipeline
    pipe = TotPipeline()
    for k, v in pipeline_params.items():
        pipe.set_param(k, v)
    result = pipe.run_pipeline([("fp", {"ntmax": 5}), ("tr", {"ntmax": 1})])
    pipe.close()

    # ----- 1e-10 一致検証
    for key in fp_state_x.scalars:
        assert math.isclose(fp_state_x.scalars[key],
                            result.last("fp").scalars[key],
                            rel_tol=1e-10, abs_tol=1e-15), f"fp.{key}"
    for key in tr_state_x.scalars:
        assert math.isclose(tr_state_x.scalars[key],
                            result.last("tr").scalars[key],
                            rel_tol=1e-10, abs_tol=1e-15), f"tr.{key}"
    assert any("RJT" in d for d in result.last("tr").coupling_applied)
```

注意: `--forked --timeout=120 --timeout-method=signal` (CLAUDE.md). pytest 設定の `addopts` で global 強制.

### 9.3 MCP tool test (`test_pipeline_tool.py`)

- `run_pipeline` MCP tool が `TotPipeline` を正しく駆動 (mock-based)
- 既存 `STATE` (Tot) と新 `PIPELINE_STATE` (TotPipeline) の同時 live を gate 検出 (片方を force-close)

## 10. 受入れ基準 (Definition of Done)

1. **コード**:
   - `python/totlib/pipeline.py` 新規, `python/totlib/totlib.py` (Tot) 変更ゼロ
   - `python/totlib/__init__.py` で `TotPipeline` を export
   - `python/totlib/errors.py` に新例外型追加
   - `python/mcp-servers/tot_mcp/server.py` に `run_pipeline` tool + force-close gate

2. **テスト**:
   - `test_pipeline.py` 全パス (mock-based)
   - `test_pipeline_equiv.py` 1e-10 tolerance pass — **CLAUDE.md non-negotiable**
   - `test_pipeline_tool.py` 全パス
   - 既存 `test_totlib.py` (legacy Tot) 変更なくパス継続

3. **ドキュメント**:
   - `python/totlib/README.md` に `TotPipeline` セクション追加
   - `python/mcp-servers/tot_mcp/README.md` に `run_pipeline` tool 説明追加
   - `docs/sphinx/modules/tot/{ja,en}/applications.md` の L-7 placeholder セクションを `TotPipeline` 実例に書き換え (L-7a 範囲のみ. L-7b 残件は明示)

4. **CI**:
   - 既存 pytest workflow に `python/totlib/tests/test_pipeline*.py` が含まれる
   - 既存 `--forked --timeout=120 --timeout-method=signal` 継承
   - macOS / Linux 両 OS で pass (fp/tr のみ使用)

5. **Pre-flight Research**:
   - R1/R2/R3 全部確定 → 本 spec の Research outcomes 節に追記
   - 確定値で COUPLING_RULES の `("fp","tr")` エントリを fill

6. **Pre-push gate** (CLAUDE.md `feedback_review_before_push.md` 規約):
   - `Agent(subagent_type="feature-dev:code-reviewer", ...)` の HIGH/MED 指摘を全て解消
   - `Agent(subagent_type="codex:codex-rescue", ...)` 追加レビュー (handoff doc 推奨, factual error 検出強化)
   - **pytest 実行コマンド**: `pytest --forked --timeout=120 --timeout-method=signal python/totlib/tests/test_pipeline*.py`
     (CLAUDE.md "Pre-push gate" 要件と同一フラグ)
   - **`REVIEW_OK_<sha>` marker 配置**: `touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"` を push 前に必ず実行
   - `--no-verify` / `--no-gpg-sign` / `--admin` merge 禁止
   - rebase / amend 後は SHA 変更により marker も再作成

7. **PR 戦略** (Codex review #18 を反映, スコープ大):
   L-7a は (TotPipeline class + MCP tool + equivalence test + docs) で diff が大きいため **3 sub-PR に分割推奨**:

   - **PR 1 (Foundation)**: `python/totlib/pipeline.py` 新規 + `_PER_MODULE_ERRORS` tuple + `TotPipelineError` family in `python/totlib/errors.py` + unit test (mock-based, lib*.so 不要) + Research outcomes (R1/R2/R3) を本 spec に追記.
     - レビュアー負荷: 中. lib*.so 不要なのでローカル CI fast.
   - **PR 2 (Equivalence test)**: `test_pipeline_equiv.py` 追加 + `compute_rjt_volint` helper + COUPLING_RULES の `("fp","tr")` エントリ fill + 1e-10 tolerance gate.
     - レビュアー負荷: 高 (物理検証が要点). lib*.so 必要.
   - **PR 3 (MCP integration)**: `tot_mcp/server.py` の `run_pipeline` tool + force-close gate + `test_pipeline_tool.py` + docs (`applications.md`, README).
     - レビュアー負荷: 中. 既存 MCP test pattern 流用.

   **代替**: 1 PR で出す場合は commit を上記 3 単位で分割 (`git rebase -i` で commit 整理は禁止 — CLAUDE.md "Do not use --no-edit with git rebase"). 必ず PR description で「L-7a スコープ + L-7b 残件 (profile coupling, BPSD ABI, declarative `couple()`)」を明記.

## 10.5 既知制約 (Codex review で flagged, plan/implementation で気をつける項目)

- **MCP 入力 schema の brittleness** (Codex #11, #15): 既存 `tot_mcp/server.py` の tool 実装は FastMCP の `Dict[str, Any]` パラメータを受けており, nested dict (`steps: list[dict]`) の構造を strict に validate しない. 不正な入力 (例: `{"module": "fp"}` で `kwargs` キー欠落) は Python KeyError として出る可能性. 実装時に `_validate_steps` (section 6.2) を MCP tool 側でも実行 → `TotPipelineCouplingError` に正規化することで mitigate.
- **MCP force-close の競合状態** (Codex #12): `STATE` (legacy Tot) と `PIPELINE_STATE` (TotPipeline) の force-close gate は同期的処理を前提. 既存 MCP server は single-thread (FastMCP の async event loop 内で逐次処理) なので race は起きない想定だが, 将来 multi-client 対応時には mutex 必要 — この時点では plan で記録のみ.
- **モジュール base error の命名規約依存**: `_MODULE_REGISTRY` に各モジュールの base error class 名 (`FplibError` 等) をハードコードしている. 該当 errors.py のリネーム / base class 階層変更時は registry も更新必須. CI で lint check を入れることが望ましい (各 `<pkg>.errors` に登録されたクラス名が実在するか起動時 assert する仕組み — 実装は plan 段階で検討).

## 11. 非機能要件

- **パフォーマンス**: `run_pipeline` のオーバヘッドは `Fplib.run` + `Trlib.run` の合計の 5% 以下 (coupling rule 適用が boilerplate より小)
- **メモリ**: 同一プロセスで `Fplib + Trlib` 両 live で resident memory 増加が単独 run の合計と比較して 10% 以下 (`tracemalloc` 確認)
- **API 安定性**: `PipelineResult` は L-7b 以降も前方互換 (新 field 追加のみ. 既存 field の型変更/削除禁止)

## 12. L-7b 以降の follow-up (本 spec 範囲外)

- `wr → fp`: RF deposition power scalar coupling (`wr.pwrtot → fp.PRF`)
- `wr → tr`: RF heating power scalar coupling
- `eq → tr`: profile 級 coupling (psi↔rho 変換が必要 → BPSD ABI 公開と同時)
- `<mod>_api_bpsd_sync()` Fortran ABI を全モジュール (eq/tr/wr/wrx/fp/ti) に追加 (L-7b)
- Declarative `tot.couple(src, dst)` API (L-7c)
- `Tot.get_state().fp_scalars` 等の per-module state aggregation (L-7b)
- `applications.md` の L-7 placeholder を完全に解消する次世代版

## 13. 参考

- handoff doc: `.claude/handoff-2026-04-28.md`
- 既存 spec (関連): `docs/superpowers/specs/2026-04-17-tr-library-design.md`
- Legacy Fortran 結合機構: `tot/totmain.f90`, `tot/totmenu.f90`, `tr/trloop.f90:65-83` (BPSD broker)
- 現 L-6 ABI: `tot/tot_api.f90`, `tot/tot_state.f90`
- 現 L-6 Python wrapper: `python/totlib/totlib.py`
- 現 L-6 MCP: `python/mcp-servers/tot_mcp/server.py`
- CLAUDE.md (pre-push gate, equivalence test): `/Users/k-yoshimi/Dropbox/cursor/task/CLAUDE.md`
