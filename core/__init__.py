"""
Core 모듈 - 비즈니스 로직

- interfaces: OCR/번역 엔진 추상화 (전략 패턴)
- capture: 화면 캡처 (mss 기반)
- ocr: OCR 엔진 구현체
- translators: 번역 엔진 구현체 (Gemini, Google)
- ocr_worker: OCR 처리 워커 스레드
- translation_service: 번역 서비스 (문맥 주입 + DB 연동)
"""

from core.ocr_worker import OCRWorker, StabilizedText, WorkerState, WorkerStats
from core.translation_service import TranslationService

__all__ = [
    "OCRWorker", "StabilizedText", "WorkerState", "WorkerStats",
    "TranslationService"
]
