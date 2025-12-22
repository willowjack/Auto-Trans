# CLAUDE.md - AI 어시스턴트 규칙

> 이 파일은 Claude Code가 매 대화 시작 시 자동으로 읽습니다.

---

## 필수 규칙

### 1. 대화 시작 시
- `PROJECT_STATUS.md`를 가장 먼저 읽고 현재 상태 파악
- 이전 대화에서 진행 중이던 작업 확인

### 2. 작업 완료 시
- 주요 작업 완료 후 `PROJECT_STATUS.md` 업데이트
- 변경사항 커밋 전 상태 파일도 함께 업데이트

### 3. 대화 종료 전
- `PROJECT_STATUS.md`에 현재 진행 상황 기록
- 다음에 해야 할 작업 명시

### 4. 백업
- 중요한 변경 전 `scripts/backup.sh` 실행
- 백업 파일은 `.backups/` 폴더에 시간별로 저장됨

---

## 프로젝트 컨벤션

### 파일 구조 (예정)
```
/core       - 핵심 로직 (OCR, 번역)
/ui         - PyQt6 UI
/database   - SQLite
/scripts    - 유틸리티 스크립트
/.backups   - 백업 폴더 (git 제외)
```

### 기술 스택 (예정)
- Python 3.10+
- PyQt6 (UI)
- RapidOCR (OCR)
- SQLite (DB)

---

## 백업 및 롤백

### 백업 생성
```bash
./scripts/backup.sh
```

### 롤백
```bash
./scripts/restore.sh [백업파일명]
```

### 백업 목록 확인
```bash
ls -la .backups/
```
