# L-7b-i External Driven Current Scalar — Design Spec

- 日付: 2026-05-02
- ブランチ (予定): `claude/2026-05-02-l7b-i-external-driven-i`
- ベースブランチ: `chore/pre-push-hook-worktree-compat`
- 対象モジュール: `tr/`, `python/totlib/`, `python/trlib/`
- 関連 commit: 0eaa25ac (handoff 2026-05-02)
- スコープ層: L-7b-i (L-7b の最初のサブ計画)
- 前提 spec: `docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md`

---

## 1. 目的と背景

L-7a は Python pipeline (`TotPipeline.run_pipeline`) で `fp → tr` の scalar coupling を実装したが, R3 の発覚で tr 側に「外部から MA で driven current を注入する」 scalar param が無いため, fallback として `PLHCD` (LH dimensionless multiplier) を流用する **skeleton coupling** にとどまった.

L-7a spec §12 follow-up リスト先頭:

> tr に `EXTERNAL_DRIVEN_I_MA` (or similar) scalar param を新規追加 — R3 で発覚した skeleton coupling 問題の真の解決. `tr/tr_param_registry.f90` に CASE 追加 + `tr/trcomm_param.f90` に COMMON 変数追加 + tr の transport eq の current source 項に注入. これで fp の `compute_rjt_volint` 出力を物理的整合性のある形で tr に流せる.

**L-7b-i スコープ (本 spec)**: 上記 follow-up を実装する. tr 内に `EXTERNAL_DRIVEN_I` [MA] + Gaussian profile shape を制御する 2 scalar (`EXTERNAL_DRIVEN_R0`, `EXTERNAL_DRIVEN_RW`) を追加し, `AJRF` に注入する. Python pipeline の COUPLING_RULES を `PLHCD` → `EXTERNAL_DRIVEN_I` に切替, skeleton caveat を撤去する. AJRFT (= 注入された総電流の検証用 scalar) を tr_state に公開する.

**handoff 2026-05-02 §A の "verify before debug" 教訓**: ht6m と同様に, L-7a の "skeleton" 注記を "PLHCD は完全に不適切" と読まずに, 「物理的に LH 効率モデルで, 我々の駆動電流とは異なる意味」と理解した上で proper 置き換えを行う.

## 2. ブレインストーミングで確定した設計方針

| 決定項目 | 選択 | 理由要旨 |
|---|---|---|
| Scope decomposition | L-7b-i のみ本セッション | L-7b は実は 4 サブ計画 (i: scalar, ii: BPSD profile coupling, iii: declarative API, iv: state aggregation). i のみで完結 |
| Scalar の意味論 | (X) 物理駆動電流 | (Y) bookkeeping のみではユーザ goal "skeleton 撤去" と乖離. (Z) profile 注入は L-7b-ii |
| Profile shape | (B) Gaussian (`R0`, `RW` 2 param) | tr の既存 PLH/PIC/PEC pattern と整合, axis-peaked default で物理妥当 |
| 単位 | MA | tr の `RIP` と整合, L-7a §12 仮称 `EXTERNAL_DRIVEN_I_MA` の精神 |
| 注入アーキテクチャ | (A) 既存 `AJRF` bucket 拡張 | (B) 専用 bucket は AJRF を sum している全箇所に diff が広がる |
| `AJRFT` C ABI 公開 | (P) 本 PR に含める | 物理整合性テスト (§7.3) の前提. 5-7 行の機械的 diff |
| `tr_api_validate` 拡張 | 本 PR に含める | `RW=0` + `I!=0` の silent no-op を user に surface するのが proper |
| Namelist サポート | 含めない | 主用途は Python pipeline 経由. forward compat で後で追加可能 |
| PR 戦略 | 単一 PR (3 commit に分割) | diff 推定 150-250 行, L-7a の 3-PR 分割するほどの規模ではない |

## 3. 非ゴール (L-7b-i で扱わない)

- **Profile 級 coupling** — fp の RJT[NR] 形状を tr に直接渡す機構. L-7b-ii (BPSD broker 経由) で実装
- **`<mod>_api_bpsd_sync()` Fortran 側新 ABI** — L-7b-ii
- **Declarative `tot.couple(src, dst)` API** — L-7b-iii
- **Per-module state aggregation (`Tot.get_state().fp_scalars` 等)** — L-7b-iv
  - ただし AJRFT 単独の C ABI 公開は本 PR に含む (本 PR 内 test の前提条件として必要)
- **`AJOHT/AJBST/AJNBT` の C ABI 公開** — AJRFT のみ. 他 3 つは L-7b-iv で current balance check を書く時に同時公開推奨
- **`PLHCD` を deprecation 路線で残すこと** — pipeline.py の COUPLING_RULES から PLHCD は完全削除. ただし `tr.set_param("PLHCD", ...)` 自体は今後も合法 (LH 用の本来の意味として)
- **wr → fp/tr, eq → tr の coupling rule** — L-7b-ii 以降
- **Trparm 名前リスト経由の EXTERNAL_DRIVEN_I 設定** — `set_param` のみ. .trparm ファイルからは読まない

## 4. アーキテクチャ概観

### 4.1 影響を受けるファイル一覧

| File | 変更内容 | 推定 +/- |
|---|---|---|
| `tr/trcomm_param.f90` | 3 scalar 宣言 (REAL(rkind)) | +5 |
| `tr/trinit.f90` | 3 default 設定 (`0.D0, 0.D0, 0.3D0`) | +5 |
| `tr/tr_param_registry.f90` | USE 句 import + 3 CASE 追加 | +6 |
| `tr/trprf.f90` | USE 句に `RM, EXTERNAL_DRIVEN_*` 追加 + Gaussian 注入 block (loop 末尾) | +20 |
| `tr/tr_api.f90` | USE 句に AJRFT 追加 + state%AJRFT zero-init + populate. validate に 1 check | +10 |
| `tr/tr_state.f90` | `tr_state_c` struct に `REAL(C_DOUBLE) :: AJRFT` 追加 (末尾) | +1 |
| `tr/tr_state.h` | C struct mirror に `double AJRFT;` 追加 (同順序) | +1 |
| `python/trlib/state.py` | `TrState.scalars` dict に `AJRFT` を append (`from_c` 経路で transparent) | +1-3 |
| `python/trlib/trlib.py` (or wrapper) | `validate()` method 既存確認, 無ければ追加 | +0 or +20 |
| `python/totlib/pipeline.py` | COUPLING_RULES の `dst_param` rewrite + skeleton caveat docstring 削除 | -8 / +3 |
| `python/totlib/README.md` | skeleton caveat block 削除 + EXTERNAL_DRIVEN_I 説明 | -10 / +15 |
| `python/trlib/README.md` | "External driven current" セクション新設 | +30 |
| `python/totlib/tests/test_pipeline.py` | PLHCD assertion 4 箇所を EXTERNAL_DRIVEN_I に置換 | ±4 |
| `python/totlib/tests/test_pipeline_equiv.py` | `tr.set_param("PLHCD", ...)` を `EXTERNAL_DRIVEN_I` に置換 + skeleton 注記削除 | -5 / +3 |
| `python/totlib/tests/test_pipeline_registry.py` | `assert rule.dst_param == "PLHCD"` 置換 | ±2 |
| `python/trlib/tests/test_external_driven_i.py` (新規) | 5 ケース (default no-op / AJT 変化 / round-trip / AJRFT 積分 / validate) | +120 |

**合計推定: ~150-220 行追加 / ~25 行削除**.

### 4.2 設計上の不変条件

1. **`EXTERNAL_DRIVEN_I = 0.D0` で `AJRF` 完全不変** — 既存 Layer 1 baseline (demo2014 + ht6m) が無修正で 1e-10 PASS 継続
2. **`AJRFT` は struct 末尾追加** — 既存 field offset を保つことで, 既存 caller の compile-time mismatch を防ぐ
3. **`PLHCD` 自体は触らない** — pipeline.py の COUPLING_RULES からのみ外す. `tr.set_param("PLHCD", ...)` は今後も合法 (LH 用の本来の意味として)
4. **Validation は OUT_OF_RANGE のみ surface** — silent no-op は維持しつつ, `tr_api_validate` で診断レベルで報告

## 5. Fortran 変更詳細

### 5.1 `tr/trcomm_param.f90`

`PLHCD` (line 37) の隣に block 追加:

```fortran
! [MA] User-supplied total externally driven current. Default 0.0 (no-op).
! Distinct from PLHCD/PECCD/PICCD: bypasses TRCDEF efficiency model — the
! given current is injected directly with a Gaussian radial profile rather
! than computed from RF wave power × efficiency.
REAL(rkind) :: EXTERNAL_DRIVEN_I    ! [MA]
REAL(rkind) :: EXTERNAL_DRIVEN_R0   ! Gaussian center [normalized rho ∈ [0,1]]
REAL(rkind) :: EXTERNAL_DRIVEN_RW   ! Gaussian width  [normalized rho]
```

### 5.2 `tr/trinit.f90`

`PLHCD = 0.D0` 等が並ぶ block の末尾に:

```fortran
EXTERNAL_DRIVEN_I  = 0.D0   ! no external drive by default → backward compat
EXTERNAL_DRIVEN_R0 = 0.D0   ! axis-peaked Gaussian
EXTERNAL_DRIVEN_RW = 0.3D0  ! width = 30% of minor radius (typical for NBI)
```

### 5.3 `tr/tr_param_registry.f90`

USE 句に追加 (line 55 周辺の TRCOMM import block):

```fortran
USE TRCOMM, ONLY: ..., &
       PLHCD, ..., &
       EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_R0, EXTERNAL_DRIVEN_RW
```

`CASE ("PLHCD"); PLHCD = value` (line 159 付近) の隣に:

```fortran
CASE ("EXTERNAL_DRIVEN_I");  EXTERNAL_DRIVEN_I  = value
CASE ("EXTERNAL_DRIVEN_R0"); EXTERNAL_DRIVEN_R0 = value
CASE ("EXTERNAL_DRIVEN_RW"); EXTERNAL_DRIVEN_RW = value
```

### 5.4 `tr/trprf.f90` の `TRPWRF` 注入

USE 句 (line 9) に追加:

```fortran
USE TRCOMM, ONLY: AJRF, AJRFV, AME, DR, DVRHO, DSRHO, EPSRHO, NRMAX, &
                  PECCD, PECNPR, PECR0, PECRW, PECTOE, PECTOT, PICCD, &
                  PICNPR, PICR0, PICRW, PICTOE, PICTOT, PLHCD, PLHNPR, &
                  PLHR0, PLHRW, PLHTOE, PLHTOT, PRF, PRFV, RA, RM, &
                  EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_R0, EXTERNAL_DRIVEN_RW
```

(DSRHO, RM, EXTERNAL_DRIVEN_* を新規追加)

既存 AJRF DO ループ末尾 (line 124 付近の `AJRF(NR) = ...` の後) に block 追加:

```fortran
! ----- L-7b-i: external driven current (scalar API, Gaussian profile) -----
! AJRFT [MA] = SUM(AJRF * DSRHO * DR) / 1.D6    (per trrslt_globals.f90:240)
! Choose AJ_ext(NR) such that SUM(AJ_ext * DSRHO * DR) = EXTERNAL_DRIVEN_I * 1.D6 [A]
! → Total contribution to AJRFT becomes EXTERNAL_DRIVEN_I [MA] exactly.
!
! Outer guard: skip when I=0 (default → no-op, backward compatible) OR when
! RW<=0 (silent: tr_api_validate surfaces this misconfiguration via OUT_OF_RANGE).
IF (EXTERNAL_DRIVEN_I /= 0.D0 .AND. EXTERNAL_DRIVEN_RW > 0.D0) THEN
   SUM_EXT = 0.D0
   DO NR = 1, NRMAX
      SUM_EXT = SUM_EXT + DEXP(-((RM(NR) - EXTERNAL_DRIVEN_R0) &
                                 / EXTERNAL_DRIVEN_RW)**2) &
                          * DSRHO(NR) * DR
   END DO
   ! Inner guard: numerical safety net for extreme RW that pushes the
   ! Gaussian entirely outside the plasma (DSRHO=0 at NR boundaries etc.).
   IF (SUM_EXT > 0.D0) THEN
      DO NR = 1, NRMAX
         AJRF(NR) = AJRF(NR) + EXTERNAL_DRIVEN_I * 1.D6 &
                    * DEXP(-((RM(NR) - EXTERNAL_DRIVEN_R0) &
                             / EXTERNAL_DRIVEN_RW)**2) &
                    / SUM_EXT
      END DO
   END IF
END IF
```

`SUM_EXT` はサブルーチン内ローカル `REAL(rkind)`. 宣言は subroutine declaration block に追加.

### 5.5 `tr/tr_state.f90` — `tr_state_c` struct 拡張

既存 struct (`AJT, BETA0, ...` が並ぶ block) の **末尾** に追加:

```fortran
TYPE, BIND(C) :: tr_state_c
  ! ... 既存 fields (NRMAX, NSMAX, NT, T, WPT, AJT, Q0, BETA0, ...) ...
  REAL(C_DOUBLE) :: AJRFT    ! L-7b-i: total RF + external driven current [MA]
END TYPE
```

末尾追加であることが重要 (既存 caller の field offset 不変保証).

### 5.6 `tr/tr_state.h` — C header sync

既存 struct definition に **同順序で** `double AJRFT;` 追加. Fortran 側の BIND(C) struct と完全に対応させる. 既存 `tr_state.h` の field 順序を grep で確認して末尾に挿入.

### 5.7 `tr/tr_api.f90` 更新

USE 句に AJRFT 追加:

```fortran
USE trcomm, ONLY: rkind, &
     NRMAX, NSMAX, NT, T, NTMAX, MODELG, KNAMEQ, &
     WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, &
     TAUE1, TAUE2, ZEFF0, ALI, RQ1, RN, RT, AJ, QP, &
     AJRFT, &
     ALLOCATE_TRCOMM, DEALLOCATE_TRCOMM, &
     EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_RW
```

`tr_api_get_state` の zero-init block (line 260 周辺) に:

```fortran
state%AJRFT = 0.0_C_DOUBLE
```

populate block (line 295 周辺) に:

```fortran
state%AJRFT = AJRFT
```

`tr_api_validate` (line 381 周辺) の既存 KNAMEQ check の後に:

```fortran
! ---- OUT_OF_RANGE: EXTERNAL_DRIVEN_I requires positive width. -------
! Non-zero I with non-positive RW would silently normalize to zero in
! trprf, leaving AJRF unchanged. Surface this so callers know their
! setting was no-op rather than physically applied.
IF (EXTERNAL_DRIVEN_I /= 0.D0 .AND. EXTERNAL_DRIVEN_RW <= 0.D0) THEN
   CALL push_diag("EXTERNAL_DRIVEN_RW", TR_DIAG_OUT_OF_RANGE, &
        "non-positive width with non-zero EXTERNAL_DRIVEN_I; profile cannot be normalized (silent no-op)")
END IF
```

### 5.8 影響範囲のスコープ確認 (再確認)

既存 `AJRF` を sum している code は default 0 で挙動不変:

- `trcalc.f90:1059`: `AJOH = AJ - (AJNB + AJRF + AJBS)` — 加算項として透過
- `trrslt_globals.f90:240`: `AJRFT = SUM(AJRF * DSRHO) * DR / 1e6` — 新項分が AJRFT に reflect
- `trgrap.f90, trgrar.f90`: graphics — default 0 で挙動同じ

**修正必須は `trprf.f90` の TRPWRF のみ**. 他の Fortran 修正 (declaration/registry/init) は機械的.

## 6. Python 変更詳細

### 6.1 `python/totlib/pipeline.py` — COUPLING_RULES rewrite

```python
COUPLING_RULES: Dict[Tuple[str, str], List[CouplingRule]] = {
    ("fp", "tr"): [
        CouplingRule(
            src_state_key=lambda state, params: compute_rjt_volint(
                state,
                R0=params["tr:RR"],
                a=params["tr:RA"],
            ),
            dst_param="EXTERNAL_DRIVEN_I",   # was "PLHCD" (L-7a R3 fallback)
            transform=lambda v: v * 1e-6,    # Amperes → MA
            doc="fp driven current (RJT volume integral, A) -> tr EXTERNAL_DRIVEN_I (MA)",
        ),
    ],
}
```

変更は実質 2 行 (`dst_param`, `doc` の wording). `compute_rjt_volint` helper と transform は無修正.

### 6.2 Skeleton caveat docstring 削除

`pipeline.py` の line 218 周辺の 5 行コメント block を削除 (`tr's PLHCD is dimensionless ...`). CouplingRule の `doc` から "(skeleton coupling; ...)" 削除.

### 6.3 `python/trlib/state.py` — AJRFT mapping

`TrState.scalars` dict の build 経路に `AJRFT` を追加 (1 行). 具体的形式は既存 dict 構築コードに依存 (実装時 grep で確認 — 通常は `from_c()` 経由で C struct field を walk する形).

### 6.4 `python/trlib/` wrapper — `validate()` method

`validate()` が既存に存在するか実装時確認. 存在しない場合は `tr_validate` C 関数を ctypes で呼ぶ薄い wrapper (~20 行) を追加. `tr_diag_entry_c` を Python 側 dataclass にマッピング.

期待 method signature:

```python
def validate(self) -> List[TrDiagEntry]:
    """Return diagnostics from tr_api_validate (e.g. OUT_OF_RANGE for misconfigured params).
    Empty list on no issues."""
```

`TrDiagEntry` dataclass: `{param: str, code: int, msg: str}`.

### 6.5 wrapper / errors 変更: それ以外なし

- `python/totlib/errors.py`: 既存 `TotPipeline*Error` で十分, 新例外なし
- `python/totlib/_ffi.py`: そのまま, AJRFT は struct field の追加なので generic 経路で transparent

## 7. テスト戦略

### 7.1 既存テスト追従更新 (mechanical PLHCD → EXTERNAL_DRIVEN_I)

| File | 変更内容 |
|---|---|
| `python/totlib/tests/test_pipeline.py` (line 403, 419, 457, 459) | `dst_param="PLHCD"` / `assert_any_call("PLHCD", ...)` / comment / `rule.dst_param == "PLHCD"` を `EXTERNAL_DRIVEN_I` に置換 |
| `python/totlib/tests/test_pipeline_equiv.py` (line 9-12, 87-88) | skeleton 注記 docstring 削除 + `tr.set_param("EXTERNAL_DRIVEN_I", rjt_volint * 1e-6)` |
| `python/totlib/tests/test_pipeline_registry.py` | dst_param assertion 同上 |

**1e-10 等価性ロジックは不変** — pattern X (direct) と Y (pipeline) が同じ scalar 値を tr に渡す形のまま.

### 7.2 新規 test (`python/trlib/tests/test_external_driven_i.py`)

```python
"""L-7b-i: External driven current scalar verification."""
import math
import pytest
from trlib import Trlib

# ITER-like fixture (L-7a R1-b で実証済の安定 fixture を再利用)
ITER_FIXTURE = {
    "RR": 8.5, "RA": 2.0, "RKAP": 1.7, "BB": 5.3,
    "NSMAX": 2, "DT": 0.1, "NTSTEP": 10,
    # PN, PT は配列なので set_params がサポートしていれば
    "PN[1]": 1.0, "PN[2]": 1.0, "PT[1]": 1.5, "PT[2]": 1.5,
}


def _run(extra_params=None):
    tr = Trlib()
    for k, v in ITER_FIXTURE.items():
        tr.set_param(k, v)
    if extra_params:
        for k, v in extra_params.items():
            tr.set_param(k, v)
    tr.run(ntmax=1)
    state = tr.get_state()
    tr.close()
    return state


def test_external_driven_i_default_is_noop():
    """Default (un-set) と explicit 0.0 set が完全一致."""
    s_default = _run()
    s_zero    = _run({"EXTERNAL_DRIVEN_I": 0.0})
    for k in s_default.scalars:
        assert math.isclose(s_default.scalars[k], s_zero.scalars[k],
                            rel_tol=1e-10, abs_tol=1e-15), f"diverged: {k}"


def test_external_driven_i_changes_ajt():
    """I=1.0 MA で AJT が default 時から有意に変化."""
    s_zero = _run()
    s_one  = _run({"EXTERNAL_DRIVEN_I": 1.0})
    assert abs(s_one.scalars["AJT"] - s_zero.scalars["AJT"]) > 0.5, \
        f"insufficient AJT shift: {s_zero.scalars['AJT']} vs {s_one.scalars['AJT']}"


def test_external_driven_i_integrates_to_total():
    """AJRFT (= 注入総量) が指定 EXTERNAL_DRIVEN_I に一致.
    Default 時 AJRFT = 0, I=1.0 時 AJRFT ≈ 1.0 (transport の 1 step での非線形効果込み)."""
    s_zero = _run()
    s_one  = _run({"EXTERNAL_DRIVEN_I": 1.0})
    assert math.isclose(s_zero.scalars["AJRFT"], 0.0, abs_tol=1e-12)
    # 1 step (NTSTEP=10, DT=0.1) 経過後の AJRFT は注入分そのものに非常に近い.
    # 厳密一致 (1e-10) は transport の back-reaction で外れるので緩めに.
    assert math.isclose(s_one.scalars["AJRFT"], 1.0, rel_tol=1e-3, abs_tol=1e-6)


def test_external_driven_r0_rw_round_trip():
    """3 scalar 全てが set_param 経由で受け付けられる (registry CASE 漏れ検知)."""
    tr = Trlib()
    for k, v in ITER_FIXTURE.items():
        tr.set_param(k, v)
    tr.set_param("EXTERNAL_DRIVEN_I",  0.5)
    tr.set_param("EXTERNAL_DRIVEN_R0", 0.2)
    tr.set_param("EXTERNAL_DRIVEN_RW", 0.4)
    tr.run(ntmax=1)
    tr.close()
    # 例外無く完走 = registry に 3 CASE 全て登録済


def test_external_driven_validate_zero_width():
    """RW=0 + I!=0 を tr_api_validate が OUT_OF_RANGE で surface."""
    tr = Trlib()
    for k, v in ITER_FIXTURE.items():
        tr.set_param(k, v)
    tr.set_param("EXTERNAL_DRIVEN_I",  1.0)
    tr.set_param("EXTERNAL_DRIVEN_RW", 0.0)
    diags = tr.validate()
    assert any(d.param == "EXTERNAL_DRIVEN_RW" and
               d.code == "OUT_OF_RANGE" for d in diags), \
        f"expected OUT_OF_RANGE diag, got: {diags}"
    tr.close()
```

### 7.3 物理整合性テストの根拠

§7.2 の `test_external_driven_i_integrates_to_total` は spec §5.4 の Gaussian normalization が正しいかの gate. 計算式:

- AJRFT [MA] = `SUM(AJRF * DSRHO) * DR / 1e6`
- 注入分: `SUM(AJ_ext * DSRHO * DR) = EXTERNAL_DRIVEN_I * 1e6 [A]`
- → AJRFT への寄与 = `EXTERNAL_DRIVEN_I [MA]` (厳密)

1 step transport 後は back-reaction で多少ずれるので tolerance `rel_tol=1e-3`. 0 step (init 直後) で AJRFT を取れるなら 1e-10 も可能だが, tr_api_run 経由で `ntmax=1` を強制する設計のため緩めに.

### 7.4 既存 Layer 1 equivalence 回帰

`test_run/baselines/tot_*_short/metrics.json` との 1e-10 比較は **default=0 で挙動不変なので無修正 PASS** が期待値. CI で自動検証されるので追加 step 不要. これが backward compat の最強保証.

### 7.5 Pipeline equivalence 回帰

`test_pipeline_equiv.py` の 1e-10 PASS は §7.1 の更新後に変わらず通る (logic 同一, dst_param のみ swap). E0=0.001 fixture で `compute_rjt_volint ≈ 9.46e5 A → EXTERNAL_DRIVEN_I ≈ 0.946 MA` が tr に渡る. **実測 final state (AJT, BETA0 等) は L-7a 時と物理的に異なる** (= 物理進歩の証拠). baseline 追従不要.

### 7.6 CI 統合

- 新 test ファイル `python/trlib/tests/test_external_driven_i.py` は既存 trlib pytest sweep に自動的に拾われる
- `--forked --timeout=120 --timeout-method=signal` 既存運用のまま
- macOS / Linux 両 OS で PASS が要件 (libtrapi.so のみ使用)
- 期待: 既存 PASS 数 (現状 206) + 新 5 ケース = 211 passed

## 8. ドキュメント更新

| File | 変更内容 |
|---|---|
| `python/totlib/README.md` (~ line 290-299) | "Skeleton coupling caveat" block 削除. `PLHCD [dimensionless] (skeleton)` → `EXTERNAL_DRIVEN_I [MA] (physical injection via Gaussian profile)` 説明に書き換え. defaults `(R0=0.0, RW=0.3)` 明記 |
| `python/totlib/pipeline.py` (~ line 218-) | 既存 5 行 skeleton caveat コメント削除. CouplingRule の `doc` から "(skeleton coupling; ...)" 削除 |
| `python/trlib/README.md` | 新規セクション "External driven current" (~30 行). 3 scalar の意味, default, set_param 経由の使い方, AJRFT で総量検証可能なことを記載 |
| `docs/sphinx/modules/tot/{ja,en}/applications.md` (存在すれば) | L-7a の "skeleton" 注記を削除し L-7b-i landed を反映. 存在しなければ作成しない |

## 9. エラー処理 / Edge cases

### 9.1 入力検証

| Layer | 戦略 |
|---|---|
| Registry (`tr_param_set`) | 値の妥当性 check しない (PLH/PIC と同じ pattern, 単純代入) |
| trprf 注入 block | 2 段ガード — 外側 `I != 0 .AND. RW > 0`, 内側 `SUM_EXT > 0`. silent no-op で NaN/Inf 防止 |
| `tr_api_validate` | `I != 0 .AND. RW <= 0` で OUT_OF_RANGE 診断 push (新規追加) |
| Python wrapper | `validate()` 経由で診断にアクセス (新規 method or 既存) |

### 9.2 Edge cases (table)

| ケース | 挙動 |
|---|---|
| `EXTERNAL_DRIVEN_I = 0.0` (default) | trprf block skip → AJRF 完全不変 |
| `EXTERNAL_DRIVEN_I < 0.0` | counter-current として AJRF に負寄与, 物理的妥当 → 許容 |
| `EXTERNAL_DRIVEN_RW = 0.0` (with I!=0) | trprf 外側 guard で skip → silent no-op. validate で OUT_OF_RANGE diag |
| `EXTERNAL_DRIVEN_R0 > 1.0` または `< 0.0` | Gaussian 中心 plasma 外, 端に局在. SUM_EXT > 0 なら正常動作. validate なし |
| `EXTERNAL_DRIVEN_RW = 1e-30` (極端小) | Gaussian が 1 grid 点に集中, SUM_EXT 浮動小数下限近辺. 数値安全網は内側 guard のみ (診断責任は呼び出し側) |

### 9.3 Concurrency

`tr_param_registry` は SAVE 変数. EXTERNAL_DRIVEN_I も globals. multi-instance Trlib は元々禁止. `--forked` test isolation で十分.

### 9.4 Performance

- Fortran 注入 block: `O(NRMAX)` の DO ループ 2 回 + DEXP 呼び出し. NRMAX ~50-100 で無視できる
- Python COUPLING_RULES: 1 行差し替え, runtime cost 不変

## 10. 受入れ基準 (Definition of Done)

| カテゴリ | 要件 |
|---|---|
| Fortran | trcomm_param に 3 scalar 宣言. trinit に default. tr_param_registry に 3 CASE. trprf に Gaussian 注入. tr_api_validate に 1 check. AJRFT を tr_state struct に追加. tr_state.h を sync |
| Python | pipeline.py の COUPLING_RULES が EXTERNAL_DRIVEN_I 採用. trlib/state.py が AJRFT を含む. trlib wrapper の validate() 経路 (必要なら新設) |
| Test | 5 新ケース PASS. 既存 test_pipeline*.py が新 dst_param で PASS. Layer 1 equivalence (demo2014 + ht6m) 1e-10 PASS 継続 (default 0 backward compat の最終 gate) |
| CI | 全 pytest sweep PASS (期待 211 passed + 1 unrelated Python 3.10 fail). macOS local 同等 |
| Doc | totlib/README + trlib/README + pipeline.py docstring 更新済 |
| Process | feature branch + PR (chore base). pre-push gate 完了. REVIEW_OK marker. HIGH/MED 反映 |

## 11. PR 戦略 + Pre-push gate

### 11.1 単一 PR (3 commit に分割)

1. `tr+totlib: add EXTERNAL_DRIVEN_I scalar (Fortran + AJRFT C ABI exposure)` — Fortran 全変更 + python/trlib/state.py + trlib wrapper validate() 拡張
2. `pipeline: replace PLHCD skeleton with EXTERNAL_DRIVEN_I (L-7b-i)` — pipeline.py + 既存 test_pipeline*.py 更新
3. `test+docs: external driven current verification + skeleton caveat removal` — 新 test_external_driven_i.py + READMEs

### 11.2 Branch 戦略

```bash
git checkout -b claude/2026-05-02-l7b-i-external-driven-i
# ... 3 commit ...
git push -u origin claude/2026-05-02-l7b-i-external-driven-i
gh pr create --base chore/pre-push-hook-worktree-compat \
    --title "tr+totlib: physical EXTERNAL_DRIVEN_I scalar (L-7b-i)" \
    --body "..."
```

handoff 2026-05-02 §C "直接 chore push 厳禁, content commit は PR 経由" を遵守.

### 11.3 Pre-push gate (CLAUDE.md 規約)

push 前に:

1. **Local pytest** (`--forked --timeout=120 --timeout-method=signal`)
   - `python/totlib/tests/`, `python/trlib/tests/`, `python/mcp-servers/tot_mcp/tests/`
   - Layer 1 equivalence (`test_equivalence.py`) も含める
   - 期待: 211 passed (+ Python 3.10 unrelated 1 fail = ExceptionGroup, 既存問題)
2. **In-house code-reviewer** Agent on cumulative diff (cumulative since last reviewed commit)
3. **Codex independent reviewer** Agent on same diff (並列起動)
4. HIGH/MED 指摘を user に共有 → 解消 (新 commit で fix; amend 禁止)
5. **REVIEW_OK marker**: `touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"`
6. Push → PR open
7. CI green 待ち + (起動すれば) Cursor Bugbot COMPLETED 待ち
8. Merge (squash) — `--admin` / `--no-verify` 厳禁

## 12. Risk register

| Risk | 影響 | 軽減策 |
|---|---|---|
| `tr_state` C struct ABI 拡張で既存 caller compile-time mismatch | tot/totlib/trlib | AJRFT を **struct 末尾** に追加. 全 USE/import を grep で確認 |
| `trlib` wrapper に `validate()` が未実装 | §7.2 validation test 失敗 | 既存 method パターン (`run`, `set_param`) 踏襲して 20 行で追加. ctypes 既存パターン流用 |
| trprf USE 句に `RM, DSRHO` が import 不足 | コンパイル失敗 | 実装時 USE 文に明示追加 |
| Layer 1 baseline (demo2014 + ht6m) の値が float 順序変化で 1e-10 から動く | CI red | EXTERNAL_DRIVEN_I=0 default で trprf 追加 block 自体が skip → 数値演算完全同一. 順序変化は起き得ない |
| L-7a `test_pipeline_equiv.py` が PLHCD → EXTERNAL_DRIVEN_I 切替後 value 一致しなくなる | test red | dst_param 変更だけで logic 不変, 同じ scalar を tr に渡す形 → 1e-10 一致は維持. 実測 final state 値は物理的に異なる (= 進歩) |
| `tr_api_validate` 拡張を Codex reviewer が "scope creep" と指摘 | review delay | PR description で "user-requested in spec § 5.2" と明記. spec 本文に validation を含めた合意あり |
| `AJRFT` の expose で他 totals (AJOHT/AJBST/AJNBT) も並列公開を求められる | review delay | spec § 3 で「本 PR は AJRFT のみ. 他 3 は L-7b-iv で current balance test を書く時に同時公開推奨」と明記 |
| 物理整合性テスト §7.3 が 1 step 後 back-reaction で `rel_tol=1e-3` を外す | test red | tolerance を緩める (1e-2) か, ntmax=0 path を test で使う. 実装時に実測値を見て調整 |

## 13. L-7b 残件 (本 spec 範囲外, 次セッション以降)

- **L-7b-ii: BPSD broker 経由 profile coupling** — wr → fp/tr の deposition profile, eq → tr の q profile 等. 各 module への `<mod>_api_bpsd_sync()` ABI 公開含む. 推定 1-数日.
- **L-7b-iii: Declarative `tot.couple(src, dst)` API** — CouplingRule の宣言的構築 + ヒューリスティック解決. Python のみ, 推定 半日〜1日.
- **L-7b-iv: Per-module state aggregation** — `Tot.get_state().fp_scalars`, `tr_scalars` 等. 同時に AJOHT/AJBST/AJNBT の C ABI 公開も実施し current balance check (`AJT ≈ AJOH+AJNB+AJRF+AJBS`) test を書ける.
- **`PNBCD` を tr_param_registry に追加** — NBI 用 dimensionless multiplier. EXTERNAL_DRIVEN_I とは独立な改修. 必要に応じて L-7b-iv で.
- **Trparm namelist 経由の EXTERNAL_DRIVEN_I 設定** — forward compat 必要時に追加.

## 14. 参考

- 前提 spec: `docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md` (commit 0a12bd07)
- handoff 2026-05-02: `.claude/handoff-2026-05-02.md` (commit 0eaa25ac)
- Legacy 注入 pattern: `tr/trprf.f90:31-124` (PEC/PLH/PIC current drive formulas)
- AJRF 単位 / 積分式: `tr/trgrad.f90:61` (`A/m^2`), `tr/trrslt_globals.f90:240` (`AJRFT [MA] = SUM * DR / 1e6`)
- AJRF reset: `tr/trcalc.f90:48`
- TR C ABI: `tr/tr_api.f90`, `tr/tr_state.f90`, `tr/tr_state.h`
- TR validation pattern: `tr/tr_api.f90:381-465` (`tr_api_validate`)
- CLAUDE.md (pre-push gate, equivalence test): `/Users/k-yoshimi/Dropbox/cursor/task/CLAUDE.md`
