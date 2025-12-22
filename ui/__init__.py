"""
UI 모듈 - PyQt6 사용자 인터페이스

- main_window: 메인 컨트롤 윈도우
- overlay_window: 번역 결과 오버레이 (강화 버전)
- history_editor: 히스토리 편집기
- settings_dialog: 설정 다이얼로그
"""

from ui.main_window import MainWindow
from ui.overlay_window import OverlayWindow, OverlayStyle, TranslationLabel
from ui.history_editor import HistoryEditor, HistoryEditorWindow, HistoryItem, EditDialog
from ui.settings_dialog import SettingsDialog

__all__ = [
    "MainWindow",
    "OverlayWindow", "OverlayStyle", "TranslationLabel",
    "HistoryEditor", "HistoryEditorWindow", "HistoryItem", "EditDialog",
    "SettingsDialog"
]
