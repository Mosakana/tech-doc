#!/usr/bin/env bash
# check_references.sh — detect which reference snapshots are STALE vs their source.
#
# Purely shell: it hashes each source file and compares to the source_sha256 stored
# in the snapshot's frontmatter. The agent spends ~0 tokens on unchanged files — it
# only needs to act on the short list this prints. Scales to a large reference/ where
# few docs actually change.
#
# Usage:  bash check_references.sh [REFERENCE_DIR]
#   REFERENCE_DIR defaults to ${KNOWLEDGE_VAULT:-~/Knowledge}/reference
# Output rows (only actionable ones are listed; unchanged are just counted):
#   CHANGED        <rel>   <- <source>     source content differs from snapshot
#   MISSING-SRC    <rel>   <- <source>     source file no longer exists (moved/deleted?)
#   NO-HASH        <rel>                    snapshot predates hashing — run refresh to backfill
#   NO-PROVENANCE  <rel>                    no source_path frontmatter — not a managed snapshot
set -euo pipefail
REF_DIR="${1:-${KNOWLEDGE_VAULT:-$HOME/Knowledge}/reference}"
[ -d "$REF_DIR" ] || { echo "reference dir not found: $REF_DIR" >&2; exit 1; }

n_changed=0 n_ok=0 n_missing=0 n_nohash=0 n_noprov=0
while IFS= read -r snap; do
  grep -q '^type: moc' "$snap" && continue   # skip the reference MOC / any index note
  src=$(sed -n 's/^source_path:[[:space:]]*//p' "$snap" | head -1)
  stored=$(sed -n 's/^source_sha256:[[:space:]]*//p' "$snap" | head -1)
  rel=${snap#"$REF_DIR"/}
  if [ -z "$src" ]; then echo "NO-PROVENANCE  $rel"; n_noprov=$((n_noprov+1)); continue; fi
  if [ ! -f "$src" ]; then echo "MISSING-SRC    $rel   <- $src"; n_missing=$((n_missing+1)); continue; fi
  cur=$(sha256sum "$src" | cut -d' ' -f1)
  if [ -z "$stored" ]; then
    echo "NO-HASH        $rel   (run refresh_reference.sh to backfill)"; n_nohash=$((n_nohash+1))
  elif [ "$cur" != "$stored" ]; then
    echo "CHANGED        $rel   <- $src"; n_changed=$((n_changed+1))
  else
    n_ok=$((n_ok+1))
  fi
done < <(find "$REF_DIR" -name '*.md' | sort)

echo "---"
echo "changed=$n_changed missing=$n_missing nohash=$n_nohash no-prov=$n_noprov unchanged=$n_ok"
echo "(未列出的 = 未改动。对每个 CHANGED/NO-HASH 跑:  refresh_reference.sh <reference/...>)"
