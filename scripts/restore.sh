#!/bin/bash

# Auto-Trans 복원 스크립트
# 사용법: ./scripts/restore.sh [백업파일명]

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/.backups"

# 백업 목록 표시 함수
show_backups() {
    echo "========================================="
    echo "사용 가능한 백업 목록:"
    echo "========================================="
    cd "$BACKUP_DIR"
    ls -1t *.tar.gz 2>/dev/null | while read backup; do
        size=$(du -h "$backup" | cut -f1)
        date=$(echo "$backup" | sed 's/backup_\([0-9]*\)_\([0-9]*\)_.*/\1 \2/' | sed 's/\(....\)\(..\)\(..\) \(..\)\(..\)\(..\)/\1-\2-\3 \4:\5:\6/')
        echo "  $backup ($size) - $date"
    done
    echo "========================================="
}

# 인자 없으면 백업 목록 표시
if [ -z "$1" ]; then
    show_backups
    echo ""
    echo "사용법: ./scripts/restore.sh <백업파일명>"
    echo "예: ./scripts/restore.sh backup_20241222_143000_manual.tar.gz"
    exit 0
fi

BACKUP_FILE="$BACKUP_DIR/$1"

# 백업 파일 존재 확인
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: 백업 파일을 찾을 수 없습니다: $BACKUP_FILE"
    show_backups
    exit 1
fi

# 복원 전 현재 상태 백업
echo "복원 전 현재 상태를 백업합니다..."
"$PROJECT_DIR/scripts/backup.sh" "before_restore"

# 확인 메시지
echo ""
echo "========================================="
echo "WARNING: 현재 파일들이 백업 내용으로 덮어씌워집니다!"
echo "백업 파일: $1"
echo "========================================="
read -p "계속하시겠습니까? (y/N): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "복원이 취소되었습니다."
    exit 0
fi

# 복원 실행
cd "$PROJECT_DIR"
echo "복원 중..."

# 기존 파일 삭제 (git, backups, scripts 제외)
find . -maxdepth 1 -type f ! -name '.gitignore' -delete 2>/dev/null || true
find . -maxdepth 1 -type d ! -name '.' ! -name '.git' ! -name '.backups' ! -name 'scripts' -exec rm -rf {} + 2>/dev/null || true

# 백업에서 복원
tar -xzf "$BACKUP_FILE"

echo "========================================="
echo "복원 완료!"
echo "========================================="
