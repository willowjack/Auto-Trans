"""
인터페이스 모듈 - 전략 패턴을 위한 추상 클래스

OCREngine: OCR 엔진 인터페이스
Translator: 번역 엔진 인터페이스
"""

from core.interfaces.ocr_engine import (
    OCREngine, OCRResult, TextBox, Language
)
from core.interfaces.translator import Translator, TranslationResult

__all__ = [
    "OCREngine", "OCRResult", "TextBox", "Language",
    "Translator", "TranslationResult"
]
