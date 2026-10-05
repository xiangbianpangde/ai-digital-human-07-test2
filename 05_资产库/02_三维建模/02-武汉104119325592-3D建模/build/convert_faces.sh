#!/bin/bash
set -e
SRC="../武汉104119325592-房源资料/03-完整VR素材/faces"
OUT="raw/faces"
n=0
for f in "$SRC"/*.avif; do
  b=$(basename "$f" .avif)
  [ -s "$OUT/$b.png" ] && continue
  sips -s format png "$f" --out "$OUT/$b.png" >/dev/null 2>&1
  n=$((n+1))
done
echo "converted $n new files; total: $(ls "$OUT"/*.png | wc -l)"
