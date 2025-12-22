# PROJECT_STATUS.md

> **이 파일은 대화가 끊길 때마다 업데이트됩니다.**
> 새 대화창을 열 때 이 내용을 가장 먼저 확인하세요.

---

## 현재 구현 상태

- **6단계 완료**: 최종 통합 및 시스템 완성
  - 시스템 트레이: 최소화 시 트레이로 이동, 트레이 메뉴
  - 예외 처리: 네트워크 오류, API 키 누락 시 알림 표시
  - 영역 선택: 마우스 드래그로 ROI 선택 (RegionSelector)
  - 설정 UI: API Keys, 안정화 시간, JSON 저장 완료
  - 전역 예외 핸들러 (sys.excepthook)
  - NotificationManager 통합

- **5단계 완료**: PyQt6 사용자 인터페이스
  - 오버레이 창: 투명 배경, Frameless, Always on Top
  - 마우스 드래그 이동, 자동 크기 조정 (Word-wrap)
  - 스타일 설정: 폰트, 색상, 투명도
  - 히스토리 에디터: 실시간 번역 로그
  - 번역 수정 → DB 업데이트 → 오버레이 즉시 반영
  - 용어집 자동 학습

- **4단계 완료**: 번역 엔진과 DB 로직 구현
  - Gemini API 기반 번역 엔진 (gemini-1.5-flash)
  - 문맥 주입: 최근 5개 대화 + 게임별 용어집
  - TranslationService: OCR → 번역 → DB 저장 통합
  - 자동 히스토리 저장 및 용어집 학습

- **3단계 완료**: 화면 캡처 및 OCR 모듈 고도화
  - mss 기반 고성능 화면 캡처 모듈
  - RapidOCR 엔진 (한/영/일/중 지원)
  - 텍스트 안정화 로직 (1.5초 동일 시 번역 신호)
  - 성능 통계 및 모니터링

## 프로젝트 개요

- **프로젝트명**: Auto-Trans (실시간 게임 화면 번역기)
- **기술 스택**: Python 3.10+, PyQt6, RapidOCR, mss, SQLite
- **지원 플랫폼**: Windows, macOS

## 핵심 모듈

### 화면 캡처 (`core/capture/`)
```python
from core.capture import ScreenCapture, CaptureRegion

capture = ScreenCapture()
capture.set_region(100, 100, 800, 600)  # 캡처 영역 설정
image = capture.grab()  # numpy 배열 반환
```

### OCR 엔진 (`core/ocr/`)
```python
from core.ocr import RapidOCREngine

engine = RapidOCREngine(use_gpu=False)
result = engine.recognize(image)
print(result.text)       # 인식된 텍스트
print(result.boxes)      # TextBox 목록
print(result.confidence) # 신뢰도
```

### OCR 워커 (`core/ocr_worker.py`)
```python
from core import OCRWorker

worker = OCRWorker(engine, capture.grab, interval=0.5)
worker.on_text_stabilized = lambda s: translate(s.text)
worker.start()
```

### 번역 서비스 (`core/translation_service.py`)
```python
from core import TranslationService
from data import Database

db = Database()
db.connect()

service = TranslationService(
    db=db,
    api_key="your-gemini-api-key",
    target_language="ko"
)

# OCRWorker와 연결
ocr_worker.on_text_stabilized = service.handle_stabilized_text

# 번역 결과 수신
service.on_translation_complete = lambda r: overlay.set_text(r.translated_text)

# 용어집 학습 (사용자가 번역 수정 시)
service.add_glossary_term("NPC", "비플레이어 캐릭터", category="게임용어")

service.start()
```

## 텍스트 안정화 로직

```
[0.0s] OCR 결과: "Hello World" → 새 텍스트, 타이머 시작
[0.5s] OCR 결과: "Hello World" → 동일, 경과 0.5초
[1.0s] OCR 결과: "Hello World" → 동일, 경과 1.0초
[1.5s] OCR 결과: "Hello World" → 동일, 경과 1.5초 ≥ 임계값
                                 → ★ 번역 신호 발생!
```

## 파일 구조

```
core/
├── __init__.py
├── interfaces/
│   ├── ocr_engine.py      # OCREngine, OCRResult, TextBox
│   └── translator.py      # Translator, TranslationResult
├── capture/
│   ├── screen_capture.py  # ScreenCapture, CaptureRegion
│   └── region.py          # RegionSelector (영역 선택 UI)
├── ocr/
│   └── rapid_ocr.py       # RapidOCREngine
├── translators/
│   └── gemini_translator.py  # GeminiTranslator, TranslationContext
├── ocr_worker.py          # OCRWorker, TextStabilizer
└── translation_service.py # TranslationService (DB 통합)

ui/
├── __init__.py
├── main_window.py         # 메인 컨트롤 윈도우
├── overlay_window.py      # 오버레이 (투명, 드래그, 스타일)
├── history_editor.py      # 히스토리 편집기 (실시간 로그)
├── settings_dialog.py     # 설정 다이얼로그 (API Keys, 탭 구조)
└── region_selector.py     # 영역 선택기 (마우스 드래그 ROI)
```

## 성능 지표

| 항목 | 목표 | 현재 |
|------|------|------|
| 캡처 시간 | < 10ms | 측정 필요 |
| OCR 시간 | < 200ms | 측정 필요 |
| 안정화 시간 | 1.5초 | 설정 가능 |
| OCR 간격 | 0.5초 | 설정 가능 |

## 번역 파이프라인

```
[화면 캡처] → [OCR 인식] → [텍스트 안정화] → [문맥 로드] → [Gemini 번역] → [오버레이 표시]
     ↓              ↓              ↓              ↓              ↓
  ScreenCapture  RapidOCR   TextStabilizer   DB Context   GeminiTranslator
                                                ↓              ↓
                                          History 5개      → History 저장
                                          + Glossary       → Glossary 학습
```

## 다음 단계

1. ~~프로젝트 스켈레톤 구현~~ (완료)
2. ~~화면 캡처 및 OCR 모듈 고도화~~ (완료)
3. ~~번역 엔진과 DB 로직 구현~~ (완료)
4. ~~PyQt6 사용자 인터페이스~~ (완료)
5. ~~영역 선택 UI 연동~~ (완료)
6. ~~최종 통합~~ (완료)
7. **실제 통합 테스트**
8. 게임 프로필 관리 UI
9. 배포 패키징 (PyInstaller)

---

**마지막 업데이트**: 2025-12-22
**현재 브랜치**: `claude/add-project-status-gUpyd`
