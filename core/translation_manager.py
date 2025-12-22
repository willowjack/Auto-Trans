"""
번역 매니저 - 번역 처리 및 캐싱

안정화된 텍스트를 받아 번역하고 결과를 관리합니다.
"""

from typing import Optional, Callable
from threading import Thread, Lock
from queue import Queue, Empty
from dataclasses import dataclass

from core.interfaces.translator import Translator, TranslationResult
from core.ocr_worker import StabilizedText


@dataclass
class TranslationTask:
    """번역 작업"""
    text: str
    source_language: Optional[str]
    target_language: str
    callback: Optional[Callable[[TranslationResult], None]]


class TranslationManager:
    """
    번역 매니저

    번역 요청을 큐에 넣고 백그라운드에서 처리합니다.
    동일한 텍스트는 캐시에서 반환합니다.

    사용 예시:
        manager = TranslationManager(translator)
        manager.on_translation_complete = lambda r: print(r.translated_text)
        manager.start()
        manager.translate("Hello", "ko")
    """

    def __init__(
        self,
        translator: Translator,
        target_language: str = "ko",
        source_language: Optional[str] = None,
        cache_size: int = 1000
    ):
        """
        Args:
            translator: 번역 엔진 인스턴스
            target_language: 기본 목표 언어
            source_language: 기본 소스 언어 (None이면 자동 감지)
            cache_size: 캐시 크기
        """
        self._translator = translator
        self._target_language = target_language
        self._source_language = source_language
        self._cache_size = cache_size

        self._queue: Queue[TranslationTask] = Queue()
        self._cache: dict[str, TranslationResult] = {}
        self._cache_lock = Lock()

        self._thread: Optional[Thread] = None
        self._running = False

        # 용어집 (Glossary) - 우선 적용되는 번역
        self._glossary: dict[str, str] = {}

        # 콜백
        self.on_translation_complete: Optional[Callable[[TranslationResult], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    @property
    def target_language(self) -> str:
        return self._target_language

    @target_language.setter
    def target_language(self, value: str) -> None:
        self._target_language = value
        self._clear_cache()

    @property
    def source_language(self) -> Optional[str]:
        return self._source_language

    @source_language.setter
    def source_language(self, value: Optional[str]) -> None:
        self._source_language = value
        self._clear_cache()

    def set_glossary(self, glossary: dict[str, str]) -> None:
        """용어집 설정"""
        self._glossary = glossary.copy()

    def add_glossary_term(self, original: str, translation: str) -> None:
        """용어집에 항목 추가"""
        self._glossary[original] = translation

    def start(self) -> None:
        """번역 매니저 시작"""
        if self._running:
            return

        self._translator.initialize()
        self._running = True
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """번역 매니저 중지"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._translator.cleanup()

    def translate(
        self,
        text: str,
        target_language: Optional[str] = None,
        source_language: Optional[str] = None,
        callback: Optional[Callable[[TranslationResult], None]] = None
    ) -> None:
        """
        번역 요청 (비동기)

        Args:
            text: 번역할 텍스트
            target_language: 목표 언어 (None이면 기본값 사용)
            source_language: 소스 언어 (None이면 기본값 사용)
            callback: 완료 시 호출할 콜백
        """
        task = TranslationTask(
            text=text,
            source_language=source_language or self._source_language,
            target_language=target_language or self._target_language,
            callback=callback
        )
        self._queue.put(task)

    def translate_sync(
        self,
        text: str,
        target_language: Optional[str] = None,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """
        번역 요청 (동기)

        Args:
            text: 번역할 텍스트
            target_language: 목표 언어
            source_language: 소스 언어

        Returns:
            TranslationResult: 번역 결과
        """
        target = target_language or self._target_language
        source = source_language or self._source_language

        # 캐시 확인
        cache_key = f"{text}|{source}|{target}"
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        # 용어집 적용
        translated_text = self._apply_glossary(text)
        if translated_text != text:
            result = TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source or "auto",
                target_language=target
            )
        else:
            result = self._translator.translate(text, target, source)

        # 캐시 저장
        self._add_to_cache(cache_key, result)

        return result

    def handle_stabilized_text(self, stabilized: StabilizedText) -> None:
        """OCRWorker의 안정화된 텍스트 처리"""
        if stabilized.text:
            self.translate(stabilized.text)

    def _run(self) -> None:
        """번역 워커 스레드"""
        while self._running:
            try:
                task = self._queue.get(timeout=0.1)
                self._process_task(task)
            except Empty:
                continue

    def _process_task(self, task: TranslationTask) -> None:
        """번역 작업 처리"""
        try:
            result = self.translate_sync(
                task.text,
                task.target_language,
                task.source_language
            )

            if task.callback:
                task.callback(result)

            if self.on_translation_complete:
                self.on_translation_complete(result)

        except Exception as e:
            if self.on_error:
                self.on_error(e)

    def _apply_glossary(self, text: str) -> str:
        """용어집 적용"""
        result = text
        for original, translation in self._glossary.items():
            result = result.replace(original, translation)
        return result

    def _add_to_cache(self, key: str, result: TranslationResult) -> None:
        """캐시에 추가"""
        with self._cache_lock:
            if len(self._cache) >= self._cache_size:
                # 가장 오래된 항목 제거 (간단한 FIFO)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = result

    def _clear_cache(self) -> None:
        """캐시 초기화"""
        with self._cache_lock:
            self._cache.clear()
