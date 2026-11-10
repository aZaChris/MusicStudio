#!/usr/bin/env bash
# Copy the Italian study docs to the owner's NotebookLM folder, organised by phase.
#
# Usage:  scripts/export-study-docs.sh [DEST]
#   DEST defaults to $STUDY_DOCS_DIR, then to the Windows folder used on the main machine.
#
# Layout produced (see CLAUDE.md, "End of a phase"):
#   00 Generale/                     cross-phase docs, refreshed every phase
#   Fase N - <name>/Concetti/        concept docs born in phase N
#   Fase N - <name>/ADR/             ADRs written in phase N
# Copies only (never moves); prints NEW / UPDATED for each changed file.
# When a phase ends: add its folder name, its concept files and its ADR range below.
set -euo pipefail

DEST="${1:-${STUDY_DOCS_DIR:-/mnt/c/Users/Christian/Documents/doc_music_studio}}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/docs/learning"

if [ ! -d "$(dirname "$DEST")" ]; then
  echo "Parent of destination not found: $DEST" >&2
  echo "Pass a path or set STUDY_DOCS_DIR." >&2
  exit 1
fi

copy() {  # copy SRC_FILE DEST_FILE, reporting what changed
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ ! -f "$dst" ]; then
    echo "NEW      ${dst#"$DEST"/}"
  elif ! cmp -s "$src" "$dst"; then
    echo "UPDATED  ${dst#"$DEST"/}"
  fi
  cp "$src" "$dst"
}

# --- Cross-phase documents ---------------------------------------------------------------
for f in 01-panoramica-architettura.md glossario.md colloquio/domande-e-risposte.md \
         concetti/sicurezza-api-owasp.md; do
  copy "$SRC/$f" "$DEST/00 Generale/$(basename "$f")"
done

# --- Per-phase documents: "folder|concept files (no .md)|first ADR|last ADR" -------------
PHASES=(
  "Fase 1 - Fondamenta|service-layer-e-modular-monolith orm-e-problema-n-piu-1 indici-ed-explain isolamento-tenant-e-bola configurazione-per-ambienti strategia-di-test ci-e-quality-gate docker-e-deploy-con-coolify health-check-e-backup|1|8"
  "Fase 2 - Dominio|exclusion-constraint multi-tenancy permessi-drf openapi-e-contratti|9|12"
  "Fase 3 - Celery e pagamenti|task-celery-idempotenti webhook-idempotenti pagamenti-online-stripe caching|13|17"
  "Fase 4 - Produzione|revoca-token-jwt ip-reale-dietro-proxy log-strutturati-e-sentry backup-off-site-e-restore-drill load-testing|18|22"
  "Web 1 - Portale web|sicurezza-di-una-spa deploy-di-una-spa-con-nginx|23|26"
)

# Knowledge-base cases (real problems solved): cross-phase, refreshed every run
for f in "$SRC"/../knowledge-base/*.md; do
  [ "$(basename "$f")" = README.md ] && continue
  copy "$f" "$DEST/00 Generale/Knowledge base/$(basename "$f")"
done

# Operations docs born in phase 4 (runbook, restore drill record, load-test baseline)
copy "$SRC/../operations/runbook.md" "$DEST/Fase 4 - Produzione/Operazioni/runbook.md"
copy "$SRC/../operations/restore-drill.md" "$DEST/Fase 4 - Produzione/Operazioni/restore-drill.md"
copy "$SRC/../loadtest/2026-11-09/README.md" "$DEST/Fase 4 - Produzione/Operazioni/load-test-2026-11-09.md"

# Web 1 (portale web): its audit and end-to-end record
copy "$SRC/audit-frontend.md" "$DEST/Web 1 - Portale web/audit-frontend.md"
copy "$SRC/verifica-web-end-to-end.md" "$DEST/Web 1 - Portale web/verifica-web-end-to-end.md"

copy "$SRC/audit-iniziale.md" "$DEST/Fase 1 - Fondamenta/audit-iniziale.md"

for phase in "${PHASES[@]}"; do
  IFS='|' read -r folder concepts first last <<< "$phase"
  for c in $concepts; do
    copy "$SRC/concetti/$c.md" "$DEST/$folder/Concetti/$c.md"
  done
  for n in $(seq "$first" "$last"); do
    for adr in "$SRC"/adr/ADR-"$(printf '%03d' "$n")"-*.md; do
      copy "$adr" "$DEST/$folder/ADR/$(basename "$adr")"
    done
  done
done

echo "Done: $(find "$DEST" -type f -name '*.md' | wc -l) files in $DEST"
