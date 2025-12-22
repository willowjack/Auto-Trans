"""
OCR 엔진 인터페이스 (전략 패턴)

새로운 OCR 엔진을 추가하려면 OCREngine 클래스를 상속받아 구현하세요.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class OCRResult:
    """OCR 결과 데이터 클래스"""
    text: str
    confidence: float
    bounding_boxes: list[dict]  # [{"x": int, "y": int, "w": int, "h": int, "text": str}, ...]

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


class OCREngine(ABC):
    """
    OCR 엔진 추상 클래스 (Strategy Interface)

    모든 OCR 엔진 구현체는 이 클래스를 상속받아야 합니다.

    구현 예시:
        class MyOCREngine(OCREngine):
            def recognize(self, image: np.ndarray) -> OCRResult:
                # OCR 로직 구현
                pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """엔진 이름 반환"""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """지원 언어 목록 반환"""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """엔진 초기화 (모델 로딩 등)"""
        pass

    @abstractmethod
    def recognize(self, image: np.ndarray, language: Optional[str] = None) -> OCRResult:
        """
        이미지에서 텍스트 인식

        Args:
            image: numpy 배열 형태의 이미지 (BGR 또는 RGB)
            language: 인식할 언어 코드 (None이면 자동 감지)

        Returns:
            OCRResult: 인식 결과
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """리소스 정리"""
        pass

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
