"""
번역 엔진 인터페이스 (전략 패턴)

새로운 번역 엔진을 추가하려면 Translator 클래스를 상속받아 구현하세요.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationResult:
    """번역 결과 데이터 클래스"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: Optional[float] = None

    @property
    def is_empty(self) -> bool:
        return not self.translated_text.strip()


class Translator(ABC):
    """
    번역 엔진 추상 클래스 (Strategy Interface)

    모든 번역 엔진 구현체는 이 클래스를 상속받아야 합니다.

    구현 예시:
        class MyTranslator(Translator):
            def translate(self, text: str, ...) -> TranslationResult:
                # 번역 로직 구현
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
        """엔진 초기화 (API 연결 등)"""
        pass

    @abstractmethod
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """
        텍스트 번역

        Args:
            text: 번역할 텍스트
            target_language: 목표 언어 코드
            source_language: 원본 언어 코드 (None이면 자동 감지)

        Returns:
            TranslationResult: 번역 결과
        """
        pass

    @abstractmethod
    def translate_batch(
        self,
        texts: list[str],
        target_language: str,
        source_language: Optional[str] = None
    ) -> list[TranslationResult]:
        """
        여러 텍스트 일괄 번역

        Args:
            texts: 번역할 텍스트 목록
            target_language: 목표 언어 코드
            source_language: 원본 언어 코드 (None이면 자동 감지)

        Returns:
            list[TranslationResult]: 번역 결과 목록
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
