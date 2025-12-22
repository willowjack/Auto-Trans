"""
영역 선택기 - 마우스 드래그로 화면 영역(ROI) 선택

사용법:
    selector = RegionSelector()
    selector.region_selected.connect(handle_region)
    selector.show()
"""

from typing import Optional, Tuple
from PyQt6.QtWidgets import QWidget, QApplication, QLabel
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QScreen, QPixmap, QCursor


class RegionSelector(QWidget):
    """
    화면 영역 선택 위젯

    전체화면 오버레이를 띄우고 마우스 드래그로 영역을 선택합니다.

    Signals:
        region_selected(x, y, width, height): 영역 선택 완료
        selection_cancelled(): 선택 취소 (ESC)
    """

    region_selected = pyqtSignal(int, int, int, int)
    selection_cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_selecting = False
        self._screenshot: Optional[QPixmap] = None

        self._setup_window()
        self._capture_screen()

    def _setup_window(self) -> None:
        """윈도우 설정"""
        # 전체 화면 오버레이
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # 전체 화면 크기로 설정
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            self.setGeometry(geometry)

    def _capture_screen(self) -> None:
        """현재 화면 캡처"""
        screen = QApplication.primaryScreen()
        if screen:
            self._screenshot = screen.grabWindow(0)

    def showEvent(self, event) -> None:
        """표시 시 화면 캡처"""
        super().showEvent(event)
        self._capture_screen()
        self.update()

    def paintEvent(self, event) -> None:
        """화면 그리기"""
        painter = QPainter(self)

        # 스크린샷 배경
        if self._screenshot:
            painter.drawPixmap(0, 0, self._screenshot)

        # 어두운 오버레이
        painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

        # 선택 영역
        if self._start_pos and self._current_pos:
            selection_rect = self._get_selection_rect()

            # 선택 영역은 밝게 (원본 표시)
            if self._screenshot:
                painter.drawPixmap(selection_rect, self._screenshot, selection_rect)

            # 테두리
            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(selection_rect)

            # 크기 표시
            if selection_rect.width() > 50 and selection_rect.height() > 20:
                size_text = f"{selection_rect.width()} x {selection_rect.height()}"
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)

                # 배경
                text_rect = painter.fontMetrics().boundingRect(size_text)
                bg_rect = QRect(
                    selection_rect.left() + 5,
                    selection_rect.top() + 5,
                    text_rect.width() + 10,
                    text_rect.height() + 6
                )
                painter.setBrush(QBrush(QColor(0, 120, 215)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg_rect, 3, 3)

                # 텍스트
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, size_text)

        # 안내 텍스트
        painter.setPen(QColor(255, 255, 255))
        font = QFont()
        font.setPointSize(14)
        painter.setFont(font)

        help_text = "드래그로 영역 선택 | ESC: 취소"
        text_rect = painter.fontMetrics().boundingRect(help_text)

        # 상단 중앙에 표시
        x = (self.width() - text_rect.width()) // 2
        y = 50

        # 배경
        bg = QRect(x - 15, y - 25, text_rect.width() + 30, text_rect.height() + 20)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bg, 8, 8)

        # 텍스트
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(x, y, help_text)

    def mousePressEvent(self, event) -> None:
        """마우스 누름"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        """마우스 이동"""
        if self._is_selecting:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """마우스 릴리스"""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            rect = self._get_selection_rect()

            if rect.width() > 10 and rect.height() > 10:
                self.region_selected.emit(
                    rect.x(), rect.y(),
                    rect.width(), rect.height()
                )
            else:
                # 너무 작은 영역은 무시
                self._start_pos = None
                self._current_pos = None
                self.update()
                return

            self.close()

    def keyPressEvent(self, event) -> None:
        """키보드 입력"""
        if event.key() == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()

    def _get_selection_rect(self) -> QRect:
        """선택 영역 사각형 반환"""
        if not self._start_pos or not self._current_pos:
            return QRect()

        return QRect(
            min(self._start_pos.x(), self._current_pos.x()),
            min(self._start_pos.y(), self._current_pos.y()),
            abs(self._current_pos.x() - self._start_pos.x()),
            abs(self._current_pos.y() - self._start_pos.y())
        )


class RegionIndicator(QWidget):
    """
    선택된 영역 표시 위젯

    현재 캡처 영역을 화면에 표시합니다.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._region: Optional[QRect] = None

    def set_region(self, x: int, y: int, width: int, height: int) -> None:
        """영역 설정"""
        self._region = QRect(x, y, width, height)
        self.setGeometry(x - 3, y - 3, width + 6, height + 6)
        self.update()

    def paintEvent(self, event) -> None:
        """그리기"""
        if not self._region:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 테두리
        pen = QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(2, 2, self.width() - 4, self.height() - 4)

        # 모서리 표시
        corner_size = 10
        pen = QPen(QColor(0, 120, 215), 3)
        painter.setPen(pen)

        # 좌상단
        painter.drawLine(2, 2, 2 + corner_size, 2)
        painter.drawLine(2, 2, 2, 2 + corner_size)

        # 우상단
        painter.drawLine(self.width() - 2, 2, self.width() - 2 - corner_size, 2)
        painter.drawLine(self.width() - 2, 2, self.width() - 2, 2 + corner_size)

        # 좌하단
        painter.drawLine(2, self.height() - 2, 2 + corner_size, self.height() - 2)
        painter.drawLine(2, self.height() - 2, 2, self.height() - 2 - corner_size)

        # 우하단
        painter.drawLine(self.width() - 2, self.height() - 2,
                         self.width() - 2 - corner_size, self.height() - 2)
        painter.drawLine(self.width() - 2, self.height() - 2,
                         self.width() - 2, self.height() - 2 - corner_size)
