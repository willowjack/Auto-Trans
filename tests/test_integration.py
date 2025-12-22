"""
통합 테스트 - 모듈별 동작 검증

사용법:
    python -m pytest tests/test_integration.py -v
    또는
    python tests/test_integration.py
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """모듈 임포트 테스트"""
    print("1. 모듈 임포트 테스트...")

    # Core 모듈
    from core.capture import ScreenCapture
    from core.ocr import RapidOCREngine
    from core.translators import GeminiTranslator
    from core import OCRWorker, TranslationService
    print("   - core 모듈 OK")

    # Data 모듈
    from data import Database, HistoryRepository, GlossaryRepository
    print("   - data 모듈 OK")

    # Utils 모듈
    from utils import Config, APIConfig, CaptureRegion, ensure_dirs
    print("   - utils 모듈 OK")

    # UI 모듈 (PyQt6 필요)
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        from ui import (
            MainWindow, OverlayWindow, HistoryEditor,
            SettingsDialog, RegionSelector
        )
        print("   - ui 모듈 OK")
    except ImportError as e:
        print(f"   - ui 모듈 SKIP (PyQt6 없음): {e}")

    print("   모든 임포트 성공!")
    return True


def test_config():
    """설정 로드/저장 테스트"""
    print("\n2. 설정 테스트...")

    from utils import Config
    from pathlib import Path
    import tempfile

    # 임시 파일로 테스트
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        test_path = Path(f.name)

    try:
        config = Config(test_path)

        # 기본값 확인
        assert config.ocr.stabilization_time == 1.5
        assert config.translation.target_language == "ko"
        print("   - 기본값 OK")

        # 값 변경 및 저장
        config.api.gemini_api_key = "test-key-12345"
        config.ocr.stabilization_time = 2.0
        config.save()
        print("   - 저장 OK")

        # 새로 로드
        config2 = Config(test_path)
        config2.load()
        assert config2.api.gemini_api_key == "test-key-12345"
        assert config2.ocr.stabilization_time == 2.0
        print("   - 로드 OK")

        print("   설정 테스트 성공!")
        return True
    finally:
        test_path.unlink(missing_ok=True)


def test_database():
    """데이터베이스 테스트"""
    print("\n3. 데이터베이스 테스트...")

    from data import Database, HistoryRepository, GlossaryRepository
    from data.models import HistoryEntry, GlossaryTerm
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_path = Path(f.name)

    try:
        db = Database(test_path)
        db.connect()
        print("   - 연결 OK")

        # 히스토리 테스트
        history_repo = HistoryRepository(db)
        entry = HistoryEntry(
            game_id=1,
            original_text="Hello World",
            translated_text="안녕하세요",
            source_language="en",
            target_language="ko"
        )
        entry = history_repo.create(entry)
        assert entry.id is not None and entry.id > 0
        entry_id = entry.id
        print(f"   - 히스토리 추가 OK (id={entry_id})")

        # 조회
        entry = history_repo.get_by_id(entry_id)
        assert entry is not None
        assert entry.original_text == "Hello World"
        print("   - 히스토리 조회 OK")

        # 수정
        success = history_repo.update_translation(entry_id, "안녕하세요 세계")
        assert success
        entry = history_repo.get_by_id(entry_id)
        assert entry.translated_text == "안녕하세요 세계"
        print("   - 히스토리 수정 OK")

        # 용어집 테스트
        glossary_repo = GlossaryRepository(db)
        term = GlossaryTerm(
            original_term="NPC",
            translated_term="비플레이어 캐릭터",
            category="게임용어"
        )
        term = glossary_repo.create(term)
        assert term.id is not None and term.id > 0
        print(f"   - 용어집 추가 OK (id={term.id})")

        db.close()
        print("   데이터베이스 테스트 성공!")
        return True
    finally:
        test_path.unlink(missing_ok=True)


def test_screen_capture():
    """화면 캡처 테스트"""
    print("\n4. 화면 캡처 테스트...")

    import os
    if not os.environ.get("DISPLAY"):
        print("   - 화면 캡처 SKIP (헤드리스 환경)")
        return True  # 헤드리스 환경에서는 스킵

    try:
        from core.capture import ScreenCapture

        capture = ScreenCapture()

        # 전체 화면 캡처
        image = capture.grab()
        assert image is not None
        assert len(image.shape) == 3  # (H, W, C)
        print(f"   - 전체 화면 캡처 OK: {image.shape}")

        # 영역 설정
        capture.set_region(0, 0, 200, 100)
        image = capture.grab()
        assert image.shape[0] == 100
        assert image.shape[1] == 200
        print(f"   - 영역 캡처 OK: {image.shape}")

        print("   화면 캡처 테스트 성공!")
        return True
    except Exception as e:
        print(f"   화면 캡처 테스트 실패: {e}")
        return False


def test_ocr():
    """OCR 테스트"""
    print("\n5. OCR 테스트...")

    try:
        from core.ocr import RapidOCREngine
        import numpy as np

        engine = RapidOCREngine(use_gpu=False)

        # 빈 이미지로 테스트
        dummy_image = np.zeros((100, 300, 3), dtype=np.uint8)
        dummy_image.fill(255)  # 흰색 배경

        result = engine.recognize(dummy_image)
        assert result is not None
        print(f"   - OCR 엔진 초기화 OK")
        print(f"   - 인식 결과: '{result.text}' (빈 이미지)")

        print("   OCR 테스트 성공!")
        return True
    except Exception as e:
        print(f"   OCR 테스트 실패: {e}")
        return False


def test_ui_components():
    """UI 컴포넌트 테스트"""
    print("\n6. UI 컴포넌트 테스트...")

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        app = QApplication.instance() or QApplication([])

        from ui import MainWindow, OverlayWindow, SettingsDialog
        from utils import Config
        import tempfile
        from pathlib import Path

        # MainWindow
        main_window = MainWindow()
        assert main_window is not None
        print("   - MainWindow OK")

        # OverlayWindow
        overlay = OverlayWindow()
        overlay.set_text("테스트 번역")
        assert overlay is not None
        print("   - OverlayWindow OK")

        # SettingsDialog
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        try:
            config = Config(config_path)
            settings = SettingsDialog(config)
            assert settings is not None
            print("   - SettingsDialog OK")
        finally:
            config_path.unlink(missing_ok=True)

        print("   UI 컴포넌트 테스트 성공!")
        return True
    except ImportError as e:
        print(f"   UI 테스트 SKIP (PyQt6 없음): {e}")
        return True
    except Exception as e:
        print(f"   UI 테스트 실패: {e}")
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 50)
    print("Auto-Trans 통합 테스트")
    print("=" * 50)

    results = []

    results.append(("임포트", test_imports()))
    results.append(("설정", test_config()))
    results.append(("데이터베이스", test_database()))
    results.append(("화면 캡처", test_screen_capture()))
    results.append(("OCR", test_ocr()))
    results.append(("UI", test_ui_components()))

    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)

    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n총 {passed}/{len(results)} 통과")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
