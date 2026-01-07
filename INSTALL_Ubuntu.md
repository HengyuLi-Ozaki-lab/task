# TASK インストールマニュアル (Ubuntu)

本マニュアルはUbuntu環境でのTASKコードのインストール手順を説明します。

## 1. 動作環境

- OS: Ubuntu 20.04 / 22.04 LTS (64bit)
- 必要なディスク容量: 約500MB

## 2. 必要なパッケージのインストール

```bash
sudo apt-get update
sudo apt-get install -y gfortran git xorg-dev xterm cmake python3 mpich
```

### パッケージの確認

```bash
which gfortran git cmake python3 mpirun
gfortran --version
```

## 3. ソースコードの取得

作業ディレクトリを作成し、3つのリポジトリをクローンします。

```bash
mkdir -p ~/program
cd ~/program

# TASKとライブラリのクローン
git clone https://bpsi.nucleng.kyoto-u.ac.jp/pub/git/task.git
git clone https://bpsi.nucleng.kyoto-u.ac.jp/pub/git/gsaf.git
git clone https://bpsi.nucleng.kyoto-u.ac.jp/pub/git/bpsd.git

# developブランチに切り替え
cd task
git checkout -t -b develop origin/develop
cd ..
```

## 4. GSAFグラフィックライブラリのインストール

### 4.1 Makefile.archの設定

```bash
cd ~/program/gsaf/src
cp ../arch/ubuntu-gfortran64-static/Makefile.arch .
```

Makefile.archを編集し、ホームディレクトリにインストールするよう設定します：

```bash
# Makefile.arch を編集
# 以下の行をコメントアウト:
#BINPATH=/usr/local/bin
#LIBPATH=/usr/local/lib

# 以下の行を有効化:
HOMEPATH=$(HOME)
BINPATH=$(HOMEPATH)/bin
LIBPATH=$(HOMEPATH)/lib
```

### 4.2 ビルドとインストール

```bash
# インストール先ディレクトリの作成
mkdir -p ~/bin ~/lib

# ビルド
cd ~/program/gsaf/src
make

# インストール
make install
```

※初回インストール時のrmエラーは無視して問題ありません。

## 5. TASKの設定

### 5.1 make.headerの設定

```bash
cd ~/program/task
cp make.header.org make.header
```

make.headerを編集し、Linux gfortran (64bit)用の設定を有効にします：

```bash
# make.header を編集

# 30-31行目をコメントアウト:
#GFLIBS=-L/usr/local/lib -lg3d -lgsp -lgdp -L/usr/X11R6/lib -lX11
#GLLIBS=-L/usr/local/lib -lgsgl

# 84-94行目を以下のように変更（コメントを外してパスを修正）:
## for linux gfortran (64bit) lib
GFLIBS=-L$(HOME)/lib -lg3d-gfc64 -lgsp-gfc64 -lgdp-gfc64  -L/usr/lib/x86_64-linux-gnu -lX11
OFLAGS = -g -O3 -m64 -std=legacy
DFLAGS = -g -m64 -fbounds-check -ffpe-trap=invalid,zero,overflow -fbacktrace -fcheck=all -std=legacy
FCFIXED = gfortran -ffixed-form
FCFREE = gfortran -ffree-form
MOD = mod
MODDIR = -Jmod
LD=ld
LDFLAGS=-r -o
FPP=
```

## 6. ライブラリのコンパイル

### 6.1 BPSDライブラリ

```bash
cd ~/program/bpsd
make
```

### 6.2 TASKライブラリ

```bash
cd ~/program/task/lib
make
```

### 6.3 行列ソルバライブラリ (mtxp)

```bash
cd ~/program/task/mtxp
cp make.mtxp.nompi make.mtxp
make
```

※MPI並列計算を使用する場合は `make.mtxp.mpi` を使用してください。

## 7. モジュールのコンパイルと動作確認

例としてeq（平衡計算）モジュールをコンパイルします：

```bash
cd ~/program/task/eq
make
```

### 動作確認

```bash
./eq
```

プロンプトが表示されたら：
1. `5` を入力（グラフィックウィンドウサイズ）
2. `c` を入力（続行）
3. `r` を入力（実行）
4. `q` を入力（終了）

## 8. 一括テストの実行

インストール後、各モジュールの動作を一括でテストできます。

### 8.1 追加モジュールのビルド（オプション）

eq以外のモジュールもテストする場合は、先にビルドしてください：

```bash
cd ~/program/task/pl && make    # プラズマプロファイル（tr, fpの依存）
cd ~/program/task/tr && make    # 輸送計算
cd ~/program/task/fp && make    # フォッカープランク
cd ~/program/task/tx && make    # 1次元輸送
```

### 8.2 テストの実行

```bash
cd ~/program/task/test_run
./run_tests.sh
```

### 8.3 テストスクリプトのオプション

```bash
# 全テスト実行
./run_tests.sh

# テスト一覧を表示
./run_tests.sh -l

# 特定テストのみ実行
./run_tests.sh eq_iter01 tx_std

# 詳細出力
./run_tests.sh -v

# タイムアウト変更（デフォルト60秒）
./run_tests.sh -t 120

# テスト後にクリーンアップ
./run_tests.sh -c

# ヘルプ表示
./run_tests.sh -h
```

### 8.4 利用可能なテスト

| テスト名 | モジュール | 説明 |
|---------|-----------|------|
| eq_iter01 | eq | ITER平衡計算 |
| eq_jt60 | eq | JT-60平衡計算 |
| eq_tst2 | eq | TST-2平衡計算 |
| tr_iter01 | tr | ITER輸送計算（短縮版） |
| tx_std | tx | 標準1D輸送計算 |

### 8.5 テスト定義の追加

`test_run/test_definitions.conf`にテストを追加できます。形式：

```
テスト名:モジュール:入力ファイル:依存テスト:タイムアウト:説明
```

例：
```
eq_new:eq:in/eq.new.in:none:60:New equilibrium test
tr_new:tr:@inputs/tr_new.in:eq_iter01:120:New transport test
```

- 入力ファイルパス: `in/file.in` はモジュールディレクトリから、`@inputs/file.in` は test_run/inputs/ から
- 依存テスト: 先に実行が必要なテスト（`none`で依存なし）

### 8.6 テスト結果の確認

テスト出力は `test_run/test_output/` に保存されます：

```bash
# 全ログ確認
cat test_run/test_output/*/output.log

# 特定テストのログ
cat test_run/test_output/eq_iter01/output.log
```

## 9. 環境変数の設定

`~/.bashrc` に以下を追加します：

```bash
export PATH=$HOME/bin:$PATH
```

設定を反映：

```bash
source ~/.bashrc
```

## 10. ディレクトリ構成

インストール後のディレクトリ構成：

```
~/program/
├── task/          # TASKメインコード
│   ├── eq/        # 平衡計算モジュール
│   ├── tr/        # 輸送計算モジュール
│   ├── fp/        # フォッカープランクモジュール
│   ├── tx/        # 1次元輸送モジュール
│   ├── lib/       # 共通ライブラリ
│   ├── mtxp/      # 行列ソルバ
│   ├── pl/        # プラズマプロファイル
│   ├── test_run/  # テストスクリプト
│   └── ...        # その他のモジュール
├── gsaf/          # グラフィックライブラリソース
└── bpsd/          # データインターフェースライブラリ

~/bin/             # GSAFコマンド群
~/lib/             # GSAFライブラリ
```

## 11. トラブルシューティング

### X11関連のエラー

グラフィック機能を使用する場合は、X11環境（xterm等）から実行してください。

```bash
xterm &
# xterm内で
cd ~/program/task/eq
./eq
```

### ライブラリが見つからないエラー

`~/lib` にライブラリがインストールされているか確認：

```bash
ls ~/lib/*.a
```

### コンパイルエラー

make.headerの設定を確認し、パスが正しいことを確認してください。

## 参考情報

- 公式サイト: https://bpsi.nucleng.kyoto-u.ac.jp/task/
- 詳細なドキュメント: `~/program/task/doc/how_to_install.pdf`
- 実行方法: `~/program/task/doc/how_to_run.pdf`
