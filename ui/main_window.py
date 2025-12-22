"""
메인 윈도우 - 애플리케이션 컨트롤 센터

게임 선택, 시작/정지, 설정 접근 등 주요 기능 제공
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QSystemTrayIcon,
    QMenu, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from ui.overlay import OverlayWindow
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """메인 컨트롤 윈도우"""

    # 시그널 정의
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    game_changed = pyqtSignal(int)  # game_id
    history_requested = pyqtSignal()  # 히스토리 열기 요청
    glossary_requested = pyqtSignal()  # 용어집 열기 요청

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._overlay: Optional[OverlayWindow] = None
        self._is_running = False

        self._setup_ui()
        self._setup_tray()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """UI 구성"""
        self.setWindowTitle("Auto-Trans")
        self.setMinimumSize(400, 200)

        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 게임 선택
        game_layout = QHBoxLayout()
        game_layout.addWidget(QLabel("게임:"))
        self._game_combo = QComboBox()
        self._game_combo.setMinimumWidth(200)
        game_layout.addWidget(self._game_combo)
        self._add_game_btn = QPushButton("+")
        self._add_game_btn.setFixedWidth(30)
        game_layout.addWidget(self._add_game_btn)
        game_layout.addStretch()
        layout.addLayout(game_layout)

        # 컨트롤 버튼
        control_layout = QHBoxLayout()
        self._start_btn = QPushButton("시작")
        self._start_btn.setMinimumHeight(40)
        control_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("정지")
        self._stop_btn.setMinimumHeight(40)
        self._stop_btn.setEnabled(False)
        control_layout.addWidget(self._stop_btn)
        layout.addLayout(control_layout)

        # 상태 표시
        self._status_label = QLabel("대기 중")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        layout.addStretch()

        # 하단 버튼
        bottom_layout = QHBoxLayout()
        self._settings_btn = QPushButton("설정")
        bottom_layout.addWidget(self._settings_btn)
        self._history_btn = QPushButton("히스토리")
        bottom_layout.addWidget(self._history_btn)
        self._glossary_btn = QPushButton("용어집")
        bottom_layout.addWidget(self._glossary_btn)
        layout.addLayout(bottom_layout)

        # 상태바
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

    def _setup_tray(self) -> None:
        """시스템 트레이 설정"""
        self._tray = QSystemTrayIcon(self)
        # TODO: 아이콘 설정
        # self._tray.setIcon(QIcon("resources/icon.png"))

        tray_menu = QMenu()
        show_action = QAction("열기", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        quit_action = QAction("종료", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        # self._tray.show()

    def _connect_signals(self) -> None:
        """시그널 연결"""
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._settings_btn.clicked.connect(self._show_settings)
        self._game_combo.currentIndexChanged.connect(self._on_game_changed)
        self._history_btn.clicked.connect(self._on_history_clicked)
        self._glossary_btn.clicked.connect(self._on_glossary_clicked)

    def _on_history_clicked(self) -> None:
        """히스토리 버튼 클릭"""
        self.history_requested.emit()

    def _on_glossary_clicked(self) -> None:
        """용어집 버튼 클릭"""
        self.glossary_requested.emit()

    def _on_start_clicked(self) -> None:
        """시작 버튼 클릭"""
        self._is_running = True
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_label.setText("실행 중...")
        self.start_requested.emit()

    def _on_stop_clicked(self) -> None:
        """정지 버튼 클릭"""
        self._is_running = False
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_label.setText("대기 중")
        self.stop_requested.emit()

    def _on_game_changed(self, index: int) -> None:
        """게임 선택 변경"""
        game_id = self._game_combo.currentData()
        if game_id is not None:
            self.game_changed.emit(game_id)

    def _show_settings(self) -> None:
        """설정 다이얼로그 표시"""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """트레이 아이콘 클릭"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def _quit_app(self) -> None:
        """애플리케이션 종료"""
        self.stop_requested.emit()
        self.close()

    def set_games(self, games: list[tuple[int, str]]) -> None:
        """게임 목록 설정"""
        self._game_combo.clear()
        for game_id, name in games:
            self._game_combo.addItem(name, game_id)

    def update_status(self, message: str) -> None:
        """상태 메시지 업데이트"""
        self._status_label.setText(message)
        self._statusbar.showMessage(message, 3000)

    def show_overlay(self) -> None:
        """오버레이 표시"""
        if self._overlay is None:
            self._overlay = OverlayWindow()
        self._overlay.show()

    def hide_overlay(self) -> None:
        """오버레이 숨김"""
        if self._overlay:
            self._overlay.hide()

    def closeEvent(self, event) -> None:
        """창 닫기 이벤트"""
        # 트레이로 최소화
        # self.hide()
        # event.ignore()
        event.accept()
