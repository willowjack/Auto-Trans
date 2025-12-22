"""
Gemini 번역 엔진 구현체

Google Gemini API를 사용한 고품질 문맥 인식 번역
- gemini-1.5-flash 모델 사용
- 대화 맥락 및 용어집 주입 지원
"""

import time
from typing import Optional, List
from dataclasses import dataclass

from core.interfaces.translator import Translator, TranslationResult


@dataclass
class TranslationContext:
    """번역 문맥 정보"""
    recent_history: List[tuple[str, str]] = None  # [(원문, 번역문), ...]
    glossary: dict[str, str] = None               # {원문: 번역문, ...}
    game_name: Optional[str] = None
    additional_instructions: Optional[str] = None

    def __post_init__(self):
        if self.recent_history is None:
            self.recent_history = []
        if self.glossary is None:
            self.glossary = {}


class GeminiTranslator(Translator):
    """
    Google Gemini 기반 번역 엔진

    특징:
    - gemini-1.5-flash 모델 사용 (빠르고 저렴)
    - 문맥 인식 번역 (이전 대화 + 용어집)
    - 게임 특화 번역 프롬프트

    사용 예시:
        translator = GeminiTranslator(api_key="your-api-key")
        translator.initialize()

        context = TranslationContext(
            recent_history=[("Hello", "안녕"), ("Knight", "기사")],
            glossary={"Dragon": "용", "Mana": "마나"}
        )

        result = translator.translate_with_context(
            "The Knight fights the Dragon",
            target_language="ko",
            context=context
        )
    """

    MODEL_NAME = "gemini-1.5-flash"

    # 시스템 프롬프트 템플릿
    SYSTEM_PROMPT_TEMPLATE = """당신은 게임 텍스트 전문 번역가입니다. 다음 규칙을 따르세요:

1. 게임의 분위기와 톤을 유지하며 자연스럽게 번역하세요.
2. 캐릭터 대사는 말투와 성격이 드러나도록 번역하세요.
3. 고유명사(캐릭터명, 지명, 아이템명)는 용어집에 있으면 그대로 사용하세요.
4. 이전 대화 맥락을 고려하여 일관성 있게 번역하세요.
5. 번역문만 출력하세요. 설명이나 주석은 포함하지 마세요.

{context_section}

원문을 {target_language}로 번역하세요."""

    CONTEXT_TEMPLATE = """
### 이전 대화 맥락:
{history}

### 용어집 (반드시 이 번역을 사용하세요):
{glossary}
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = MODEL_NAME,
        temperature: float = 0.3,
        max_output_tokens: int = 1024
    ):
        """
        Args:
            api_key: Gemini API 키 (None이면 환경변수에서 로드)
            model_name: 사용할 모델 이름
            temperature: 생성 온도 (낮을수록 일관성 있음)
            max_output_tokens: 최대 출력 토큰 수
        """
        self._api_key = api_key
        self._model_name = model_name
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

        self._model = None
        self._initialized = False

        # 통계
        self._total_translations = 0
        self._total_tokens = 0
        self._total_time_ms = 0.0

    @property
    def name(self) -> str:
        return f"Gemini ({self._model_name})"

    @property
    def supported_languages(self) -> list[str]:
        return [
            "ko", "en", "ja", "zh-cn", "zh-tw",
            "es", "fr", "de", "it", "pt", "ru",
            "ar", "hi", "th", "vi"
        ]

    @property
    def avg_translation_time_ms(self) -> float:
        if self._total_translations == 0:
            return 0.0
        return self._total_time_ms / self._total_translations

    def initialize(self) -> None:
        """Gemini API 초기화"""
        if self._initialized:
            return

        try:
            import google.generativeai as genai

            # API 키 설정
            if self._api_key:
                genai.configure(api_key=self._api_key)
            else:
                import os
                api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError(
                        "Gemini API 키가 필요합니다. "
                        "GEMINI_API_KEY 환경변수를 설정하거나 api_key 매개변수를 전달하세요."
                    )
                genai.configure(api_key=api_key)

            # 모델 생성
            generation_config = genai.types.GenerationConfig(
                temperature=self._temperature,
                max_output_tokens=self._max_output_tokens,
            )

            self._model = genai.GenerativeModel(
                model_name=self._model_name,
                generation_config=generation_config
            )

            self._initialized = True

        except ImportError:
            raise ImportError(
                "google-generativeai가 설치되지 않았습니다.\n"
                "설치: pip install google-generativeai"
            )

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """기본 번역 (문맥 없음)"""
        return self.translate_with_context(
            text=text,
            target_language=target_language,
            source_language=source_language,
            context=None
        )

    def translate_with_context(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        context: Optional[TranslationContext] = None
    ) -> TranslationResult:
        """
        문맥 인식 번역

        Args:
            text: 번역할 텍스트
            target_language: 목표 언어 코드
            source_language: 원본 언어 코드 (자동 감지)
            context: 번역 문맥 (이전 대화, 용어집 등)

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

        start_time = time.perf_counter()

        # 프롬프트 생성
        system_prompt = self._build_system_prompt(target_language, context)
        user_prompt = f"원문: {text}"

        try:
            # Gemini API 호출
            response = self._model.generate_content(
                f"{system_prompt}\n\n{user_prompt}"
            )

            translated_text = response.text.strip()

            # 통계 업데이트
            processing_time = (time.perf_counter() - start_time) * 1000
            self._total_translations += 1
            self._total_time_ms += processing_time

            # 토큰 사용량 추적 (가능한 경우)
            if hasattr(response, 'usage_metadata'):
                self._total_tokens += getattr(response.usage_metadata, 'total_token_count', 0)

            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source_language or "auto",
                target_language=target_language,
                confidence=1.0  # Gemini는 신뢰도를 제공하지 않음
            )

        except Exception as e:
            print(f"[GeminiTranslator] 번역 오류: {e}")
            return TranslationResult(
                original_text=text,
                translated_text=f"[번역 오류: {str(e)[:50]}]",
                source_language=source_language or "auto",
                target_language=target_language,
                confidence=0.0
            )

    def translate_batch(
        self,
        texts: list[str],
        target_language: str,
        source_language: Optional[str] = None
    ) -> list[TranslationResult]:
        """여러 텍스트 일괄 번역"""
        results = []
        for text in texts:
            result = self.translate(text, target_language, source_language)
            results.append(result)
        return results

    def _build_system_prompt(
        self,
        target_language: str,
        context: Optional[TranslationContext]
    ) -> str:
        """시스템 프롬프트 생성"""
        target_lang_name = self._get_language_name(target_language)

        if context and (context.recent_history or context.glossary):
            # 히스토리 포맷팅
            history_text = ""
            if context.recent_history:
                history_lines = []
                for i, (orig, trans) in enumerate(context.recent_history[-5:], 1):
                    history_lines.append(f"{i}. \"{orig}\" → \"{trans}\"")
                history_text = "\n".join(history_lines)
            else:
                history_text = "(없음)"

            # 용어집 포맷팅
            glossary_text = ""
            if context.glossary:
                glossary_lines = [f"- {k} = {v}" for k, v in context.glossary.items()]
                glossary_text = "\n".join(glossary_lines[:20])  # 최대 20개
            else:
                glossary_text = "(없음)"

            context_section = self.CONTEXT_TEMPLATE.format(
                history=history_text,
                glossary=glossary_text
            )
        else:
            context_section = ""

        return self.SYSTEM_PROMPT_TEMPLATE.format(
            context_section=context_section,
            target_language=target_lang_name
        )

    def _get_language_name(self, code: str) -> str:
        """언어 코드를 언어 이름으로 변환"""
        names = {
            "ko": "한국어",
            "en": "English",
            "ja": "日本語",
            "zh-cn": "简体中文",
            "zh-tw": "繁體中文",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский"
        }
        return names.get(code, code)

    def cleanup(self) -> None:
        """리소스 정리"""
        self._model = None
        self._initialized = False

    def get_stats(self) -> dict:
        """통계 반환"""
        return {
            "total_translations": self._total_translations,
            "total_tokens": self._total_tokens,
            "avg_time_ms": self.avg_translation_time_ms
        }

    def reset_stats(self) -> None:
        """통계 초기화"""
        self._total_translations = 0
        self._total_tokens = 0
        self._total_time_ms = 0.0
