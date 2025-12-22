#!/usr/bin/env python3
"""
Auto-Trans - 실시간 게임 화면 번역기

진입점 (Entry Point)
"""

import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal

# 모듈 임포트
from core import OCRWorker, TranslationManager
from core.ocr import RapidOCREngine
from core.translators import GoogleTranslator
from core.interfaces import TranslationResult
from core.ocr_worker import StabilizedText

from data import Database, GameRepository, HistoryRepository, GlossaryRepository
from data.models import HistoryEntry

from ui import MainWindow, OverlayWindow

from utils import Config, ensure_dirs, is_windows, is_macos

import numpy as np


class ScreenCapture:
    """화면 캡처 유틸리티"""

    def __init__(self):
        self._mss = None
        self._region: Optional[tuple[int, int, int, int]] = None

    def initialize(self) -> None:
        """캡처 초기화"""
        import mss
        self._mss = mss.mss()

    def set_region(self, x: int, y: int, w: int, h: int) -> None:
        """캡처 영역 설정"""
        self._region = (x, y, w, h)

    def capture(self) -> Optional[np.ndarray]:
        """화면 캡처"""
        if self._mss is None:
            self.initialize()

        try:
            if self._region:
                monitor = {
                    "left": self._region[0],
                    "top": self._region[1],
                    "width": self._region[2],
                    "height": self._region[3]
                }
            else:
                # 전체 화면 (기본 모니터)
                monitor = self._mss.monitors[1]

            screenshot = self._mss.grab(monitor)
            return np.array(screenshot)

        except Exception as e:
            print(f"캡처 오류: {e}")
            return None

    def cleanup(self) -> None:
        """리소스 정리"""
        if self._mss:
            self._mss.close()
            self._mss = None


class Application:
    """메인 애플리케이션 클래스"""

    def __init__(self):
        # 디렉토리 초기화
        ensure_dirs()

        # 설정 로드
        self.config = Config()
        self.config.load()

        # 데이터베이스
        self.db = Database()
        self.db.connect()

        # Repositories
        self.game_repo = GameRepository(self.db)
        self.history_repo = HistoryRepository(self.db)
        self.glossary_repo = GlossaryRepository(self.db)

        # Core 컴포넌트
        self.ocr_engine = RapidOCREngine()
        self.translator = GoogleTranslator()
        self.screen_capture = ScreenCapture()

        # 워커
        self.ocr_worker = OCRWorker(
            ocr_engine=self.ocr_engine,
            capture_callback=self.screen_capture.capture,
            interval=self.config.ocr.interval,
            stabilization_time=self.config.ocr.stabilization_time
        )

        self.translation_manager = TranslationManager(
            translator=self.translator,
            target_language=self.config.translation.target_language,
            source_language=self.config.translation.source_language
        )

        # UI
        self.qt_app = QApplication(sys.argv)
        self.main_window = MainWindow()
        self.overlay = OverlayWindow()

        # 현재 게임 ID
        self._current_game_id: Optional[int] = None

        self._setup_connections()
        self._load_games()
        self._load_glossary()

    def _setup_connections(self) -> None:
        """시그널 연결"""
        # 메인 윈도우 시그널
        self.main_window.start_requested.connect(self.start)
        self.main_window.stop_requested.connect(self.stop)
        self.main_window.game_changed.connect(self._on_game_changed)

        # OCR 워커 콜백
        self.ocr_worker.on_text_stabilized = self._on_text_stabilized
        self.ocr_worker.on_error = self._on_ocr_error

        # 번역 매니저 콜백
        self.translation_manager.on_translation_complete = self._on_translation_complete
        self.translation_manager.on_error = self._on_translation_error

    def _load_games(self) -> None:
        """게임 목록 로드"""
        games = self.game_repo.get_all(active_only=True)
        game_list = [(g.id, g.name) for g in games]
        self.main_window.set_games(game_list)

    def _load_glossary(self) -> None:
        """용어집 로드"""
        glossary = self.glossary_repo.get_as_dict(self._current_game_id)
        self.translation_manager.set_glossary(glossary)

    def _on_game_changed(self, game_id: int) -> None:
        """게임 선택 변경"""
        self._current_game_id = game_id
        game = self.game_repo.get_by_id(game_id)

        if game:
            # 캡처 영역 설정
            if game.has_capture_region:
                region = game.capture_region
                self.screen_capture.set_region(*region)

            # 언어 설정
            self.translation_manager.source_language = game.source_language
            self.translation_manager.target_language = game.target_language

            # 용어집 리로드
            self._load_glossary()

            self.main_window.update_status(f"게임 선택: {game.name}")

    def _on_text_stabilized(self, stabilized: StabilizedText) -> None:
        """텍스트 안정화 완료"""
        if stabilized.text:
            self.translation_manager.translate(stabilized.text)

    def _on_translation_complete(self, result: TranslationResult) -> None:
        """번역 완료"""
        # 오버레이 업데이트
        if self.config.overlay.show_original:
            self.overlay.set_original_and_translated(
                result.original_text,
                result.translated_text
            )
        else:
            self.overlay.set_text(result.translated_text)

        # 히스토리 저장
        entry = HistoryEntry(
            game_id=self._current_game_id,
            original_text=result.original_text,
            translated_text=result.translated_text,
            source_language=result.source_language,
            target_language=result.target_language,
            confidence=result.confidence
        )
        self.history_repo.create(entry)

    def _on_ocr_error(self, error: Exception) -> None:
        """OCR 오류"""
        print(f"OCR 오류: {error}")
        self.main_window.update_status(f"OCR 오류: {error}")

    def _on_translation_error(self, error: Exception) -> None:
        """번역 오류"""
        print(f"번역 오류: {error}")
        self.main_window.update_status(f"번역 오류: {error}")

    def start(self) -> None:
        """번역 시작"""
        self.screen_capture.initialize()
        self.ocr_worker.start()
        self.translation_manager.start()
        self.overlay.show()
        self.main_window.update_status("번역 실행 중...")

    def stop(self) -> None:
        """번역 정지"""
        self.ocr_worker.stop()
        self.translation_manager.stop()
        self.overlay.hide()
        self.screen_capture.cleanup()
        self.main_window.update_status("대기 중")

    def run(self) -> int:
        """애플리케이션 실행"""
        self.main_window.show()
        return self.qt_app.exec()

    def cleanup(self) -> None:
        """종료 정리"""
        self.stop()
        self.db.close()
        self.config.save()


def main() -> int:
    """메인 함수"""
    app = Application()
    try:
        return app.run()
    finally:
        app.cleanup()


if __name__ == "__main__":
    sys.exit(main())
