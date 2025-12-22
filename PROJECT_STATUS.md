# PROJECT_STATUS.md

> **이 파일은 대화가 끊길 때마다 업데이트됩니다.**
> 새 대화창을 열 때 이 내용을 가장 먼저 확인하세요.

---

## 현재 구현 상태

- **2단계 완료**: 전체 프로젝트 스켈레톤 구현
  - MVC 패턴 기반 모듈 분리 완료
  - 전략 패턴으로 OCR/번역 엔진 추상화
  - SQLite DB 스키마 설계 (Games, History, Glossary)
  - PyQt6 UI 스켈레톤 구현
  - 크로스 플랫폼 (Win/Mac) 경로 처리

## 프로젝트 개요

- **프로젝트명**: Auto-Trans (실시간 게임 화면 번역기)
- **기술 스택**: Python 3.10+, PyQt6, RapidOCR, SQLite
- **지원 플랫폼**: Windows, macOS

## 파일 구조

```
/home/user/Auto-Trans/
├── main.py                 # 진입점
├── requirements.txt        # 의존성
├── CLAUDE.md              # AI 어시스턴트 규칙
├── PROJECT_STATUS.md      # 현재 파일
│
├── core/                   # 비즈니스 로직
│   ├── __init__.py
│   ├── interfaces/         # 전략 패턴 인터페이스
│   │   ├── ocr_engine.py   # OCR 엔진 추상 클래스
│   │   └── translator.py   # 번역 엔진 추상 클래스
│   ├── ocr/
│   │   └── rapid_ocr.py    # RapidOCR 구현체
│   ├── translators/
│   │   └── google_translator.py
│   ├── ocr_worker.py       # OCR 워커 스레드
│   └── translation_manager.py
│
├── ui/                     # PyQt6 UI
│   ├── main_window.py      # 메인 컨트롤 윈도우
│   ├── overlay.py          # 번역 오버레이
│   └── settings_dialog.py  # 설정 다이얼로그
│
├── data/                   # 데이터 레이어
│   ├── database.py         # SQLite 연결 및 스키마
│   ├── models.py           # 데이터 모델
│   └── repositories.py     # Repository 패턴 CRUD
│
├── utils/                  # 유틸리티
│   ├── platform.py         # OS별 경로 처리
│   └── config.py           # 설정 관리
│
└── scripts/
    ├── backup.sh
    └── restore.sh
```

## DB 스키마

```sql
-- Games: 게임별 설정
CREATE TABLE games (
    id, name, process_name,
    source_language, target_language,
    capture_region_x/y/w/h,
    ocr_interval, stabilization_time, is_active
);

-- History: 번역 기록
CREATE TABLE history (
    id, game_id, original_text, translated_text,
    source_language, target_language, confidence
);

-- Glossary: 용어집
CREATE TABLE glossary (
    id, game_id, original_term, translated_term,
    category, notes, is_global
);
```

## 주요 규칙

- **OCR**: 0.5초마다 실행
- **번역 트리거**: 텍스트가 1.5초간 동일할 때만 번역
- **전략 패턴**: `OCREngine`, `Translator` 인터페이스 상속으로 엔진 교체 가능

## 다음 단계

1. ~~프로젝트 스켈레톤 구현~~ (완료)
2. **화면 캡처 영역 선택 UI** 구현
3. 실제 OCR/번역 테스트
4. 게임 프로필 관리 UI
5. 용어집/히스토리 뷰어 UI
6. 시스템 트레이 연동
7. 배포 패키징 (PyInstaller)

---

**마지막 업데이트**: 2024-12-22 04:35
**현재 브랜치**: `claude/add-project-status-gUpyd`
