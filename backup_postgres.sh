#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?Set DATABASE_URL to the production PostgreSQL connection string}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/neural_gold_${STAMP}.dump"
pg_dump "$DATABASE_URL" --format=custom --no-owner --file="$OUT"
find "$BACKUP_DIR" -type f -name 'neural_gold_*.dump' -mtime +"$RETENTION_DAYS" -delete
echo "Created $OUT"
