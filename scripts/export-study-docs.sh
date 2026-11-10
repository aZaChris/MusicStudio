#!/usr/bin/env bash
# Copy the mobile app's Italian study docs to the owner's NotebookLM folder.
#
# Usage:  scripts/export-study-docs.sh [DEST]
#   DEST defaults to $STUDY_DOCS_DIR, then to the Windows folder used on the main machine.
# Layout: "Mobile/" (cross-phase docs) and "Mobile - Fase N/" (docs born in phase N), next to
# the backend's folders. Copies only; prints NEW / UPDATED for each changed file.
set -euo pipefail

DEST="${1:-${STUDY_DOCS_DIR:-/mnt/c/Users/Christian/Documents/doc_music_studio}}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/docs/learning"

if [ ! -d "$(dirname "$DEST")" ]; then
  echo "Parent of destination not found: $DEST" >&2
  exit 1
fi

copy() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ ! -f "$dst" ]; then echo "NEW      ${dst#"$DEST"/}"
  elif ! cmp -s "$src" "$dst"; then echo "UPDATED  ${dst#"$DEST"/}"; fi
  cp "$src" "$dst"
}

# Cross-phase
for f in 00-indice.md glossario.md colloquio/domande-e-risposte.md concetti/sicurezza-mobile-owasp.md; do
  copy "$SRC/$f" "$DEST/Mobile/$(basename "$f")"
done

# Phase 1: parity on the Django API
P="Mobile - Fase 1 - Parita su Django"
copy "$SRC/audit-iniziale.md" "$DEST/$P/audit-iniziale.md"
copy "$SRC/verifica-end-to-end.md" "$DEST/$P/verifica-end-to-end.md"
for c in client-api-generato-dal-contratto sessione-jwt-nel-client stato-del-server-con-react-query \
         test-di-un-app-react-native; do
  copy "$SRC/concetti/$c.md" "$DEST/$P/Concetti/$c.md"
done
for adr in "$SRC"/adr/ADR-M00[1-5]-*.md; do
  copy "$adr" "$DEST/$P/ADR/$(basename "$adr")"
done

echo "Done: $(find "$DEST" -path '*Mobile*' -type f -name '*.md' | wc -l) mobile files in $DEST"
