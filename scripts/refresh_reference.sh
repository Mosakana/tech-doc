#!/usr/bin/env bash
# refresh_reference.sh — re-snapshot ONE reference doc from its source.
#
# Keeps our curated frontmatter (title / type / source_project / source_path /
# snapshot_reason / aliases / tags), replaces the BODY with the current source
# content, and bumps snapshot_date + source_sha256. Mechanical → ~0 LLM tokens.
#
# Usage:  bash refresh_reference.sh "$KNOWLEDGE_VAULT/reference/<project>/<doc>.md"
#
# AFTER running: scan links once. If the new source body brought in relative links
# to docs we've snapshotted (rule 7 in VAULT_STRUCTURE.md), re-point them to [[slug]]
# — that one re-edit is the only part that may cost tokens, and only for changed docs.
set -euo pipefail
snap="${1:?usage: refresh_reference.sh <snapshot.md>}"
[ -f "$snap" ] || { echo "快照不存在: $snap" >&2; exit 1; }

src=$(sed -n 's/^source_path:[[:space:]]*//p' "$snap" | head -1)
[ -n "$src" ] && [ -f "$src" ] || { echo "源文件无效: ${src:-<空>}" >&2; exit 1; }

sha=$(sha256sum "$src" | cut -d' ' -f1)
today=$(date +%F)
tmp=$(mktemp)

# Emit the (updated) frontmatter only: preserve every field, set snapshot_date +
# source_sha256, then stop at the closing --- (body is replaced below).
awk -v sha="$sha" -v today="$today" '
  NR==1 && $0=="---"{print; infm=1; next}
  infm && $0=="---"{
    if(!sd) print "snapshot_date: " today;
    if(!sh) print "source_sha256: " sha;
    print "---"; exit
  }
  infm && /^snapshot_date:/{print "snapshot_date: " today; sd=1; next}
  infm && /^source_sha256:/{print "source_sha256: " sha; sh=1; next}
  infm{print; next}
' "$snap" > "$tmp"

printf '\n' >> "$tmp"
cat "$src" >> "$tmp"
mv "$tmp" "$snap"

echo "refreshed: $snap"
echo "  source : $src"
echo "  sha    : ${sha:0:16}…    date: $today"
echo "  next   : 跑链接扫描;新正文若带指向 vault 内文档的相对链接,按 rule-7 改成 [[slug]]"
