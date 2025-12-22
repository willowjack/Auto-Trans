#!/usr/bin/env python3
"""
Auto-Trans - 실시간 게임 화면 번역기

진입점 (Entry Point)
"""

import sys
import os
from typing import Optional

from PyQt6.QtWidgets import QApplication

# 모듈 임포트
from core import OCRWorker, TranslationService
from core.capture import ScreenCapture
from core.ocr import RapidOCREngine
from core.interfaces import TranslationResult
from core.ocr_worker import StabilizedText

from data import Database, GameRepository, HistoryRepository, GlossaryRepository

from ui import MainWindow, OverlayWindow, HistoryEditorWindow

from utils import Config, ensure_dirs


class Application:
    """
    메인 애플리케이션 클래스

    전체 번역 파이프라인을 관리합니다:
    1. 화면 캡처 (ScreenCapture)
    2. OCR 인식 (OCRWorker + RapidOCR)
    3. 텍스트 안정화 (1.5초)
    4. 문맥 인식 번역 (TranslationService + Gemini)
    5. 오버레이 표시 (OverlayWindow)
    6. 히스토리 편집 (HistoryEditorWindow)
    7. DB 저장 (History, Glossary)
    """

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
        self.translation_service = TranslationService(
            db=self.db,
            api_key=os.environ.get("GEMINI_API_KEY"),
            target_language=self.config.translation.target_language,
            source_language=self.config.translation.source_language,
            use_cache=True
        )

        # UI
        self.qt_app = QApplication(sys.argv)
        self.main_window = MainWindow()
        self.overlay = OverlayWindow()
        self.history_editor = HistoryEditorWindow()

        # 현재 게임 ID
        self._current_game_id: Optional[int] = None

        self._setup_connections()
        self._setup_ui_connections()
        self._load_games()

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
        # 메인 윈도우 → 히스토리/용어집 열기
        self.main_window.history_requested.connect(self._show_history_editor)

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

    def _show_history_editor(self) -> None:
        """히스토리 에디터 표시"""
        self.history_editor.show()
        self.history_editor.activateWindow()

    def _load_games(self) -> None:
        """게임 목록 로드"""
        games = self.game_repo.get_all(active_only=True)
        game_list = [(g.id, g.name) for g in games]
        self.main_window.set_games(game_list)

    def _on_game_changed(self, game_id: int) -> None:
        """게임 선택 변경"""
        self._current_game_id = game_id
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

    def _on_translation_start(self, text: str) -> None:
        """번역 시작"""
        # 번역 중 표시 (선택적)
        preview = text[:30] + "..." if len(text) > 30 else text
        self.main_window.update_status(f"번역 중: {preview}")

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

        # 히스토리 에디터에 추가
        self.history_editor.add_entry(result)

        self.main_window.update_status("번역 완료")

    def _on_overlay_update_from_editor(self, original: str, translated: str) -> None:
        """히스토리 에디터에서 오버레이 업데이트 요청"""
        if self.config.overlay.show_original:
            self.overlay.set_original_and_translated(original, translated)
        else:
            self.overlay.set_text(translated)

    def _on_glossary_added(self, original: str, translated: str, category: str) -> None:
        """용어집 추가"""
        self.translation_service.add_glossary_term(
            original=original,
            translation=translated,
            category=category,
            is_global=False
        )
        self.main_window.update_status(f"용어집 추가: {original} → {translated}")

    def _on_translation_edited(self, entry_id: int, original: str, new_translated: str) -> None:
        """번역 수정 → DB 업데이트"""
        try:
            self.history_repo.update_translation(entry_id, new_translated)
            print(f"[Application] 번역 수정 저장: ID={entry_id}")
        except Exception as e:
            print(f"[Application] 번역 수정 저장 실패: {e}")

    def _on_edit_requested(self, original: str, translated: str) -> None:
        """오버레이에서 편집 요청 → 히스토리 에디터 열기"""
        self.history_editor.show()
        self.history_editor.activateWindow()

    def _on_ocr_error(self, error: Exception) -> None:
        """OCR 오류"""
        print(f"[OCR 오류] {error}")
        self.main_window.update_status(f"OCR 오류: {str(error)[:50]}")

    def _on_translation_error(self, error: Exception) -> None:
        """번역 오류"""
        print(f"[번역 오류] {error}")
        self.main_window.update_status(f"번역 오류: {str(error)[:50]}")

    def start(self) -> None:
        """번역 시작"""
        # 초기화
        self.screen_capture.initialize()
        self.ocr_worker.start()
        self.translation_service.start()
        self.overlay.show()

        self.main_window.update_status("번역 실행 중...")
        print("[Application] 번역 시작")

        # 통계 초기화
        self.ocr_worker.reset_stats()

    def stop(self) -> None:
        """번역 정지"""
        self.ocr_worker.stop()
        self.translation_service.stop()
        self.overlay.hide()
        self.screen_capture.cleanup()

        self.main_window.update_status("대기 중")
        print("[Application] 번역 정지")

        # 통계 출력
        ocr_stats = self.ocr_worker.get_stats_dict()
        trans_stats = self.translation_service.get_stats_dict()
        print(f"[통계] OCR: {ocr_stats}")
        print(f"[통계] 번역: {trans_stats}")

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
    print("=" * 50)
    print("Auto-Trans - 실시간 게임 화면 번역기")
    print("=" * 50)

    # API 키 확인
    if not os.environ.get("GEMINI_API_KEY"):
        print("\n[경고] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("Gemini 번역을 사용하려면 API 키를 설정하세요:")
        print("  export GEMINI_API_KEY='your-api-key'\n")

    app = Application()
    try:
        return app.run()
    finally:
        app.cleanup()


if __name__ == "__main__":
    sys.exit(main())
