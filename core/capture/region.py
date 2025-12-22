"""
캡처 영역 선택 유틸리티

마우스 드래그로 캡처 영역을 선택할 수 있는 기능 제공
"""

from typing import Optional, Callable, Tuple
from dataclasses import dataclass

from PyQt6.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QScreen

from core.capture.screen_capture import CaptureRegion


class RegionSelector(QWidget):
    """
    화면 영역 선택 위젯

    전체 화면을 덮는 반투명 오버레이를 표시하고,
    사용자가 마우스로 드래그하여 영역을 선택할 수 있습니다.

    사용 예시:
        selector = RegionSelector()
        selector.region_selected.connect(on_region_selected)
        selector.start_selection()
    """

    # 시그널: 영역 선택 완료
    region_selected = pyqtSignal(CaptureRegion)
    selection_cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._rubber_band: Optional[QRubberBand] = None
        self._screen_geometry: Optional[QRect] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 설정"""
        # 전체 화면 덮기
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def start_selection(self, screen_index: int = 0) -> None:
        """영역 선택 시작"""
        app = QApplication.instance()
        screens = app.screens()

        if screen_index < len(screens):
            screen = screens[screen_index]
        else:
            screen = app.primaryScreen()

        self._screen_geometry = screen.geometry()

        # 전체 화면 크기로 설정
        self.setGeometry(self._screen_geometry)
        self.showFullScreen()
        self.activateWindow()

    def paintEvent(self, event) -> None:
        """그리기 이벤트"""
        painter = QPainter(self)

        # 반투명 배경
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # 선택 영역이 있으면 해당 부분은 투명하게
        if self._start_pos and self._current_pos:
            rect = self._get_selection_rect()

            # 선택 영역 투명하게 (구멍 뚫기)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)

            # 테두리 그리기
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 크기 표시
            size_text = f"{rect.width()} x {rect.height()}"
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect.x() + 5, rect.y() - 5, size_text)

        # 안내 텍스트
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(20, 30, "마우스로 드래그하여 캡처 영역을 선택하세요. ESC: 취소")

    def mousePressEvent(self, event) -> None:
        """마우스 누름"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self.update()

    def mouseMoveEvent(self, event) -> None:
        """마우스 이동"""
        if self._start_pos:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """마우스 릴리스"""
        if event.button() == Qt.MouseButton.LeftButton and self._start_pos:
            self._current_pos = event.pos()
            rect = self._get_selection_rect()

            # 최소 크기 체크
            if rect.width() > 10 and rect.height() > 10:
                # 스크린 좌표로 변환
                if self._screen_geometry:
                    region = CaptureRegion(
                        x=self._screen_geometry.x() + rect.x(),
                        y=self._screen_geometry.y() + rect.y(),
                        width=rect.width(),
                        height=rect.height()
                    )
                else:
                    region = CaptureRegion(
                        x=rect.x(),
                        y=rect.y(),
                        width=rect.width(),
                        height=rect.height()
                    )

                self.region_selected.emit(region)

            self.close()
            self._reset()

    def keyPressEvent(self, event) -> None:
        """키 입력"""
        if event.key() == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()
            self._reset()

    def _get_selection_rect(self) -> QRect:
        """선택 영역 QRect 반환"""
        if not self._start_pos or not self._current_pos:
            return QRect()

        return QRect(
            min(self._start_pos.x(), self._current_pos.x()),
            min(self._start_pos.y(), self._current_pos.y()),
            abs(self._current_pos.x() - self._start_pos.x()),
            abs(self._current_pos.y() - self._start_pos.y())
        )

    def _reset(self) -> None:
        """상태 초기화"""
        self._start_pos = None
        self._current_pos = None


def select_region_blocking(screen_index: int = 0) -> Optional[CaptureRegion]:
    """
    영역 선택 (블로킹 방식)

    사용자가 영역을 선택할 때까지 대기합니다.

    Returns:
        CaptureRegion: 선택된 영역
        None: 취소됨
    """
    result: list[Optional[CaptureRegion]] = [None]

    def on_selected(region: CaptureRegion):
        result[0] = region

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    selector = RegionSelector()
    selector.region_selected.connect(on_selected)
    selector.start_selection(screen_index)

    # 이벤트 루프 실행 (선택 완료까지)
    while selector.isVisible():
        app.processEvents()

    return result[0]
