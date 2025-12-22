"""
OCR 워커 - 백그라운드 OCR 처리 스레드

화면 캡처 → OCR 인식 → 텍스트 안정화 처리
"""

import time
from typing import Optional, Callable
from threading import Thread, Event
from dataclasses import dataclass
from collections import deque

import numpy as np

from core.interfaces.ocr_engine import OCREngine, OCRResult


@dataclass
class StabilizedText:
    """안정화된 텍스트 결과"""
    text: str
    stable_duration: float  # 텍스트가 동일하게 유지된 시간 (초)
    ocr_result: OCRResult


class OCRWorker:
    """
    OCR 워커 스레드

    주기적으로 화면을 캡처하고 OCR을 수행합니다.
    텍스트가 일정 시간(기본 1.5초) 동안 동일하면 안정화된 것으로 판단합니다.

    사용 예시:
        worker = OCRWorker(ocr_engine)
        worker.on_text_stabilized = lambda text: print(text)
        worker.start()
    """

    # 기본 설정
    DEFAULT_INTERVAL = 0.5  # OCR 실행 간격 (초)
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
            capture_callback: 화면 캡처 콜백 (None 반환 시 스킵)
            interval: OCR 실행 간격 (초)
            stabilization_time: 텍스트 안정화 판단 시간 (초)
        """
        self._ocr_engine = ocr_engine
        self._capture_callback = capture_callback
        self._interval = interval
        self._stabilization_time = stabilization_time

        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self._pause_event = Event()
        self._pause_event.set()  # 초기 상태: 실행 중

        # 텍스트 안정화 추적
        self._last_text = ""
        self._last_text_time = 0.0
        self._text_history: deque = deque(maxlen=10)

        # 콜백 함수들
        self.on_ocr_result: Optional[Callable[[OCRResult], None]] = None
        self.on_text_stabilized: Optional[Callable[[StabilizedText], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def set_capture_callback(self, callback: Callable[[], Optional[np.ndarray]]) -> None:
        """화면 캡처 콜백 설정"""
        self._capture_callback = callback

    def start(self) -> None:
        """워커 스레드 시작"""
        if self.is_running:
            return

        self._ocr_engine.initialize()
        self._stop_event.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """워커 스레드 중지"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._ocr_engine.cleanup()

    def pause(self) -> None:
        """일시 정지"""
        self._pause_event.clear()

    def resume(self) -> None:
        """재개"""
        self._pause_event.set()

    def _run(self) -> None:
        """워커 스레드 메인 루프"""
        while not self._stop_event.is_set():
            # 일시 정지 상태면 대기
            self._pause_event.wait()

            if self._stop_event.is_set():
                break

            try:
                self._process_frame()
            except Exception as e:
                if self.on_error:
                    self.on_error(e)

            time.sleep(self._interval)

    def _process_frame(self) -> None:
        """단일 프레임 처리"""
        if not self._capture_callback:
            return

        # 화면 캡처
        image = self._capture_callback()
        if image is None:
            return

        # OCR 수행
        result = self._ocr_engine.recognize(image)

        # OCR 결과 콜백
        if self.on_ocr_result:
            self.on_ocr_result(result)

        # 텍스트 안정화 체크
        self._check_text_stability(result)

    def _check_text_stability(self, result: OCRResult) -> None:
        """텍스트 안정화 확인"""
        current_text = result.text.strip()
        current_time = time.time()

        if current_text == self._last_text:
            # 텍스트가 동일함 - 안정화 시간 체크
            stable_duration = current_time - self._last_text_time

            if stable_duration >= self._stabilization_time:
                # 안정화된 텍스트
                if current_text and current_text not in self._text_history:
                    self._text_history.append(current_text)

                    if self.on_text_stabilized:
                        stabilized = StabilizedText(
                            text=current_text,
                            stable_duration=stable_duration,
                            ocr_result=result
                        )
                        self.on_text_stabilized(stabilized)

                    # 안정화 후 타이머 리셋
                    self._last_text_time = current_time
        else:
            # 텍스트가 변경됨 - 타이머 리셋
            self._last_text = current_text
            self._last_text_time = current_time
