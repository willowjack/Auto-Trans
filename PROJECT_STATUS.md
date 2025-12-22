# PROJECT_STATUS.md

> **이 파일은 대화가 끊길 때마다 업데이트됩니다.**
> 새 대화창을 열 때 이 내용을 가장 먼저 확인하세요.

---

## 현재 구현 상태

- **0단계 (초기화)**: 프로젝트 초기 설정 완료
  - Git 저장소 초기화됨
  - 기본 .gitignore, LICENSE, README.md 존재

## 프로젝트 개요

- **프로젝트명**: Auto-Trans (자동 번역 도구)
- **목표**: OCR 기반 실시간 화면 번역 시스템 (추정)

## 파일 구조

```
/home/user/Auto-Trans/
├── .gitignore
├── LICENSE
├── README.md
└── PROJECT_STATUS.md (현재 파일)
```

## 예정된 구조 (계획)

```
/core       - 핵심 로직 (OCR, 번역 등)
/ui         - PyQt6 사용자 인터페이스
/database   - SQLite 데이터베이스
```

## 주요 규칙 (예정)

- OCR은 0.5초마다 실행, 번역은 텍스트가 1.5초간 동일할 때만 트리거
- DB 스키마: History, Glossary 테이블

## 다음 단계

1. 프로젝트 기본 구조 생성 (/core, /ui, /database)
2. 의존성 정의 (requirements.txt)
3. RapidOCR 연동
4. PyQt6 UI 구현
5. SQLite 데이터베이스 설정

---

**마지막 업데이트**: 2024-12-22
**현재 브랜치**: `claude/add-project-status-gUpyd`
