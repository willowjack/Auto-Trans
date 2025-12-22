#!/usr/bin/env python3
"""
Auto-Trans - 실시간 게임 화면 번역기

통합 진입점 (Entry Point)

기능:
1. 화면 캡처 (ScreenCapture)
2. OCR 인식 (OCRWorker + RapidOCR)
3. 텍스트 안정화 (1.5초)
4. 문맥 인식 번역 (TranslationService + Gemini)
5. 오버레이 표시 (OverlayWindow)
6. 히스토리 편집 (HistoryEditorWindow)
7. 시스템 트레이 (최소화)
8. 예외 처리 및 알림
"""

import sys
import os
import traceback
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor

# 모듈 임포트
from core import OCRWorker, TranslationService
from core.capture import ScreenCapture
from core.ocr import RapidOCREngine
from core.interfaces import TranslationResult
from core.ocr_worker import StabilizedText

from data import Database, GameRepository, HistoryRepository, GlossaryRepository

from ui import MainWindow, OverlayWindow, HistoryEditorWindow, SettingsDialog
from ui.region_selector import RegionSelector

from utils import Config, ensure_dirs


class NotificationManager:
    """알림 관리자"""

    def __init__(self, tray_icon: Optional[QSystemTrayIcon] = None):
        self._tray = tray_icon
        self._error_count = 0
        self._last_error = ""

    def set_tray(self, tray: QSystemTrayIcon) -> None:
        self._tray = tray

    def show_info(self, title: str, message: str) -> None:
        """정보 알림"""
        if self._tray and self._tray.isVisible():
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
        else:
            print(f"[INFO] {title}: {message}")

    def show_warning(self, title: str, message: str) -> None:
        """경고 알림"""
        if self._tray and self._tray.isVisible():
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 5000)
        else:
            print(f"[WARNING] {title}: {message}")

    def show_error(self, title: str, message: str, show_dialog: bool = False) -> None:
        """오류 알림"""
        self._error_count += 1
        self._last_error = message

        if self._tray and self._tray.isVisible():
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Critical, 5000)

        if show_dialog:
            QMessageBox.critical(None, title, message)

        print(f"[ERROR] {title}: {message}")

    def reset_errors(self) -> None:
        self._error_count = 0
        self._last_error = ""


class Application:
    """
    메인 애플리케이션 클래스

    전체 번역 파이프라인을 관리합니다.
    """

    def __init__(self):
        # 알림 관리자
        self.notifications = NotificationManager()

        # 디렉토리 초기화
        ensure_dirs()

        # 설정 로드
        self.config = Config()
        self.config.load()

        # 데이터베이스
        self.db = Database()
        self._init_database()

        # Repositories
        self.game_repo = GameRepository(self.db)
        self.history_repo = HistoryRepository(self.db)
        self.glossary_repo = GlossaryRepository(self.db)

        # 화면 캡처
        self.screen_capture = ScreenCapture()

        # OCR 엔진 및 워커
        self.ocr_engine = RapidOCREngine(
            use_gpu=False,
            print_verbose=False
        )

        self.ocr_worker = OCRWorker(
            ocr_engine=self.ocr_engine,
            capture_callback=self.screen_capture.grab,
            interval=self.config.ocr.interval,
            stabilization_time=self.config.ocr.stabilization_time
        )

        # 번역 서비스 (Gemini + DB 연동)
        api_key = self._get_api_key()
        self.translation_service = TranslationService(
            db=self.db,
            api_key=api_key,
            target_language=self.config.translation.target_language,
            source_language=self.config.translation.source_language,
            use_cache=True
        )

        # UI
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)  # 트레이에서 동작

        # 윈도우 생성
        self.main_window = MainWindow()
        self.overlay = OverlayWindow()
        self.history_editor = HistoryEditorWindow()
        self.settings_dialog: Optional[SettingsDialog] = None
        self.region_selector: Optional[RegionSelector] = None

        # 시스템 트레이
        self._setup_tray()

        # 현재 게임 ID
        self._current_game_id: Optional[int] = None

        # 연결 설정
        self._setup_connections()
        self._setup_ui_connections()
        self._load_games()

        # 캡처 영역 적용
        self._apply_capture_region()

        # 예외 핸들러
        sys.excepthook = self._handle_exception

    def _init_database(self) -> None:
        """데이터베이스 초기화"""
        try:
            self.db.connect()
        except Exception as e:
            self.notifications.show_error(
                "데이터베이스 오류",
                f"데이터베이스 연결 실패: {e}",
                show_dialog=True
            )

    def _get_api_key(self) -> Optional[str]:
        """API 키 가져오기 (설정 또는 환경변수)"""
        # 설정에서 먼저 확인
        if self.config.api.gemini_api_key:
            return self.config.api.gemini_api_key

        # 환경변수에서 확인
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key:
            return env_key

        return None

    def _setup_tray(self) -> None:
        """시스템 트레이 설정"""
        self.tray = QSystemTrayIcon()

        # 기본 아이콘 생성 (텍스트 기반)
        icon = self._create_default_icon()
        self.tray.setIcon(icon)
        self.tray.setToolTip("Auto-Trans - 실시간 번역기")

        # 메뉴
        tray_menu = QMenu()

        # 열기
        show_action = QAction("열기", None)
        show_action.triggered.connect(self._show_main_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        # 시작/정지
        self._tray_start_action = QAction("번역 시작", None)
        self._tray_start_action.triggered.connect(self.start)
        tray_menu.addAction(self._tray_start_action)

        self._tray_stop_action = QAction("번역 정지", None)
        self._tray_stop_action.triggered.connect(self.stop)
        self._tray_stop_action.setEnabled(False)
        tray_menu.addAction(self._tray_stop_action)

        tray_menu.addSeparator()

        # 히스토리
        history_action = QAction("히스토리", None)
        history_action.triggered.connect(self._show_history_editor)
        tray_menu.addAction(history_action)

        # 설정
        settings_action = QAction("설정", None)
        settings_action.triggered.connect(self._show_settings)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        # 종료
        quit_action = QAction("종료", None)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # 알림 관리자에 트레이 설정
        self.notifications.set_tray(self.tray)

    def _create_default_icon(self) -> QIcon:
        """기본 아이콘 생성"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 120, 215))

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x0084, "A")  # AlignCenter
        painter.end()

        return QIcon(pixmap)

    def _setup_connections(self) -> None:
        """시그널 및 콜백 연결"""
        # 메인 윈도우 시그널
        self.main_window.start_requested.connect(self.start)
        self.main_window.stop_requested.connect(self.stop)
        self.main_window.game_changed.connect(self._on_game_changed)

        # OCR 워커 → 번역 서비스 연결
        self.ocr_worker.on_text_stabilized = self.translation_service.handle_stabilized_text
        self.ocr_worker.on_error = self._on_ocr_error

        # 번역 서비스 콜백
        self.translation_service.on_translation_complete = self._on_translation_complete
        self.translation_service.on_translation_start = self._on_translation_start
        self.translation_service.on_error = self._on_translation_error

    def _setup_ui_connections(self) -> None:
        """UI 컴포넌트 간 시그널 연결"""
        # 메인 윈도우 → 히스토리/설정 열기
        self.main_window.history_requested.connect(self._show_history_editor)

        # 메인 윈도우 설정 버튼 연결
        # MainWindow._settings_btn.clicked 이미 _show_settings에 연결되어 있음

        # 히스토리 에디터 → 오버레이 (즉시 반영)
        self.history_editor.overlay_update_requested.connect(
            self._on_overlay_update_from_editor
        )

        # 히스토리 에디터 → 용어집 추가
        self.history_editor.glossary_added.connect(
            self._on_glossary_added
        )

        # 히스토리 에디터 → DB 업데이트
        self.history_editor.translation_edited.connect(
            self._on_translation_edited
        )

        # 오버레이 → 편집 요청
        self.overlay.edit_requested.connect(
            self._on_edit_requested
        )

    def _apply_capture_region(self) -> None:
        """저장된 캡처 영역 적용"""
        if self.config.capture_region.is_set:
            region = self.config.capture_region.as_tuple()
            self.screen_capture.set_region(*region)

    def _show_main_window(self) -> None:
        """메인 윈도우 표시"""
        self.main_window.show()
        self.main_window.activateWindow()

    def _show_history_editor(self) -> None:
        """히스토리 에디터 표시"""
        self.history_editor.show()
        self.history_editor.activateWindow()

    def _show_settings(self) -> None:
        """설정 다이얼로그 표시"""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.config, self.main_window)
            self.settings_dialog.settings_saved.connect(self._on_settings_saved)
            self.settings_dialog.region_select_requested.connect(self._start_region_selection)

        self.settings_dialog.show()

    def _start_region_selection(self) -> None:
        """영역 선택 시작"""
        self.region_selector = RegionSelector()
        self.region_selector.region_selected.connect(self._on_region_selected)
        self.region_selector.selection_cancelled.connect(self._on_region_cancelled)
        self.region_selector.show()

    def _on_region_selected(self, x: int, y: int, w: int, h: int) -> None:
        """영역 선택 완료"""
        # 설정에 저장
        self.config.capture_region.x = x
        self.config.capture_region.y = y
        self.config.capture_region.width = w
        self.config.capture_region.height = h

        # 캡처에 적용
        self.screen_capture.set_region(x, y, w, h)

        # 설정 다이얼로그에 반영
        if self.settings_dialog:
            self.settings_dialog.set_region(x, y, w, h)

        self.notifications.show_info("영역 선택", f"캡처 영역: {w}x{h}")

    def _on_region_cancelled(self) -> None:
        """영역 선택 취소"""
        if self.settings_dialog:
            self.settings_dialog.show()

    def _on_settings_saved(self) -> None:
        """설정 저장됨"""
        # OCR 설정 적용
        self.ocr_worker.interval = self.config.ocr.interval
        self.ocr_worker.stabilization_time = self.config.ocr.stabilization_time

        # 번역 서비스 설정 적용
        self.translation_service.source_language = self.config.translation.source_language
        self.translation_service.target_language = self.config.translation.target_language

        # 캡처 영역 적용
        if self.config.capture_region.is_set:
            region = self.config.capture_region.as_tuple()
            self.screen_capture.set_region(*region)
        else:
            self.screen_capture.set_region(0, 0, 0, 0)  # 전체 화면

        # API 키 업데이트
        new_api_key = self._get_api_key()
        if new_api_key:
            self.translation_service._translator._api_key = new_api_key

        self.notifications.show_info("설정", "설정이 적용되었습니다.")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """트레이 아이콘 활성화"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_main_window()

    def _quit_app(self) -> None:
        """앱 종료"""
        self.stop()
        self.tray.hide()
        self.qt_app.quit()

    def _load_games(self) -> None:
        """게임 목록 로드"""
        try:
            games = self.game_repo.get_all(active_only=True)
            game_list = [(g.id, g.name) for g in games]
            self.main_window.set_games(game_list)
        except Exception as e:
            self.notifications.show_error("데이터베이스 오류", f"게임 목록 로드 실패: {e}")

    def _on_game_changed(self, game_id: int) -> None:
        """게임 선택 변경"""
        self._current_game_id = game_id

        try:
            game = self.game_repo.get_by_id(game_id)

            if game:
                # 캡처 영역 설정
                if game.has_capture_region:
                    region = game.capture_region
                    self.screen_capture.set_region(*region)

                # 번역 서비스에 게임 설정
                self.translation_service.set_game(game_id)
                self.translation_service.source_language = game.source_language
                self.translation_service.target_language = game.target_language

                # OCR 설정 적용
                self.ocr_worker.interval = game.ocr_interval
                self.ocr_worker.stabilization_time = game.stabilization_time

                self.main_window.update_status(f"게임 선택: {game.name}")
        except Exception as e:
            self.notifications.show_error("게임 설정 오류", str(e))

    def _on_translation_start(self, text: str) -> None:
        """번역 시작"""
        preview = text[:30] + "..." if len(text) > 30 else text
        self.main_window.update_status(f"번역 중: {preview}")

    def _on_translation_complete(self, result: TranslationResult) -> None:
        """번역 완료"""
        try:
            # 오버레이 업데이트
            if self.config.overlay.show_original:
                self.overlay.set_original_and_translated(
                    result.original_text,
                    result.translated_text
                )
            else:
                self.overlay.set_text(result.translated_text)

            # 히스토리 에디터에 추가
            self.history_editor.add_entry(result)

            self.main_window.update_status("번역 완료")
        except Exception as e:
            self.notifications.show_error("UI 오류", f"번역 표시 실패: {e}")

    def _on_overlay_update_from_editor(self, original: str, translated: str) -> None:
        """히스토리 에디터에서 오버레이 업데이트 요청"""
        if self.config.overlay.show_original:
            self.overlay.set_original_and_translated(original, translated)
        else:
            self.overlay.set_text(translated)

    def _on_glossary_added(self, original: str, translated: str, category: str) -> None:
        """용어집 추가"""
        try:
            self.translation_service.add_glossary_term(
                original=original,
                translation=translated,
                category=category,
                is_global=False
            )
            self.main_window.update_status(f"용어집 추가: {original} → {translated}")
        except Exception as e:
            self.notifications.show_error("용어집 오류", f"용어집 추가 실패: {e}")

    def _on_translation_edited(self, entry_id: int, original: str, new_translated: str) -> None:
        """번역 수정 → DB 업데이트"""
        try:
            self.history_repo.update_translation(entry_id, new_translated)
            print(f"[Application] 번역 수정 저장: ID={entry_id}")
        except Exception as e:
            self.notifications.show_error("저장 오류", f"번역 수정 저장 실패: {e}")

    def _on_edit_requested(self, original: str, translated: str) -> None:
        """오버레이에서 편집 요청 → 히스토리 에디터 열기"""
        self._show_history_editor()

    def _on_ocr_error(self, error: Exception) -> None:
        """OCR 오류"""
        error_msg = str(error)[:50]
        self.main_window.update_status(f"OCR 오류: {error_msg}")
        self.notifications.show_warning("OCR 오류", error_msg)

    def _on_translation_error(self, error: Exception) -> None:
        """번역 오류"""
        error_msg = str(error)

        # API 키 오류 확인
        if "API_KEY" in error_msg.upper() or "UNAUTHORIZED" in error_msg.upper():
            self.notifications.show_error(
                "API 키 오류",
                "API 키가 설정되지 않았거나 유효하지 않습니다.\n설정에서 API 키를 확인하세요.",
                show_dialog=True
            )
        # 네트워크 오류 확인
        elif "NETWORK" in error_msg.upper() or "CONNECTION" in error_msg.upper():
            self.notifications.show_warning("네트워크 오류", "인터넷 연결을 확인하세요.")
        else:
            self.notifications.show_warning("번역 오류", error_msg[:100])

        self.main_window.update_status(f"번역 오류: {error_msg[:50]}")

    def _handle_exception(self, exc_type, exc_value, exc_tb) -> None:
        """전역 예외 처리"""
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(f"[CRITICAL ERROR]\n{error_msg}")

        self.notifications.show_error(
            "치명적 오류",
            f"예기치 않은 오류가 발생했습니다:\n{exc_value}",
            show_dialog=True
        )

    def start(self) -> None:
        """번역 시작"""
        # API 키 확인
        api_key = self._get_api_key()
        if not api_key:
            self.notifications.show_error(
                "API 키 필요",
                "Gemini API 키가 설정되지 않았습니다.\n설정에서 API 키를 입력하세요.",
                show_dialog=True
            )
            self._show_settings()
            return

        try:
            # 초기화
            self.screen_capture.initialize()
            self.ocr_worker.start()
            self.translation_service.start()
            self.overlay.show()

            # 오버레이 위치 설정
            self.overlay.move(
                self.config.overlay.position_x,
                self.config.overlay.position_y
            )

            self.main_window.update_status("번역 실행 중...")
            print("[Application] 번역 시작")

            # 트레이 메뉴 업데이트
            self._tray_start_action.setEnabled(False)
            self._tray_stop_action.setEnabled(True)

            # 통계 초기화
            self.ocr_worker.reset_stats()

            self.notifications.show_info("Auto-Trans", "번역이 시작되었습니다.")

        except Exception as e:
            self.notifications.show_error("시작 오류", f"번역 시작 실패: {e}", show_dialog=True)

    def stop(self) -> None:
        """번역 정지"""
        try:
            self.ocr_worker.stop()
            self.translation_service.stop()
            self.overlay.hide()
            self.screen_capture.cleanup()

            self.main_window.update_status("대기 중")
            print("[Application] 번역 정지")

            # 트레이 메뉴 업데이트
            self._tray_start_action.setEnabled(True)
            self._tray_stop_action.setEnabled(False)

            # 통계 출력
            ocr_stats = self.ocr_worker.get_stats_dict()
            trans_stats = self.translation_service.get_stats_dict()
            print(f"[통계] OCR: {ocr_stats}")
            print(f"[통계] 번역: {trans_stats}")

        except Exception as e:
            print(f"[Application] 정지 중 오류: {e}")

    def run(self) -> int:
        """애플리케이션 실행"""
        # 메인 윈도우 표시
        self.main_window.show()

        # 트레이 시작 알림
        self.notifications.show_info("Auto-Trans", "실시간 게임 화면 번역기가 시작되었습니다.")

        # 메인 윈도우 닫기 이벤트 처리
        original_close = self.main_window.closeEvent

        def close_to_tray(event):
            if self.config.minimize_to_tray:
                event.ignore()
                self.main_window.hide()
                self.notifications.show_info("Auto-Trans", "트레이로 최소화되었습니다.")
            else:
                original_close(event)
                self._quit_app()

        self.main_window.closeEvent = close_to_tray

        return self.qt_app.exec()

    def cleanup(self) -> None:
        """종료 정리"""
        try:
            self.stop()

            # 오버레이 위치 저장
            pos = self.overlay.pos()
            self.config.overlay.position_x = pos.x()
            self.config.overlay.position_y = pos.y()

            self.db.close()
            self.config.save()
        except Exception as e:
            print(f"[Application] 정리 중 오류: {e}")


def main() -> int:
    """메인 함수"""
    print("=" * 50)
    print("Auto-Trans - 실시간 게임 화면 번역기")
    print("=" * 50)

    app = Application()
    try:
        return app.run()
    finally:
        app.cleanup()


if __name__ == "__main__":
    sys.exit(main())
