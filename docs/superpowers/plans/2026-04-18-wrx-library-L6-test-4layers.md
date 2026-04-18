# WRX ライブラリ化 Phase L-6: テスト 4 層実装計画

**位置:** `docs/superpowers/plans/2026-04-18-wrx-library-L6-test-4layers.md`
**実装スパン:** 1〜2 週
**前提:** L-5 完了（`python/wrxlib/` パッケージ・基本 unittest 通過）
**目標:** tr Phase L-6 と同じ 4 層テスト（等価性 / C ABI / Python wrapper / sweep smoke）を wrx 用に実装。

## テスト 4 層設計

| Layer | 目的 | 比較対象 | 場所 |
|---|---|---|---|
| 1: 等価性 | wrxlib 経由結果が既存 `wrx` バイナリと数値一致 | `wrx` バイナリ + `WRX_REGRESS_DUMP=1` (L-0 で導入) | `test_run/` |
| 2: C ABI 直叩き | `tr` 同等の C smoke (init→run→get_state→finalize) | exit code 0 + 出力範囲 | `wrx/tests/c_smoke/` |
| 3: Python wrapper | `WrxLib` の挙動（既に L-5 で骨格） | unittest 単位 | `python/wrxlib/tests/` |
| 4: Sweep smoke | パラメータスイープでクラッシュしない | exit code 0 全 OK | `python/wrxlib/tests/` (notebook 化は L-7) |

## Task 1: Layer 1 — 等価性テスト追加

`test_run/test_definitions.conf` に L-0 で追加した wrx ケース（`wrx_test001` 等）を Python 経由で再走させ、`wrxlib` 出力と既存 `wrx` バイナリ baseline を比較。

`test_run/scripts/check_regression.sh` は既に `--schema wr` を持つ（wr 用）。wrx 用は既存スキーマを再利用可能（L-0 で確認済み）。

新規追加:
- `test_run/scripts/run_wrxlib_regression.py`：`wrxlib` で同入力ケースを走らせて `metrics.json` 生成、baseline と比較
- `run_tests.sh` に `--mode={native,python}` 引数を追加（tr Phase L-6 と同じパターン）

完了基準:
- [ ] `./run_tests.sh wrx_test001 --mode=python` が `1e-10` tolerance で PASS

## Task 2: Layer 2 — C ABI 直叩きスモーク

`wrx/tests/c_smoke/wrx_smoke.c` を新規作成。`wrx_init`→`wrx_set_param("NRAYMAX", 4)`→`wrx_run(0)`→`wrx_get_state("pwr_profile", buf, 101)`→`wrx_finalize` を呼んで exit 0 を確認。

ビルド:
```makefile
wrx/tests/c_smoke/wrx_smoke: wrx_smoke.c ../libwrxapi.so
	$(CC) -o $@ $< -L../. -lwrxapi -Wl,-rpath,$(PWD)/wrx
```

完了基準:
- [ ] `./wrx/tests/c_smoke/wrx_smoke` が exit 0
- [ ] `pwr_profile` の sum が正の有限値

## Task 3: Layer 3 — Python wrapper unittest 拡充

L-5 の最低 3 件に加えて以下を追加:

- `test_set_get_roundtrip.py`: `set_param('NRAYMAX', N)` 後に `get_state('NRAYMAX', 1)` で N が読み戻せる
- `test_run_produces_state.py`: `run()` 後に `pwr_profile` 等の主要 state がゼロ全埋めでない
- `test_error_codes.py`: 未知 param 名で `set_param` → `WrxError` raise、`code == ErrorCode.UNKNOWN_PARAM`
- `test_finalize_idempotent.py`: 二重 `finalize()` で例外にならない（state 戻し）
- `test_init_failure_recovery.py`: `init` 失敗時に `_initialized` が False のまま

完了基準:
- [ ] `python -m unittest discover python/wrxlib/tests -v` 全 PASS
- [ ] テスト件数 13 件以上（L-5 の 3 件 + Layer 3 で 10+ 件追加）

## Task 4: Layer 4 — Sweep smoke

`python/wrxlib/tests/test_sweep_smoke.py` を追加。3×3 程度の小さい param grid でループ実行、各反復で:
- init→set_param→run→get_state→finalize が exit 0
- crash しない
- timeout 60 秒以内

```python
import unittest
from wrxlib import WrxLib

class TestSweepSmoke(unittest.TestCase):
    def test_3x3_sweep(self):
        for nray in (4, 8, 16):
            for power in (0.5, 1.0, 2.0):
                with WrxLib() as w:
                    w.set_param('NRAYMAX', nray)
                    w.set_param('PWAVE', power)
                    w.run()
                    s = w.get_state('pwr_profile', 101)
                    self.assertGreater(float(s.sum()), 0.0)
```

完了基準:
- [ ] sweep 9 ケース全 PASS
- [ ] 全 sweep 完了時間 < 5 分（環境依存だが目安）

## Task 5: `run_tests.sh` 統合

L-0 で wrx を `run_tests.sh` 対象に追加済み。本フェーズで Python モードを追加:

```bash
./run_tests.sh wrx_test001                # native (既存 wrx バイナリ)
./run_tests.sh wrx_test001 --mode=python  # wrxlib 経由
```

両モードで `metrics.json` が baseline と一致することを CI で必須化。

## Task 6: CI 統合

`.github/workflows/test.yml` に wrx native + python モード両方を追加（既存 tr/fp と並列）。

## 完了基準（フェーズ全体）
- [ ] Layer 1〜4 全テストが `develop` で PASS
- [ ] `wrxlib` 経由結果が既存 `wrx` バイナリと `1e-10` 以内一致
- [ ] sweep smoke 9 ケース PASS
- [ ] CI に組み込まれる

## 撤退条件
- Layer 1 で数値乖離 > 1e-6 → L-2 (C ABI) で global state リセット漏れ → L-2 設計に戻る
- sweep でセグフォ多発 → L-4 (PIC build) でアロケーション再現性問題 → L-4 設計に戻る

## 依存
- L-5 完了（`wrxlib` パッケージ）
- L-0 完了（baseline 存在）
- `test_run/scripts/run_tests.sh` Python モード対応（tr L-6 で先行整備されている前提）
