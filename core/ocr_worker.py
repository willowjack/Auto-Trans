"""
OCR 워커 - 고성능 백그라운드 OCR 처리

핵심 기능:
- 0.5초 간격으로 화면 캡처 및 OCR 수행
- 텍스트 안정화: 1.5초간 동일한 텍스트면 번역 신호 발생
- 성능 모니터링 및 통계
- PyQt 시그널 지원
"""

import time
from typing import Optional, Callable, List
from threading import Thread, Event, Lock
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

import numpy as np

from core.interfaces.ocr_engine import OCREngine, OCRResult, TextBox


class WorkerState(Enum):
    """워커 상태"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class StabilizedText:
    """
    안정화된 텍스트 결과

    텍스트가 stabilization_time 동안 동일하게 유지되면 생성됩니다.
    """
    text: str                          # 안정화된 텍스트
    stable_duration: float             # 동일하게 유지된 시간 (초)
    ocr_result: OCRResult              # 원본 OCR 결과
    timestamp: float = field(default_factory=time.time)  # 안정화 시점

    @property
    def boxes(self) -> List[TextBox]:
        """텍스트 박스 목록"""
        return self.ocr_result.boxes

    @property
    def confidence(self) -> float:
        """신뢰도"""
        return self.ocr_result.confidence


@dataclass
class WorkerStats:
    """워커 성능 통계"""
    total_frames: int = 0              # 처리한 총 프레임 수
    total_ocr_time_ms: float = 0.0     # 총 OCR 시간 (ms)
    total_capture_time_ms: float = 0.0  # 총 캡처 시간 (ms)
    stabilized_count: int = 0          # 안정화 횟수
    error_count: int = 0               # 오류 횟수
    start_time: float = 0.0            # 시작 시간

    @property
    def avg_ocr_time_ms(self) -> float:
        """평균 OCR 시간"""
        if self.total_frames == 0:
            return 0.0
        return self.total_ocr_time_ms / self.total_frames

    @property
    def avg_capture_time_ms(self) -> float:
        """평균 캡처 시간"""
        if self.total_frames == 0:
            return 0.0
        return self.total_capture_time_ms / self.total_frames

    @property
    def fps(self) -> float:
        """실제 FPS"""
        if self.start_time == 0 or self.total_frames == 0:
            return 0.0
        elapsed = time.time() - self.start_time
        return self.total_frames / elapsed if elapsed > 0 else 0.0

    @property
    def uptime_seconds(self) -> float:
        """실행 시간 (초)"""
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "total_frames": self.total_frames,
            "avg_ocr_time_ms": round(self.avg_ocr_time_ms, 2),
            "avg_capture_time_ms": round(self.avg_capture_time_ms, 2),
            "fps": round(self.fps, 2),
            "stabilized_count": self.stabilized_count,
            "error_count": self.error_count,
            "uptime_seconds": round(self.uptime_seconds, 1)
        }


class TextStabilizer:
    """
    텍스트 안정화 로직

    연속된 OCR 결과에서 텍스트가 일정 시간 동안 동일하면
    안정화된 것으로 판단합니다.

    로직:
    1. 매 OCR 결과마다 텍스트 비교
    2. 텍스트가 이전과 동일하면 타이머 유지
    3. stabilization_time 이상 동일하면 안정화 신호 발생
    4. 텍스트가 변경되면 타이머 리셋
    5. 이미 처리한 텍스트는 중복 처리 방지
    """

    def __init__(
        self,
        stabilization_time: float = 1.5,
        history_size: int = 20,
        similarity_threshold: float = 0.95
    ):
        """
        Args:
            stabilization_time: 안정화 판단 시간 (초)
            history_size: 히스토리 크기 (중복 방지용)
            similarity_threshold: 유사도 임계값 (0.0~1.0)
        """
        self._stabilization_time = stabilization_time
        self._similarity_threshold = similarity_threshold

        # 현재 추적 중인 텍스트
        self._current_text: str = ""
        self._current_result: Optional[OCRResult] = None
        self._first_seen_time: float = 0.0
        self._is_stabilized: bool = False

        # 중복 방지용 히스토리
        self._history: deque = deque(maxlen=history_size)

        # 스레드 안전을 위한 락
        self._lock = Lock()

    @property
    def stabilization_time(self) -> float:
        return self._stabilization_time

    @stabilization_time.setter
    def stabilization_time(self, value: float) -> None:
        self._stabilization_time = max(0.1, value)

    def process(self, result: OCRResult) -> Optional[StabilizedText]:
        """
        OCR 결과 처리

        Args:
            result: OCR 결과

        Returns:
            StabilizedText: 안정화된 경우 반환
            None: 아직 안정화되지 않음
        """
        with self._lock:
            current_text = self._normalize_text(result.text)
            current_time = time.time()

            # 빈 텍스트는 무시
            if not current_text:
                self._reset()
                return None

            # 텍스트 비교
            if self._is_similar(current_text, self._current_text):
                # 텍스트가 동일 (또는 유사)
                stable_duration = current_time - self._first_seen_time

                if stable_duration >= self._stabilization_time and not self._is_stabilized:
                    # 안정화 조건 충족
                    if current_text not in self._history:
                        self._history.append(current_text)
                        self._is_stabilized = True

                        return StabilizedText(
                            text=current_text,
                            stable_duration=stable_duration,
                            ocr_result=result
                        )
            else:
                # 텍스트가 변경됨 - 새로운 추적 시작
                self._current_text = current_text
                self._current_result = result
                self._first_seen_time = current_time
                self._is_stabilized = False

            return None

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화 (비교용)"""
        if not text:
            return ""

        # 공백 정규화
        normalized = " ".join(text.split())

        # 소문자 변환 (선택적)
        # normalized = normalized.lower()

        return normalized.strip()

    def _is_similar(self, text1: str, text2: str) -> bool:
        """
        두 텍스트가 유사한지 확인

        완전 일치가 아닌 유사도 기반 비교로
        OCR의 작은 오류를 허용합니다.
        """
        if not text1 or not text2:
            return text1 == text2

        if text1 == text2:
            return True

        # 길이 차이가 너무 크면 다른 텍스트
        len_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))
        if len_ratio < 0.8:
            return False

        # 간단한 유사도 계산 (Jaccard 유사도)
        set1 = set(text1.split())
        set2 = set(text2.split())

        if not set1 or not set2:
            return False

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        similarity = intersection / union

        return similarity >= self._similarity_threshold

    def _reset(self) -> None:
        """상태 초기화"""
        self._current_text = ""
        self._current_result = None
        self._first_seen_time = 0.0
        self._is_stabilized = False

    def clear_history(self) -> None:
        """히스토리 초기화 (같은 텍스트 다시 처리 가능)"""
        with self._lock:
            self._history.clear()
            self._reset()

    def get_current_state(self) -> dict:
        """현재 상태 반환"""
        with self._lock:
            elapsed = time.time() - self._first_seen_time if self._first_seen_time > 0 else 0
            return {
                "current_text": self._current_text[:50] if self._current_text else "",
                "elapsed_seconds": round(elapsed, 2),
                "is_stabilized": self._is_stabilized,
                "remaining_seconds": max(0, self._stabilization_time - elapsed)
            }


class OCRWorker:
    """
    고성능 OCR 워커

    백그라운드 스레드에서 주기적으로 화면을 캡처하고 OCR을 수행합니다.
    텍스트가 일정 시간(기본 1.5초) 동안 동일하면 번역 신호를 발생시킵니다.

    사용 예시:
        from core.capture import ScreenCapture
        from core.ocr import RapidOCREngine

        capture = ScreenCapture()
        engine = RapidOCREngine()
        worker = OCRWorker(engine, capture)

        worker.on_text_stabilized = lambda s: print(f"번역 요청: {s.text}")
        worker.start()
    """

    # 기본 설정
    DEFAULT_INTERVAL = 0.5            # OCR 실행 간격 (초)
    DEFAULT_STABILIZATION_TIME = 1.5  # 텍스트 안정화 시간 (초)

    def __init__(
        self,
        ocr_engine: OCREngine,
        capture_callback: Optional[Callable[[], Optional[np.ndarray]]] = None,
        interval: float = DEFAULT_INTERVAL,
        stabilization_time: float = DEFAULT_STABILIZATION_TIME
    ):
        """
        Args:
            ocr_engine: OCR 엔진 인스턴스
            capture_callback: 화면 캡처 콜백 함수
            interval: OCR 실행 간격 (초)
            stabilization_time: 텍스트 안정화 시간 (초)
        """
        self._ocr_engine = ocr_engine
        self._capture_callback = capture_callback
        self._interval = interval

        # 스레드 관련
        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self._pause_event = Event()
        self._pause_event.set()  # 초기 상태: 실행 중

        # 텍스트 안정화
        self._stabilizer = TextStabilizer(stabilization_time=stabilization_time)

        # 성능 통계
        self._stats = WorkerStats()
        self._stats_lock = Lock()

        # 상태
        self._state = WorkerState.STOPPED
        self._last_result: Optional[OCRResult] = None

        # 콜백 함수들
        self.on_ocr_result: Optional[Callable[[OCRResult], None]] = None
        self.on_text_stabilized: Optional[Callable[[StabilizedText], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_state_changed: Optional[Callable[[WorkerState], None]] = None

    # === 속성 ===

    @property
    def state(self) -> WorkerState:
        """현재 상태"""
        return self._state

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, value: float) -> None:
        self._interval = max(0.1, value)  # 최소 0.1초

    @property
    def stabilization_time(self) -> float:
        return self._stabilizer.stabilization_time

    @stabilization_time.setter
    def stabilization_time(self, value: float) -> None:
        self._stabilizer.stabilization_time = value

    @property
    def stats(self) -> WorkerStats:
        return self._stats

    @property
    def last_result(self) -> Optional[OCRResult]:
        return self._last_result

    # === 캡처 콜백 ===

    def set_capture_callback(self, callback: Callable[[], Optional[np.ndarray]]) -> None:
        """화면 캡처 콜백 설정"""
        self._capture_callback = callback

    # === 제어 메서드 ===

    def start(self) -> None:
        """워커 시작"""
        if self.is_running:
            return

        # 초기화
        self._ocr_engine.initialize()
        self._stop_event.clear()
        self._pause_event.set()
        self._stats = WorkerStats(start_time=time.time())
        self._stabilizer.clear_history()

        # 스레드 시작
        self._thread = Thread(target=self._run_loop, daemon=True, name="OCRWorker")
        self._thread.start()

        self._set_state(WorkerState.RUNNING)

    def stop(self) -> None:
        """워커 중지"""
        self._stop_event.set()
        self._pause_event.set()  # pause 상태에서도 종료되도록

        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

        self._ocr_engine.cleanup()
        self._set_state(WorkerState.STOPPED)

    def pause(self) -> None:
        """일시 정지"""
        self._pause_event.clear()
        self._set_state(WorkerState.PAUSED)

    def resume(self) -> None:
        """재개"""
        self._pause_event.set()
        self._set_state(WorkerState.RUNNING)

    def reset_stats(self) -> None:
        """통계 초기화"""
        with self._stats_lock:
            self._stats = WorkerStats(start_time=time.time())

    def clear_stabilization_history(self) -> None:
        """안정화 히스토리 초기화"""
        self._stabilizer.clear_history()

    # === 내부 메서드 ===

    def _set_state(self, state: WorkerState) -> None:
        """상태 변경 및 콜백 호출"""
        self._state = state
        if self.on_state_changed:
            try:
                self.on_state_changed(state)
            except Exception:
                pass

    def _run_loop(self) -> None:
        """메인 처리 루프"""
        while not self._stop_event.is_set():
            # 일시 정지 상태면 대기
            self._pause_event.wait(timeout=0.1)

            if self._stop_event.is_set():
                break

            if not self._pause_event.is_set():
                continue

            # 프레임 처리
            loop_start = time.perf_counter()

            try:
                self._process_frame()
            except Exception as e:
                self._handle_error(e)

            # 간격 조절 (처리 시간 고려)
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, self._interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _process_frame(self) -> None:
        """단일 프레임 처리"""
        if not self._capture_callback:
            return

        # 1. 화면 캡처
        capture_start = time.perf_counter()
        image = self._capture_callback()
        capture_time = (time.perf_counter() - capture_start) * 1000

        if image is None:
            return

        # 2. OCR 수행
        ocr_start = time.perf_counter()
        result = self._ocr_engine.recognize(image)
        ocr_time = (time.perf_counter() - ocr_start) * 1000

        self._last_result = result

        # 3. 통계 업데이트
        with self._stats_lock:
            self._stats.total_frames += 1
            self._stats.total_capture_time_ms += capture_time
            self._stats.total_ocr_time_ms += ocr_time

        # 4. OCR 결과 콜백
        if self.on_ocr_result:
            try:
                self.on_ocr_result(result)
            except Exception as e:
                self._handle_error(e)

        # 5. 텍스트 안정화 체크
        stabilized = self._stabilizer.process(result)

        if stabilized:
            with self._stats_lock:
                self._stats.stabilized_count += 1

            # 안정화 콜백 (번역 요청 신호)
            if self.on_text_stabilized:
                try:
                    self.on_text_stabilized(stabilized)
                except Exception as e:
                    self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """오류 처리"""
        with self._stats_lock:
            self._stats.error_count += 1

        if self.on_error:
            try:
                self.on_error(error)
            except Exception:
                pass

    # === 정보 조회 ===

    def get_stabilizer_state(self) -> dict:
        """안정화 상태 조회"""
        return self._stabilizer.get_current_state()

    def get_stats_dict(self) -> dict:
        """통계 딕셔너리 조회"""
        with self._stats_lock:
            return self._stats.to_dict()

    def __repr__(self) -> str:
        return (
            f"OCRWorker(state={self._state.value}, "
            f"interval={self._interval}s, "
            f"frames={self._stats.total_frames})"
        )
