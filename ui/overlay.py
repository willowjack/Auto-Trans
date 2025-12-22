"""
오버레이 윈도우 - 번역 결과 표시

게임 화면 위에 반투명하게 번역 결과를 표시합니다.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette


class OverlayWindow(QWidget):
    """번역 결과 오버레이 윈도우"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._drag_position: Optional[QPoint] = None

        self._setup_ui()
        self._setup_window_flags()

    def _setup_window_flags(self) -> None:
        """윈도우 플래그 설정"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _setup_ui(self) -> None:
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 번역 텍스트 레이블
        self._text_label = QLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # 스타일 설정
        self._text_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 15px;
                border-radius: 8px;
                font-size: 14px;
            }
        """)

        font = QFont()
        font.setPointSize(12)
        self._text_label.setFont(font)

        layout.addWidget(self._text_label)

        # 기본 크기
        self.setMinimumSize(300, 100)
        self.resize(400, 150)

    def set_text(self, text: str) -> None:
        """번역 텍스트 설정"""
        self._text_label.setText(text)
        self.adjustSize()

    def set_original_and_translated(self, original: str, translated: str) -> None:
        """원본과 번역문 함께 표시"""
        html = f"""
        <div style='color: #888; font-size: 11px; margin-bottom: 5px;'>{original}</div>
        <div style='color: white; font-size: 14px;'>{translated}</div>
        """
        self._text_label.setText(html)
        self.adjustSize()

    def set_position(self, x: int, y: int) -> None:
        """위치 설정"""
        self.move(x, y)

    def set_opacity(self, opacity: float) -> None:
        """투명도 설정 (0.0 ~ 1.0)"""
        self.setWindowOpacity(opacity)

    def set_font_size(self, size: int) -> None:
        """폰트 크기 설정"""
        font = self._text_label.font()
        font.setPointSize(size)
        self._text_label.setFont(font)

    # 드래그로 이동 가능하게
    def mousePressEvent(self, event) -> None:
        """마우스 누름 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """마우스 이동 이벤트"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """마우스 릴리스 이벤트"""
        self._drag_position = None

    def mouseDoubleClickEvent(self, event) -> None:
        """더블클릭 - 숨김"""
        self.hide()
