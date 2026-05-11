# セッション引き継ぎ — 2026-04-28 (夜版 / merge 完了)

このファイルは 2026-04-28 セッション (L-7a 全 5 PR merge 完了時点) からの引き継ぎ情報です. 新セッション開始時には先に過去 handoff (`.claude/handoff-2026-04-28.md`, `.claude/handoff-2026-04-28-evening.md`) を読み, 続いて本ファイルを読んでください.

## 大局

プロジェクト: **TASK プラズマライブラリの Python ラッパー / MCP サーバ化 + Sphinx マニュアル全モジュール展開**

L-7a シリーズ完全完了. **5 PR が origin/chore/pre-push-hook-worktree-compat に直列 merge 済**.

```
master (置いていかれている, 759+5=764 commits behind chore)
  ↑
caa57ad0 docs: portal:common-architecture {ref} cleanup (#182)
5b994217 docs: plan sync + CLAUDE.md Codex 段落 (#180)
eee67a70 feat(tot_mcp): run_pipeline tool + docs (L-7a Phase 3) (#181)
05d7ce91 test(totlib): fp→tr equivalence test (L-7a Phase 2) (#179)
5a79b5db feat(totlib): TotPipeline foundation (L-7a Phase 1) (#178)
52481e9f chore(handoff): record session state at 2026-04-28 for resumption
... master まで 759 commits ...
```

## 完了済み (本セッション 2026-04-28 夜)

### 5 PR 順次マージ

| PR | 内容 | Squash commit | テスト数 |
|---|---|---|---|
| #178 | L-7a Phase 1 — TotPipeline foundation + Bugbot 全 7 件 fix | `5a79b5db` | 96 mock |
| #179 | L-7a Phase 2 — compute_rjt_volint + 1e-10 等価性テスト | `05d7ce91` | +6 (=102) |
| #181 | L-7a Phase 3 — run_pipeline MCP tool + 4 docs | `eee67a70` | +tot_mcp 8 (=193) |
| #180 | docs: plan sync + CLAUDE.md Codex 段落追加 | `5b994217` | doc-only |
| #182 | docs: portal:common-architecture {ref} 30 件除去 + warning suppression | `caa57ad0` | doc-only |

### マージ手順 (再現用)

各 PR 順次:

1. **#178** (Phase 1, base=chore) — squash merge
2. **#179** (Phase 2) — base を chore に edit, `git rebase --onto origin/chore/... 941f3533 feat/totlib-pipeline-phase2` で 6 commits replay → force-push → squash merge
3. **#181** (Phase 3) — 同様に rebase + base edit + force-push + squash merge
4. **#180** (docs) — 1 commit を `--onto` rebase + force-push + merge
5. **#182** (portal) — 3 commits を `--onto` rebase + force-push + merge

**重要なポイント:** stacked PR を順次 squash merge する場合, 各 PR の base を merge 後に `chore` に切替えて, 該当 PR の commits を新 chore tip に rebase する必要があります. 直接 merge すると "already merged" 判定 + commit hash 不一致で `mergeStateStatus=DIRTY` `mergeable=CONFLICTING` になります.

### Bugbot 対応の詳細

PR #178 で計 **7 件** の Bugbot 指摘を 2 ラウンドで処理:

**Round 1 (commit `e1e5a378`):**
- `_import_module_error` dead code 削除
- `close()` ExceptionGroup 化 (multi-error visibility)
- `set_param` `_params` の型乖離 fix

**Round 2 (commit `29285f27`):**
- `to_dict()` defensive copy
- `_validate_steps` list 受容
- `set_param` bool 拒否 (silent coercion 防止)
- ExceptionGroup Python 3.10 compat shim (`exceptiongroup` backport optional)

PR #179, #181, #180 はすべて Bugbot 初回 "no new issues". PR #182 は base lineage 由来の false positive (PR #178 で fix 済の dead code を見ていた).

### 確立した運用パターン

- **Subagent-driven development**: 25+ subagent dispatch (implementer + spec reviewer + code quality reviewer + codex reviewer)
- **2-stage review**: spec compliance review が先, code quality review が後 (skill 規定通り)
- **Pre-push gate**: code-reviewer + codex:codex-rescue 並列起動 (CLAUDE.md 規約)
- **CLAUDE.md Codex review 段落** (PR #180): 既存の規約を明文化
- **Stacked PR rebase pattern**: `git rebase --onto <new_base> <old_base_tip> <feature>` で clean replay

## 環境セットアップ (新セッションで再現する場合)

```bash
# 一度だけ:
scripts/setup.sh
# → ../bpsd clone, lib*_pic.a / lib*api.so 全ビルド

# Python パス:
export PYTHONPATH=/Users/k-yoshimi/Dropbox/cursor/task/python:$PYTHONPATH

# pytest 実行 (canonical CI flags, totlib + tot_mcp):
PYTHONPATH=python python3 -m pytest \
  --forked --timeout=120 --timeout-method=signal \
  python/totlib/tests/ python/mcp-servers/tot_mcp/tests/ 2>&1 | tail -10
# 期待: ~197 passed, ~3 skipped (test_pipeline_equiv は lib*.so 必要)

# Sphinx build (全モジュール+portal, 2-pass で warning ゼロ):
cd docs/sphinx
for lang in en ja; do sphinx-build -b html portal/$lang _build/portal/$lang ; done
for m in tr eq ti fp wr wrx tot; do
  for lang in en ja; do
    sphinx-build -b html -W --keep-going modules/$m/$lang _build/$m/$lang
  done
done
for lang in en ja; do sphinx-build -b html -W --keep-going portal/$lang _build/portal/$lang ; done

# REVIEW_OK marker:
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"

# Codex CLI 確認:
node "/Users/k-yoshimi/.claude/plugins/cache/openai-codex/codex/1.0.4/scripts/codex-companion.mjs" setup --json
# 期待: ready: true, codex available, auth loggedIn: true

# gh auth (PR 操作用):
# GITHUB_TOKEN env var に invalid token が居座っているので, env -u GITHUB_TOKEN で gh を呼ぶ
env -u GITHUB_TOKEN gh pr view 178
```

## 残タスク (handoff §低優先 残)

L-7a が完成したので, 次は:

### 中優先

#### L-7b (将来) — profile-level coupling

L-7a の skeleton coupling (`tr.PLHCD` 無次元) を proper scalar に置換し, profile coupling を BPSD broker 経由で実装:

1. **Fortran 側**: `tr/tr_param_registry.f90` に `EXTERNAL_DRIVEN_I` (MA 単位の current drive scalar) を追加
2. **Python 側**: `python/totlib/pipeline.py` の `COUPLING_RULES[("fp","tr")]` を `dst_param="EXTERNAL_DRIVEN_I"` + `transform=lambda v: v * 1e-6` に更新 (skeleton caveat 撤去)
3. **profile coupling**: BPSD ABI 経由で wr → fp/tr (RF deposition profile), eq → tr (q-profile) を coupling
4. **declarative API**: `tot.couple(src, dst)` の宣言的 coupling 定義 (現状は `COUPLING_RULES` dict の hardcode)

L-7b の brainstorm がまだ. 着手前に新 spec/plan が必要.

### 低優先 (handoff 午前版から継続)

- ti/fp/wr/wrx/tot quickstart notebook
- MCP bundle (全 mcp-server を 1 wrapper にまとめる)
- master へ chore branch 統合 (PR base 整理) — 759+ commits の長期スタックを解消

### 中優先 (今日着手しなかった handoff §中優先 残)

- master ブランチ整理 (`chore/pre-push-hook-worktree-compat` を master に merge or rebase)

## 重要な設計上の注意点 (新セッションで尊重すべき)

### A. master との関係

`chore/pre-push-hook-worktree-compat` は master の **764 commits 先**. 本ブランチが事実上の "main line" として機能している. master へ統合する PR を出すか, このまま運用継続するかは要判断.

### B. ExceptionGroup compat shim の意図

`python/totlib/pipeline.py` 冒頭の `try: ExceptionGroup; except NameError` は Python 3.10 互換のため. `tot_mcp/pyproject.toml` の `requires-python = ">=3.10"` 宣言と整合.

完全な互換性のためには `exceptiongroup` PyPI パッケージを `tot_mcp/pyproject.toml` の deps に `'exceptiongroup; python_version < "3.11"'` で追加する必要がある (本セッションでは未対応, 別 follow-up).

CI matrix は 3.11/3.13 のみなので 3.10 では走らないが, ユーザーが手動で 3.10 に install したら fallback path (errors[0] のみ raise) になる.

### C. `set_param` bool 拒否

`pipe.set_param("fp:E0", True)` は `TotPipelineCouplingError` で拒否される. Python の bool は int subclass なので silent float() 化を防ぐため. 数値が必要なら `True` ではなく `1.0` を明示.

### D. portal:common-architecture {ref}

`docs/sphinx/modules/*/{en,ja}/*.md` 内の `{ref}`<text> <portal:common-architecture>`` は **すべて relative-path Markdown link に置換済**: `[<text>](../../../portal/<lang>/common/architecture.md)`. 

各モジュールの `conf.py` に `suppress_warnings = ["myst.xref_missing"]` を追加 (cross-Sphinx-project link が myst.xref_missing 出すため). portal の本番 URL が確定したら `intersphinx_mapping` の URL を直して suppression を撤去 (TODO コメント記載済み).

### E. Sphinx build 順序

Portal は modules の `objects.inv` を intersphinx で参照する. clean build (`rm -rf _build`) では:
1. portal first → 失敗 (modules .inv 不在 で 7 warning, `-W` で error)
2. modules first → 成功 (portal .inv は遅延参照)
3. portal again → 成功 (modules .inv 揃った)

`make html` の依存順序が逆なので, `make modules` 先 → `make portal-en portal-ja` 後 が正解. 本セッションでは Makefile 修正なし (out of scope).

### F. CLAUDE.md Pre-push gate

PR #180 で **Codex review を ステップ 3 として明文化**:

```
1. Local test (--forked --timeout=120 --timeout-method=signal)
2. Code review (superpowers:code-reviewer)
3. Codex independent review (codex:codex-rescue) ← NEW
4. REVIEW_OK marker
```

両 reviewer 並列起動 (single message に複数 Agent tool call). HIGH/MED 指摘を user に共有してから push.

### G. 手元のみ (前々セッションからの残留物 — 触っていない)

- `python/mcp-servers/tr_mcp/setup_cli.py` (新規 untracked)
- `python/mcp-servers/tr_mcp/tests/test_setup_cli.py` (新規 untracked)
- `python/mcp-servers/tr_mcp/README.md` (M)
- `python/mcp-servers/tr_mcp/server.py` (M)
- `python/trlib/CMakeLists.txt` (新規 untracked)
- `tr/libtrapi.so` (build artifact, untracked)
- `txnew/docs/_build/` (sphinx build artifact, untracked)
- `docs/slides/` (前セッションの slides 生成 script + pptx — 手元のみ)
- `.worktrees/` (worktree operations 残骸)

これらは本セッションでも触れていない.

## 次に何をするか (推奨)

新セッション開始時の最短ルート:

1. このファイル (`.claude/handoff-2026-04-28-night.md`) を読む
2. `git fetch origin && git log --oneline -10` で origin/chore tip = `caa57ad0` を確認
3. 全テスト通過確認:
   ```bash
   PYTHONPATH=python python3 -m pytest --forked --timeout=120 --timeout-method=signal \
     python/totlib/tests/ python/mcp-servers/tot_mcp/tests/ 2>&1 | tail -5
   ```
   期待: 197 passed, 3 skipped
4. **次タスク選択**:
   - **L-7b (中優先)**: brainstorm 開始 → spec → plan → 実装. EXTERNAL_DRIVEN_I scalar 追加から
   - **master 統合 (中優先)**: `chore` を master に merge or PR 化
   - **低優先**: notebook, MCP bundle 等

## 次セッション開始用プロンプト例

```
前回のセッション (2026-04-28 夜, L-7a 全 5 PR merge 完了) からの引き継ぎです.
最初に `.claude/handoff-2026-04-28-night.md` を読んでから始めてください.

プロジェクト状態:
- L-7a シリーズ完了 (PR #178/#179/#181/#180/#182 すべて merge 済).
- origin/chore/pre-push-hook-worktree-compat HEAD = caa57ad0
- master との関係: 764 commits behind master (chore が事実上の main)

優先度順の残タスク:
1. L-7b — profile coupling + EXTERNAL_DRIVEN_I scalar (brainstorm 必要)
2. master 統合 (chore を main に統合する PR)
3. 低優先: ti/fp/wr/wrx/tot quickstart notebook, MCP bundle

L-7b に着手する場合は brainstorming skill から start. master 統合の場合は
master との diff を確認して進め方を相談.
```

(優先度を変えたい場合は上のプロンプトを修正.)
