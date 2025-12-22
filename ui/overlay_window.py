"""
오버레이 윈도우 - 번역 결과 표시 (강화 버전)

기능:
- 투명 배경, Frameless, Always on Top
- OCR 좌표 기반 텍스트 표시
- Auto-sizing (Word-wrap 적용)
- 마우스 드래그 이동
- 스타일 설정 (폰트, 색상, 투명도)
"""

from typing import Optional, List
from dataclasses import dataclass
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QFontMetrics


@dataclass
class OverlayStyle:
    """오버레이 스타일 설정"""
    font_family: str = "맑은 고딕"
    font_size: int = 14
    text_color: str = "#FFFFFF"
    background_color: str = "#000000"
    background_opacity: int = 180  # 0-255
    border_radius: int = 8
    padding: int = 15
    show_original: bool = False
    original_color: str = "#888888"
    original_size: int = 11
    shadow_enabled: bool = True
    shadow_blur: int = 10
    shadow_color: str = "#000000"
    max_width: int = 600
    min_width: int = 200


@dataclass
class TextPosition:
    """텍스트 위치 정보"""
    x: int
    y: int
    width: int
    height: int
    text: str
    translated: str = ""


class TranslationLabel(QLabel):
    """번역 텍스트를 표시하는 레이블"""

    def __init__(self, style: OverlayStyle, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._style = style
        self._original_text = ""
        self._translated_text = ""
        self._apply_style()

    def _apply_style(self) -> None:
        """스타일 적용"""
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # 폰트 설정
        font = QFont(self._style.font_family)
        font.setPointSize(self._style.font_size)
        self.setFont(font)

        # 최대/최소 너비
        self.setMinimumWidth(self._style.min_width)
        self.setMaximumWidth(self._style.max_width)

        # 스타일시트
        bg_color = QColor(self._style.background_color)
        bg_rgba = f"rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, {self._style.background_opacity})"

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_rgba};
                color: {self._style.text_color};
                padding: {self._style.padding}px;
                border-radius: {self._style.border_radius}px;
            }}
        """)

        # 그림자 효과
        if self._style.shadow_enabled:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(self._style.shadow_blur)
            shadow.setColor(QColor(self._style.shadow_color))
            shadow.setOffset(2, 2)
            self.setGraphicsEffect(shadow)

    def set_style(self, style: OverlayStyle) -> None:
        """스타일 변경"""
        self._style = style
        self._apply_style()
        self._update_display()

    def set_text_content(self, original: str, translated: str) -> None:
        """텍스트 설정"""
        self._original_text = original
        self._translated_text = translated
        self._update_display()

    def _update_display(self) -> None:
        """디스플레이 업데이트"""
        if self._style.show_original and self._original_text:
            html = f"""
            <div style='color: {self._style.original_color}; font-size: {self._style.original_size}px; margin-bottom: 5px;'>{self._original_text}</div>
            <div style='color: {self._style.text_color}; font-size: {self._style.font_size}px;'>{self._translated_text}</div>
            """
            self.setText(html)
        else:
            self.setText(self._translated_text)

        self.adjustSize()

    @property
    def translated_text(self) -> str:
        return self._translated_text


class OverlayWindow(QWidget):
    """
    번역 결과 오버레이 윈도우

    투명 배경으로 게임 화면 위에 번역 결과를 표시합니다.

    Signals:
        position_changed: 위치 변경 시
        style_changed: 스타일 변경 시
        text_clicked: 텍스트 클릭 시 (원본 텍스트 전달)
    """

    # 시그널 정의
    position_changed = pyqtSignal(int, int)
    style_changed = pyqtSignal(OverlayStyle)
    text_clicked = pyqtSignal(str, str)  # (original, translated)
    edit_requested = pyqtSignal(str, str)  # 편집 요청 (original, translated)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._drag_position: Optional[QPoint] = None
        self._style = OverlayStyle()
        self._current_original = ""
        self._current_translated = ""

        self._setup_window_flags()
        self._setup_ui()

    def _setup_window_flags(self) -> None:
        """윈도우 플래그 설정"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def _setup_ui(self) -> None:
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        # 번역 텍스트 레이블
        self._text_label = TranslationLabel(self._style)
        layout.addWidget(self._text_label)

        # 기본 크기
        self.setMinimumSize(self._style.min_width, 50)

    # === 텍스트 설정 ===

    def set_text(self, text: str) -> None:
        """번역 텍스트만 설정"""
        self._current_translated = text
        self._text_label.set_text_content("", text)
        self._adjust_size()

    def set_original_and_translated(self, original: str, translated: str) -> None:
        """원본과 번역문 함께 표시"""
        self._current_original = original
        self._current_translated = translated
        self._text_label.set_text_content(original, translated)
        self._adjust_size()

    def update_translation(self, original: str, new_translated: str) -> None:
        """
        번역 업데이트 (히스토리 에디터에서 호출)

        현재 표시 중인 텍스트와 원본이 일치하면 번역을 업데이트합니다.
        """
        if self._current_original == original:
            self._current_translated = new_translated
            self._text_label.set_text_content(original, new_translated)
            self._adjust_size()

    def clear(self) -> None:
        """텍스트 클리어"""
        self._current_original = ""
        self._current_translated = ""
        self._text_label.set_text_content("", "")

    def _adjust_size(self) -> None:
        """크기 자동 조정"""
        self._text_label.adjustSize()
        self.adjustSize()

    # === 스타일 설정 ===

    def set_style(self, style: OverlayStyle) -> None:
        """스타일 설정"""
        self._style = style
        self._text_label.set_style(style)
        self.style_changed.emit(style)

    def get_style(self) -> OverlayStyle:
        """현재 스타일 반환"""
        return self._style

    def set_font_size(self, size: int) -> None:
        """폰트 크기 설정"""
        self._style.font_size = size
        self._text_label.set_style(self._style)

    def set_font_family(self, family: str) -> None:
        """폰트 패밀리 설정"""
        self._style.font_family = family
        self._text_label.set_style(self._style)

    def set_text_color(self, color: str) -> None:
        """텍스트 색상 설정"""
        self._style.text_color = color
        self._text_label.set_style(self._style)

    def set_background_color(self, color: str, opacity: int = 180) -> None:
        """배경 색상 설정"""
        self._style.background_color = color
        self._style.background_opacity = opacity
        self._text_label.set_style(self._style)

    def set_opacity(self, opacity: float) -> None:
        """윈도우 전체 투명도 설정 (0.0 ~ 1.0)"""
        self.setWindowOpacity(opacity)

    def set_show_original(self, show: bool) -> None:
        """원문 표시 여부 설정"""
        self._style.show_original = show
        self._text_label.set_style(self._style)

    # === 위치 설정 ===

    def set_position(self, x: int, y: int) -> None:
        """위치 설정"""
        self.move(x, y)
        self.position_changed.emit(x, y)

    def move_to_ocr_position(self, x: int, y: int, width: int = 0, height: int = 0) -> None:
        """OCR 좌표 기준으로 이동"""
        # OCR 영역 아래에 표시
        offset_y = height + 5 if height > 0 else 0
        self.move(x, y + offset_y)

    def center_on_screen(self) -> None:
        """화면 중앙으로 이동"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.width()) // 2
            y = screen_geo.height() - self.height() - 100  # 하단에서 100px 위
            self.move(x, y)

    # === 마우스 이벤트 (드래그 이동) ===

    def mousePressEvent(self, event) -> None:
        """마우스 누름 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """마우스 이동 이벤트 (드래그)"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            new_pos = event.globalPosition().toPoint() - self._drag_position
            self.move(new_pos)
            self.position_changed.emit(new_pos.x(), new_pos.y())
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """마우스 릴리스 이벤트"""
        self._drag_position = None

    def mouseDoubleClickEvent(self, event) -> None:
        """더블클릭 - 편집 요청"""
        if self._current_original or self._current_translated:
            self.edit_requested.emit(self._current_original, self._current_translated)

    def contextMenuEvent(self, event) -> None:
        """우클릭 메뉴"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction

        menu = QMenu(self)

        # 복사
        copy_action = QAction("번역 복사", self)
        copy_action.triggered.connect(self._copy_translated)
        menu.addAction(copy_action)

        if self._current_original:
            copy_orig_action = QAction("원문 복사", self)
            copy_orig_action.triggered.connect(self._copy_original)
            menu.addAction(copy_orig_action)

        menu.addSeparator()

        # 편집
        edit_action = QAction("편집...", self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(
            self._current_original, self._current_translated
        ))
        menu.addAction(edit_action)

        menu.addSeparator()

        # 숨김
        hide_action = QAction("숨기기", self)
        hide_action.triggered.connect(self.hide)
        menu.addAction(hide_action)

        menu.exec(event.globalPos())

    def _copy_translated(self) -> None:
        """번역문 복사"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._current_translated)

    def _copy_original(self) -> None:
        """원문 복사"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._current_original)

    # === 애니메이션 ===

    def fade_in(self, duration: int = 200) -> None:
        """페이드 인"""
        self.setWindowOpacity(0)
        self.show()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(duration)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def fade_out(self, duration: int = 200) -> None:
        """페이드 아웃"""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(duration)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    # === 프로퍼티 ===

    @property
    def current_original(self) -> str:
        """현재 원문"""
        return self._current_original

    @property
    def current_translated(self) -> str:
        """현재 번역문"""
        return self._current_translated
