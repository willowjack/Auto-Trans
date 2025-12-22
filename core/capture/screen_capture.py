"""
고성능 화면 캡처 모듈

mss 라이브러리를 사용하여 최적화된 화면 캡처를 수행합니다.
- 메모리 재사용으로 GC 부하 최소화
- BGR/RGB 변환 최적화
- 캡처 영역 관리
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np

try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


@dataclass
class CaptureRegion:
    """캡처 영역 정의"""
    x: int
    y: int
    width: int
    height: int
    monitor_index: int = 0  # 0 = 전체, 1 = 주 모니터, 2+ = 추가 모니터

    def to_mss_monitor(self) -> dict:
        """mss 모니터 딕셔너리로 변환"""
        return {
            "left": self.x,
            "top": self.y,
            "width": self.width,
            "height": self.height
        }

    def contains_point(self, x: int, y: int) -> bool:
        """점이 영역 내에 있는지 확인"""
        return (self.x <= x < self.x + self.width and
                self.y <= y < self.y + self.height)

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """(x, y, width, height) 튜플 반환"""
        return (self.x, self.y, self.width, self.height)

    @classmethod
    def from_tuple(cls, t: Tuple[int, int, int, int], monitor_index: int = 0) -> "CaptureRegion":
        """튜플에서 생성"""
        return cls(x=t[0], y=t[1], width=t[2], height=t[3], monitor_index=monitor_index)

    def __str__(self) -> str:
        return f"Region({self.x}, {self.y}, {self.width}x{self.height})"


class ScreenCapture:
    """
    고성능 화면 캡처 클래스

    특징:
    - mss 인스턴스 재사용으로 오버헤드 최소화
    - numpy 배열 직접 반환 (OpenCV/PIL 호환)
    - 스레드 안전 (각 스레드에서 별도 인스턴스 사용 권장)

    사용 예시:
        capture = ScreenCapture()
        capture.set_region(100, 100, 800, 600)

        with capture:
            while running:
                image = capture.grab()
                if image is not None:
                    process(image)
    """

    def __init__(self):
        if not MSS_AVAILABLE:
            raise ImportError(
                "mss 라이브러리가 설치되지 않았습니다. "
                "'pip install mss' 명령어로 설치하세요."
            )

        self._sct: Optional[mss.mss] = None
        self._region: Optional[CaptureRegion] = None
        self._monitors: list[dict] = []

        # 성능 통계
        self._capture_count: int = 0
        self._total_capture_time: float = 0.0

    @property
    def is_initialized(self) -> bool:
        return self._sct is not None

    @property
    def region(self) -> Optional[CaptureRegion]:
        return self._region

    @property
    def monitors(self) -> list[dict]:
        """사용 가능한 모니터 목록"""
        if self._sct is None:
            self.initialize()
        return self._monitors

    @property
    def avg_capture_time_ms(self) -> float:
        """평균 캡처 시간 (밀리초)"""
        if self._capture_count == 0:
            return 0.0
        return (self._total_capture_time / self._capture_count) * 1000

    def initialize(self) -> None:
        """캡처 초기화"""
        if self._sct is not None:
            return

        self._sct = mss.mss()
        self._monitors = list(self._sct.monitors)
        self._capture_count = 0
        self._total_capture_time = 0.0

    def cleanup(self) -> None:
        """리소스 정리"""
        if self._sct:
            self._sct.close()
            self._sct = None

    def set_region(self, x: int, y: int, width: int, height: int,
                   monitor_index: int = 0) -> None:
        """캡처 영역 설정"""
        self._region = CaptureRegion(
            x=x, y=y, width=width, height=height,
            monitor_index=monitor_index
        )

    def set_region_from_object(self, region: CaptureRegion) -> None:
        """CaptureRegion 객체로 영역 설정"""
        self._region = region

    def clear_region(self) -> None:
        """영역 설정 해제 (전체 화면 캡처)"""
        self._region = None

    def set_monitor(self, monitor_index: int) -> None:
        """특정 모니터 전체를 캡처 영역으로 설정"""
        if not self.is_initialized:
            self.initialize()

        if monitor_index >= len(self._monitors):
            raise ValueError(f"모니터 인덱스 {monitor_index}가 범위를 벗어났습니다.")

        mon = self._monitors[monitor_index]
        self._region = CaptureRegion(
            x=mon["left"],
            y=mon["top"],
            width=mon["width"],
            height=mon["height"],
            monitor_index=monitor_index
        )

    def grab(self, convert_to_bgr: bool = True) -> Optional[np.ndarray]:
        """
        화면 캡처 수행

        Args:
            convert_to_bgr: True면 BGR로 변환 (OpenCV 호환)
                           False면 BGRA 그대로 반환

        Returns:
            numpy.ndarray: 캡처된 이미지 (H, W, 3 or 4)
            None: 캡처 실패 시
        """
        if not self.is_initialized:
            self.initialize()

        import time
        start_time = time.perf_counter()

        try:
            # 캡처 영역 결정
            if self._region:
                monitor = self._region.to_mss_monitor()
            else:
                # 기본: 주 모니터 (인덱스 1)
                monitor = self._sct.monitors[1] if len(self._sct.monitors) > 1 else self._sct.monitors[0]

            # 캡처 수행
            screenshot = self._sct.grab(monitor)

            # numpy 배열로 변환
            # mss는 BGRA 형식으로 반환
            img = np.array(screenshot, dtype=np.uint8)

            if convert_to_bgr:
                # BGRA -> BGR (알파 채널 제거)
                img = img[:, :, :3]

            # 성능 통계 업데이트
            elapsed = time.perf_counter() - start_time
            self._capture_count += 1
            self._total_capture_time += elapsed

            return img

        except Exception as e:
            print(f"[ScreenCapture] 캡처 오류: {e}")
            return None

    def grab_pil(self):
        """PIL Image로 캡처 (UI 표시용)"""
        if not self.is_initialized:
            self.initialize()

        try:
            if self._region:
                monitor = self._region.to_mss_monitor()
            else:
                monitor = self._sct.monitors[1] if len(self._sct.monitors) > 1 else self._sct.monitors[0]

            screenshot = self._sct.grab(monitor)
            return screenshot  # mss.ScreenShot은 PIL 호환

        except Exception as e:
            print(f"[ScreenCapture] 캡처 오류: {e}")
            return None

    def get_monitor_info(self) -> list[dict]:
        """모니터 정보 반환"""
        if not self.is_initialized:
            self.initialize()

        result = []
        for i, mon in enumerate(self._monitors):
            if i == 0:
                continue  # 인덱스 0은 전체 화면
            result.append({
                "index": i,
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
                "is_primary": i == 1
            })
        return result

    def reset_stats(self) -> None:
        """성능 통계 초기화"""
        self._capture_count = 0
        self._total_capture_time = 0.0

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
