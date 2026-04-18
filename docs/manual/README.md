# TASK プラズマ輸送ライブラリ化プロジェクト マニュアル (日本語)

本ディレクトリには, tr / ti / wr / wrx / fp 5 モジュールの
ライブラリ化 (Phase L-0 〜 L-7) をまとめた日本語マニュアル兼報告書が
含まれる.

## 成果物

| ファイル | 内容 |
|----------|------|
| `task-library-manual.tex` | 正本の LaTeX ソース (xeCJK + tcolorbox + TikZ) |
| `task-library-manual.pdf` | 同梱の生成済み PDF (A4, 52 ページ) |
| `_render_pdf.py` | TeX 不在環境向けの matplotlib フォールバック |

## 推奨ビルド (TeX Live 利用可能時)

```bash
cd docs/manual
xelatex -interaction=nonstopmode task-library-manual.tex
xelatex -interaction=nonstopmode task-library-manual.tex   # 相互参照
```

TeX Live のインストールは:

```bash
sudo apt-get install -y texlive-xetex texlive-lang-japanese \
     texlive-latex-extra fonts-noto-cjk fonts-noto-cjk-extra \
     fonts-dejavu-core
```

## フォールバックビルド (本リポジトリに同梱済み PDF の生成方法)

本マニュアルを書いた環境には xelatex が入っていなかったため,
PDF は `_render_pdf.py` (matplotlib の `PdfPages`, Noto Serif CJK JP)
で生成している. 同じ環境で再生成したい場合:

```bash
python3 docs/manual/_render_pdf.py
```

matplotlib と Noto CJK フォントが必要.
整形精度は xelatex より劣るが, 検索可能な PDF (テキスト埋め込み) である.

## 使用フォント

- 本文 (和文): Noto Serif CJK JP (Regular / Bold)
- 見出し: Noto Sans CJK JP (Bold)
- コード: Noto Sans Mono CJK JP (TeX 版), Noto Sans CJK JP (matplotlib 版)
- 欧文モノスペース: DejaVu Sans Mono

## 生成物の配置

相互参照などで生成される中間ファイル (`*.aux`, `*.log`, `*.toc`,
`*.out`, `*.fls`, `*.fdb_latexmk`, `*.synctex.gz`) は
リポジトリ root の `.gitignore` で除外する.
