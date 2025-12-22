#!/bin/bash

# Auto-Trans 백업 스크립트
# 사용법: ./scripts/backup.sh [설명]

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/.backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DESCRIPTION="${1:-manual}"
BACKUP_NAME="backup_${TIMESTAMP}_${DESCRIPTION}"
BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"

# 백업 폴더 생성
mkdir -p "$BACKUP_DIR"

# 백업 대상 (git 폴더, 백업 폴더, __pycache__ 제외)
cd "$PROJECT_DIR"
tar --exclude='.git' \
    --exclude='.backups' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='venv' \
    -czf "$BACKUP_FILE" .

# 백업 정보 저장
echo "Created: $(date)" > "$BACKUP_DIR/${BACKUP_NAME}.info"
echo "Description: $DESCRIPTION" >> "$BACKUP_DIR/${BACKUP_NAME}.info"
echo "Files:" >> "$BACKUP_DIR/${BACKUP_NAME}.info"
tar -tzf "$BACKUP_FILE" >> "$BACKUP_DIR/${BACKUP_NAME}.info"

# 오래된 백업 정리 (30개 초과 시 가장 오래된 것 삭제)
cd "$BACKUP_DIR"
BACKUP_COUNT=$(ls -1 *.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 30 ]; then
    ls -1t *.tar.gz | tail -n +31 | while read old_backup; do
        rm -f "$old_backup" "${old_backup%.tar.gz}.info"
        echo "Deleted old backup: $old_backup"
    done
fi

echo "========================================="
echo "Backup created: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo "========================================="
