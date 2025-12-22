"""
번역 서비스 - 번역 엔진과 DB를 통합하는 고수준 서비스

핵심 기능:
1. 안정화된 텍스트 수신 시 번역 수행
2. DB에서 문맥 로드 (최근 대화 5개 + 용어집)
3. 번역 결과 자동 저장
4. 용어집 학습 및 적용
"""

import time
from typing import Optional, Callable, List
from threading import Thread, Lock
from queue import Queue, Empty
from dataclasses import dataclass

from core.interfaces.translator import TranslationResult
from core.translators.gemini_translator import GeminiTranslator, TranslationContext
from core.ocr_worker import StabilizedText
from data.database import Database
from data.models import HistoryEntry, GlossaryTerm
from data.repositories import HistoryRepository, GlossaryRepository


@dataclass
class TranslationJob:
    """번역 작업"""
    text: str
    game_id: Optional[int]
    source_language: Optional[str]
    target_language: str
    ocr_confidence: float = 0.0
    callback: Optional[Callable[[TranslationResult], None]] = None


@dataclass
class TranslationStats:
    """번역 통계"""
    total_translations: int = 0
    cache_hits: int = 0
    api_calls: int = 0
    total_time_ms: float = 0.0
    glossary_applications: int = 0

    @property
    def cache_hit_rate(self) -> float:
        if self.total_translations == 0:
            return 0.0
        return self.cache_hits / self.total_translations

    @property
    def avg_time_ms(self) -> float:
        if self.api_calls == 0:
            return 0.0
        return self.total_time_ms / self.api_calls


class TranslationService:
    """
    번역 서비스

    OCRWorker의 안정화된 텍스트를 받아 번역하고 결과를 DB에 저장합니다.
    번역 시 DB에서 문맥(최근 대화 + 용어집)을 로드하여 품질을 향상시킵니다.

    사용 예시:
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

        service.start()
    """

    # 설정
    HISTORY_CONTEXT_SIZE = 5     # 문맥에 포함할 최근 대화 수
    MAX_GLOSSARY_TERMS = 50      # 프롬프트에 포함할 최대 용어 수
    CACHE_SIZE = 500             # 번역 캐시 크기

    def __init__(
        self,
        db: Database,
        api_key: Optional[str] = None,
        target_language: str = "ko",
        source_language: Optional[str] = None,
        use_cache: bool = True
    ):
        """
        Args:
            db: 데이터베이스 인스턴스
            api_key: Gemini API 키
            target_language: 기본 목표 언어
            source_language: 기본 소스 언어 (None = 자동)
            use_cache: 캐시 사용 여부
        """
        self._db = db
        self._target_language = target_language
        self._source_language = source_language
        self._use_cache = use_cache

        # 번역 엔진
        self._translator = GeminiTranslator(api_key=api_key)

        # Repository
        self._history_repo = HistoryRepository(db)
        self._glossary_repo = GlossaryRepository(db)

        # 작업 큐 및 스레드
        self._queue: Queue[TranslationJob] = Queue()
        self._thread: Optional[Thread] = None
        self._running = False

        # 캐시
        self._cache: dict[str, TranslationResult] = {}
        self._cache_lock = Lock()

        # 현재 게임
        self._current_game_id: Optional[int] = None
        self._current_glossary: dict[str, str] = {}

        # 통계
        self._stats = TranslationStats()
        self._stats_lock = Lock()

        # 콜백
        self.on_translation_complete: Optional[Callable[[TranslationResult], None]] = None
        self.on_translation_start: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    # === 속성 ===

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

    @property
    def current_game_id(self) -> Optional[int]:
        return self._current_game_id

    @property
    def stats(self) -> TranslationStats:
        with self._stats_lock:
            return self._stats

    @property
    def is_running(self) -> bool:
        return self._running

    # === 게임 설정 ===

    def set_game(self, game_id: int) -> None:
        """
        현재 게임 설정

        게임이 변경되면 해당 게임의 용어집을 로드합니다.
        """
        self._current_game_id = game_id
        self._load_glossary(game_id)
        self._clear_cache()

    def _load_glossary(self, game_id: int) -> None:
        """게임 용어집 로드"""
        self._current_glossary = self._glossary_repo.get_as_dict(game_id)
        print(f"[TranslationService] 용어집 로드: {len(self._current_glossary)}개")

    def reload_glossary(self) -> None:
        """용어집 다시 로드"""
        if self._current_game_id:
            self._load_glossary(self._current_game_id)

    # === 제어 ===

    def start(self) -> None:
        """서비스 시작"""
        if self._running:
            return

        self._translator.initialize()
        self._running = True
        self._thread = Thread(target=self._run_loop, daemon=True, name="TranslationService")
        self._thread.start()

    def stop(self) -> None:
        """서비스 중지"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._translator.cleanup()

    # === 번역 요청 ===

    def handle_stabilized_text(self, stabilized: StabilizedText) -> None:
        """
        OCRWorker의 안정화된 텍스트 처리

        이 메서드를 OCRWorker.on_text_stabilized에 연결하세요.
        """
        if not stabilized.text.strip():
            return

        job = TranslationJob(
            text=stabilized.text,
            game_id=self._current_game_id,
            source_language=self._source_language,
            target_language=self._target_language,
            ocr_confidence=stabilized.confidence
        )

        self._queue.put(job)

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
            target_language: 목표 언어 (None이면 기본값)
            source_language: 소스 언어 (None이면 자동)
            callback: 완료 시 호출할 콜백
        """
        job = TranslationJob(
            text=text,
            game_id=self._current_game_id,
            source_language=source_language or self._source_language,
            target_language=target_language or self._target_language,
            callback=callback
        )

        self._queue.put(job)

    def translate_sync(
        self,
        text: str,
        target_language: Optional[str] = None,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """
        번역 요청 (동기)

        Returns:
            TranslationResult: 번역 결과
        """
        target = target_language or self._target_language
        source = source_language or self._source_language

        # 캐시 확인
        cache_key = self._make_cache_key(text, source, target)
        cached = self._get_from_cache(cache_key)
        if cached:
            with self._stats_lock:
                self._stats.total_translations += 1
                self._stats.cache_hits += 1
            return cached

        # 문맥 생성 및 번역
        context = self._build_context()
        result = self._translator.translate_with_context(
            text=text,
            target_language=target,
            source_language=source,
            context=context
        )

        # 캐시 및 DB 저장
        self._add_to_cache(cache_key, result)
        self._save_to_history(result)

        # 통계 업데이트
        with self._stats_lock:
            self._stats.total_translations += 1
            self._stats.api_calls += 1

        return result

    # === 내부 처리 ===

    def _run_loop(self) -> None:
        """번역 워커 루프"""
        while self._running:
            try:
                job = self._queue.get(timeout=0.1)
                self._process_job(job)
            except Empty:
                continue
            except Exception as e:
                if self.on_error:
                    self.on_error(e)

    def _process_job(self, job: TranslationJob) -> None:
        """번역 작업 처리"""
        # 시작 콜백
        if self.on_translation_start:
            try:
                self.on_translation_start(job.text)
            except Exception:
                pass

        start_time = time.perf_counter()

        try:
            # 캐시 확인
            cache_key = self._make_cache_key(
                job.text, job.source_language, job.target_language
            )
            cached = self._get_from_cache(cache_key)

            if cached:
                result = cached
                with self._stats_lock:
                    self._stats.cache_hits += 1
            else:
                # 문맥 생성
                context = self._build_context()

                # 번역 수행
                result = self._translator.translate_with_context(
                    text=job.text,
                    target_language=job.target_language,
                    source_language=job.source_language,
                    context=context
                )

                # 캐시 저장
                self._add_to_cache(cache_key, result)

                # DB 저장
                self._save_to_history(result)

                with self._stats_lock:
                    self._stats.api_calls += 1

            # 통계 업데이트
            processing_time = (time.perf_counter() - start_time) * 1000
            with self._stats_lock:
                self._stats.total_translations += 1
                self._stats.total_time_ms += processing_time

            # 콜백 호출
            if job.callback:
                job.callback(result)

            if self.on_translation_complete:
                self.on_translation_complete(result)

        except Exception as e:
            if self.on_error:
                self.on_error(e)

    def _build_context(self) -> TranslationContext:
        """번역 문맥 생성"""
        # 최근 대화 로드
        recent_history: List[tuple[str, str]] = []
        if self._current_game_id:
            entries = self._history_repo.get_recent(
                limit=self.HISTORY_CONTEXT_SIZE,
                game_id=self._current_game_id
            )
            # 시간순 정렬 (오래된 것부터)
            entries.reverse()
            recent_history = [
                (e.original_text, e.translated_text)
                for e in entries
            ]

        return TranslationContext(
            recent_history=recent_history,
            glossary=self._current_glossary
        )

    def _save_to_history(self, result: TranslationResult) -> None:
        """번역 결과를 히스토리에 저장"""
        try:
            entry = HistoryEntry(
                game_id=self._current_game_id,
                original_text=result.original_text,
                translated_text=result.translated_text,
                source_language=result.source_language,
                target_language=result.target_language,
                confidence=result.confidence
            )
            self._history_repo.create(entry)
        except Exception as e:
            print(f"[TranslationService] 히스토리 저장 실패: {e}")

    # === 용어집 관리 ===

    def add_glossary_term(
        self,
        original: str,
        translation: str,
        category: Optional[str] = None,
        is_global: bool = False
    ) -> None:
        """
        용어집에 새 항목 추가

        사용자가 번역을 수정했을 때 호출하세요.
        다음 번역부터 이 용어가 적용됩니다.
        """
        term = GlossaryTerm(
            game_id=None if is_global else self._current_game_id,
            original_term=original,
            translated_term=translation,
            category=category,
            is_global=is_global
        )

        try:
            self._glossary_repo.create(term)

            # 현재 용어집에도 추가
            self._current_glossary[original] = translation

            with self._stats_lock:
                self._stats.glossary_applications += 1

            print(f"[TranslationService] 용어집 추가: {original} → {translation}")
        except Exception as e:
            print(f"[TranslationService] 용어집 추가 실패: {e}")

    def update_glossary_term(
        self,
        original: str,
        new_translation: str
    ) -> None:
        """용어집 항목 업데이트"""
        self._current_glossary[original] = new_translation
        # TODO: DB 업데이트

    def remove_glossary_term(self, original: str) -> None:
        """용어집 항목 삭제"""
        if original in self._current_glossary:
            del self._current_glossary[original]
        # TODO: DB 삭제

    # === 캐시 관리 ===

    def _make_cache_key(
        self,
        text: str,
        source: Optional[str],
        target: str
    ) -> str:
        """캐시 키 생성"""
        return f"{text}|{source or 'auto'}|{target}|{self._current_game_id}"

    def _get_from_cache(self, key: str) -> Optional[TranslationResult]:
        """캐시에서 조회"""
        if not self._use_cache:
            return None

        with self._cache_lock:
            return self._cache.get(key)

    def _add_to_cache(self, key: str, result: TranslationResult) -> None:
        """캐시에 추가"""
        if not self._use_cache:
            return

        with self._cache_lock:
            # 캐시 크기 제한
            if len(self._cache) >= self.CACHE_SIZE:
                # 가장 오래된 항목 제거 (간단한 FIFO)
                oldest = next(iter(self._cache))
                del self._cache[oldest]

            self._cache[key] = result

    def _clear_cache(self) -> None:
        """캐시 초기화"""
        with self._cache_lock:
            self._cache.clear()

    # === 통계 ===

    def get_stats_dict(self) -> dict:
        """통계 딕셔너리 반환"""
        with self._stats_lock:
            return {
                "total_translations": self._stats.total_translations,
                "cache_hits": self._stats.cache_hits,
                "cache_hit_rate": f"{self._stats.cache_hit_rate:.1%}",
                "api_calls": self._stats.api_calls,
                "avg_time_ms": round(self._stats.avg_time_ms, 2),
                "glossary_terms": len(self._current_glossary),
                "glossary_applications": self._stats.glossary_applications
            }

    def reset_stats(self) -> None:
        """통계 초기화"""
        with self._stats_lock:
            self._stats = TranslationStats()
