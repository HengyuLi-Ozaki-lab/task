#!/bin/bash
# check_dealloc.sh - Fortran ALLOCATE/DEALLOCATE 対応チェックスクリプト
#
# 使い方:
#   ./check_dealloc.sh [ディレクトリ]
#
# 指定ディレクトリ(デフォルト: カレント)配下の .f90 ファイルを走査し、
# ALLOCATE に対応する DEALLOCATE が同一ディレクトリ内に存在しない
# 変数を検出する。
#
# 出力例:
#   [MISSING] SPSC  (trcomm.f90:351)
#   [OK]      SPSCT (trcomm.f90:367 -> trcomm.f90:542)

TARGET_DIR="${1:-.}"
TOTAL_ALLOC=0
TOTAL_MISSING=0
TOTAL_OK=0

# 色付け (端末の場合)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

echo "=============================================="
echo " Fortran ALLOCATE/DEALLOCATE チェック"
echo " 対象: $TARGET_DIR"
echo "=============================================="
echo ""

# .f90 ファイルから ALLOCATE 文を抽出
# - DEALLOCATE 行は除外
# - コメント行は除外
# - STAT= や IERR は除外
tmpfile=$(mktemp)

grep -rn "ALLOCATE(" "$TARGET_DIR" --include="*.f90" --include="*.f" 2>/dev/null \
  | grep -vi "DEALLOCATE" \
  | grep -v "^[^:]*:[^:]*:[ ]*!" \
  | grep -v "^[^:]*:[^:]*:.*!.*ALLOCATE" \
  > "$tmpfile"

# 各 ALLOCATE 行から変数名を抽出してチェック
while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    lineno=$(echo "$line" | cut -d: -f2)
    content=$(echo "$line" | cut -d: -f3-)

    # ALLOCATE( の後の変数名を抽出 (複数変数の場合はカンマ区切り)
    # ALLOCATE(VAR1(N), VAR2(M), STAT=IERR) のパターンに対応
    vars=$(echo "$content" \
      | sed 's/.*ALLOCATE(//I' \
      | sed 's/STAT=.*//I' \
      | sed 's/)$//' \
      | tr ',' '\n' \
      | sed 's/(.*//' \
      | sed 's/^[ \t]*//' \
      | sed 's/[ \t]*$//' \
      | grep -v "^$" \
      | grep -v -i "^STAT" \
      | grep -v -i "^IERR")

    relfile=$(echo "$file" | sed "s|^$TARGET_DIR/||")

    for var in $vars; do
        # 変数名のクリーンアップ (余計な括弧等を除去)
        var=$(echo "$var" | sed 's/[()]//g' | sed 's/%.*//')

        # 空や短すぎるものはスキップ
        [ ${#var} -lt 2 ] && continue
        # 数字のみはスキップ
        echo "$var" | grep -q "^[0-9]" && continue

        TOTAL_ALLOC=$((TOTAL_ALLOC + 1))

        # 同一ディレクトリ内で DEALLOCATE を検索
        dir=$(dirname "$file")
        dealloc_match=$(grep -rn "DEALLOCATE.*\b${var}\b" "$dir/" --include="*.f90" --include="*.f" 2>/dev/null | head -1)

        if [ -z "$dealloc_match" ]; then
            printf "${RED}[MISSING]${NC} %-25s (%s:%s)\n" "$var" "$relfile" "$lineno"
            TOTAL_MISSING=$((TOTAL_MISSING + 1))
        else
            dealloc_file=$(echo "$dealloc_match" | cut -d: -f1 | sed "s|^$TARGET_DIR/||")
            dealloc_line=$(echo "$dealloc_match" | cut -d: -f2)
            printf "${GREEN}[OK]${NC}      %-25s (%s:%s -> %s:%s)\n" "$var" "$relfile" "$lineno" "$dealloc_file" "$dealloc_line"
            TOTAL_OK=$((TOTAL_OK + 1))
        fi
    done
done < "$tmpfile"

rm -f "$tmpfile"

echo ""
echo "=============================================="
echo " 結果サマリ"
echo "=============================================="
echo " ALLOCATE 総数:     $TOTAL_ALLOC"
printf " ${GREEN}DEALLOCATE あり:    $TOTAL_OK${NC}\n"
printf " ${RED}DEALLOCATE なし:    $TOTAL_MISSING${NC}\n"

if [ "$TOTAL_ALLOC" -gt 0 ]; then
    rate=$(( (TOTAL_OK * 100) / TOTAL_ALLOC ))
    echo " カバー率:          ${rate}%"
fi
echo "=============================================="

if [ "$TOTAL_MISSING" -gt 0 ]; then
    exit 1
else
    exit 0
fi
