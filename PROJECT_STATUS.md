# PROJECT_STATUS.md

> **이 파일은 대화가 끊길 때마다 업데이트됩니다.**
> 새 대화창을 열 때 이 내용을 가장 먼저 확인하세요.

---

## 현재 구현 상태

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
│   └── google_translator.py
├── ocr_worker.py          # OCRWorker, TextStabilizer
└── translation_manager.py
```

## 성능 지표

| 항목 | 목표 | 현재 |
|------|------|------|
| 캡처 시간 | < 10ms | 측정 필요 |
| OCR 시간 | < 200ms | 측정 필요 |
| 안정화 시간 | 1.5초 | 설정 가능 |
| OCR 간격 | 0.5초 | 설정 가능 |

## 다음 단계

1. ~~프로젝트 스켈레톤 구현~~ (완료)
2. ~~화면 캡처 및 OCR 모듈 고도화~~ (완료)
3. **영역 선택 UI 연동**
4. 실제 통합 테스트
5. 게임 프로필 관리 UI
6. 번역 캐시 및 용어집 연동
7. 배포 패키징 (PyInstaller)

---

**마지막 업데이트**: 2024-12-22 04:50
**현재 브랜치**: `claude/add-project-status-gUpyd`
