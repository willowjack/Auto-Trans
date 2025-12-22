"""
Google 번역 엔진 구현체

googletrans 라이브러리를 사용한 무료 번역
"""

from typing import Optional

from core.interfaces.translator import Translator, TranslationResult


class GoogleTranslator(Translator):
    """Google 번역 기반 번역 엔진"""

    def __init__(self):
        self._translator = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "Google Translate"

    @property
    def supported_languages(self) -> list[str]:
        return [
            "ko", "en", "ja", "zh-cn", "zh-tw",
            "es", "fr", "de", "it", "pt", "ru"
        ]

    def initialize(self) -> None:
        """번역기 초기화"""
        if self._initialized:
            return

        try:
            from googletrans import Translator as GTranslator
            self._translator = GTranslator()
            self._initialized = True
        except ImportError:
            raise ImportError(
                "googletrans가 설치되지 않았습니다. "
                "'pip install googletrans==4.0.0-rc1' 명령어로 설치하세요."
            )

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
        if not self._initialized:
            self.initialize()

        if not text.strip():
            return TranslationResult(
                original_text=text,
                translated_text="",
                source_language=source_language or "auto",
                target_language=target_language
            )

        src = source_language or "auto"
        result = self._translator.translate(text, dest=target_language, src=src)

        return TranslationResult(
            original_text=text,
            translated_text=result.text,
            source_language=result.src,
            target_language=target_language,
            confidence=None
        )

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
            source_language: 원본 언어 코드

        Returns:
            list[TranslationResult]: 번역 결과 목록
        """
        if not self._initialized:
            self.initialize()

        results = []
        for text in texts:
            result = self.translate(text, target_language, source_language)
            results.append(result)
        return results

    def cleanup(self) -> None:
        """리소스 정리"""
        self._translator = None
        self._initialized = False
