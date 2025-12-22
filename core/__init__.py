"""
Core 모듈 - 비즈니스 로직

- interfaces: OCR/번역 엔진 추상화 (전략 패턴)
- ocr: OCR 엔진 구현체
- translators: 번역 엔진 구현체
- ocr_worker: OCR 처리 워커 스레드
- translation_manager: 번역 관리자
"""

from core.ocr_worker import OCRWorker
from core.translation_manager import TranslationManager

__all__ = ["OCRWorker", "TranslationManager"]
