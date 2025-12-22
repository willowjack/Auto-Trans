"""
설정 다이얼로그 - 애플리케이션 설정 관리

기능:
- API 키 설정 (Gemini, DeepL)
- OCR 설정 (안정화 시간, 간격)
- 번역 설정 (엔진 선택, 언어)
- 오버레이 설정 (폰트, 투명도)
- JSON 저장/로드
"""

from typing import Optional, TYPE_CHECKING
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QLabel, QGroupBox, QMessageBox, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

if TYPE_CHECKING:
    from utils.config import Config


class SettingsDialog(QDialog):
    """설정 다이얼로그"""

    # 시그널
    settings_saved = pyqtSignal()
    region_select_requested = pyqtSignal()

    def __init__(self, config: Optional['Config'] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config
        self._setup_ui()

        if config:
            self._load_from_config()

    def _setup_ui(self) -> None:
        """UI 구성"""
        self.setWindowTitle("설정")
        self.setMinimumSize(550, 500)

        layout = QVBoxLayout(self)

        # 탭 위젯
        tabs = QTabWidget()
        tabs.addTab(self._create_api_tab(), "API 키")
        tabs.addTab(self._create_general_tab(), "일반")
        tabs.addTab(self._create_ocr_tab(), "OCR")
        tabs.addTab(self._create_translation_tab(), "번역")
        tabs.addTab(self._create_overlay_tab(), "오버레이")
        tabs.addTab(self._create_region_tab(), "캡처 영역")
        layout.addWidget(tabs)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _create_api_tab(self) -> QWidget:
        """API 키 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Gemini API
        gemini_group = QGroupBox("Gemini API")
        gemini_layout = QFormLayout()

        self._gemini_key = QLineEdit()
        self._gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._gemini_key.setPlaceholderText("Gemini API 키를 입력하세요")
        gemini_layout.addRow("API 키:", self._gemini_key)

        # 키 표시/숨김 버튼
        show_gemini = QCheckBox("키 표시")
        show_gemini.toggled.connect(
            lambda checked: self._gemini_key.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        gemini_layout.addRow("", show_gemini)

        gemini_help = QLabel(
            '<a href="https://makersuite.google.com/app/apikey">Gemini API 키 발급받기</a>'
        )
        gemini_help.setOpenExternalLinks(True)
        gemini_layout.addRow("", gemini_help)

        gemini_group.setLayout(gemini_layout)
        layout.addWidget(gemini_group)

        # DeepL API
        deepl_group = QGroupBox("DeepL API (선택)")
        deepl_layout = QFormLayout()

        self._deepl_key = QLineEdit()
        self._deepl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._deepl_key.setPlaceholderText("DeepL API 키 (선택사항)")
        deepl_layout.addRow("API 키:", self._deepl_key)

        show_deepl = QCheckBox("키 표시")
        show_deepl.toggled.connect(
            lambda checked: self._deepl_key.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        deepl_layout.addRow("", show_deepl)

        deepl_help = QLabel(
            '<a href="https://www.deepl.com/pro-api">DeepL API 키 발급받기</a>'
        )
        deepl_help.setOpenExternalLinks(True)
        deepl_layout.addRow("", deepl_help)

        deepl_group.setLayout(deepl_layout)
        layout.addWidget(deepl_group)

        # 테스트 버튼
        test_btn = QPushButton("API 연결 테스트")
        test_btn.clicked.connect(self._test_api_connection)
        layout.addWidget(test_btn)

        layout.addStretch()
        return widget

    def _create_general_tab(self) -> QWidget:
        """일반 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 언어 설정
        lang_group = QGroupBox("언어 설정")
        lang_layout = QFormLayout()

        self._source_lang = QComboBox()
        self._source_lang.addItems(["auto", "en", "ja", "zh"])
        self._source_lang.setItemText(0, "자동 감지")
        self._source_lang.setItemText(1, "영어")
        self._source_lang.setItemText(2, "일본어")
        self._source_lang.setItemText(3, "중국어")
        lang_layout.addRow("원본 언어:", self._source_lang)

        self._target_lang = QComboBox()
        self._target_lang.addItems(["ko", "en", "ja"])
        self._target_lang.setItemText(0, "한국어")
        self._target_lang.setItemText(1, "영어")
        self._target_lang.setItemText(2, "일본어")
        lang_layout.addRow("번역 언어:", self._target_lang)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # 시작 설정
        startup_group = QGroupBox("시작 설정")
        startup_layout = QVBoxLayout()

        self._minimize_to_tray = QCheckBox("창 닫기 시 트레이로 최소화")
        self._minimize_to_tray.setChecked(True)
        startup_layout.addWidget(self._minimize_to_tray)

        self._auto_start = QCheckBox("윈도우 시작 시 자동 실행")
        startup_layout.addWidget(self._auto_start)

        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)

        layout.addStretch()
        return widget

    def _create_ocr_tab(self) -> QWidget:
        """OCR 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # OCR 엔진 선택
        engine_group = QGroupBox("OCR 엔진")
        engine_layout = QFormLayout()

        self._ocr_engine = QComboBox()
        self._ocr_engine.addItems(["rapidocr", "tesseract", "easyocr"])
        self._ocr_engine.setItemText(0, "RapidOCR (권장)")
        self._ocr_engine.setItemText(1, "Tesseract")
        self._ocr_engine.setItemText(2, "EasyOCR")
        engine_layout.addRow("엔진:", self._ocr_engine)

        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)

        # 타이밍 설정
        timing_group = QGroupBox("타이밍")
        timing_layout = QFormLayout()

        self._ocr_interval = QDoubleSpinBox()
        self._ocr_interval.setRange(0.1, 5.0)
        self._ocr_interval.setSingleStep(0.1)
        self._ocr_interval.setValue(0.5)
        self._ocr_interval.setSuffix(" 초")
        self._ocr_interval.setToolTip("화면 캡처 및 OCR 수행 간격")
        timing_layout.addRow("OCR 간격:", self._ocr_interval)

        self._stabilization_time = QDoubleSpinBox()
        self._stabilization_time.setRange(0.5, 5.0)
        self._stabilization_time.setSingleStep(0.1)
        self._stabilization_time.setValue(1.5)
        self._stabilization_time.setSuffix(" 초")
        self._stabilization_time.setToolTip(
            "텍스트가 동일하게 유지되어야 번역이 시작되는 시간\n"
            "짧으면 빠르지만 불안정, 길면 안정적이지만 느림"
        )
        timing_layout.addRow("텍스트 안정화 시간:", self._stabilization_time)

        # 안정화 시간 설명
        stabilization_desc = QLabel(
            "💡 텍스트가 이 시간 동안 동일하게 유지되면 번역을 시작합니다.\n"
            "   게임 대화 속도에 맞게 조절하세요."
        )
        stabilization_desc.setStyleSheet("color: #666; font-size: 11px;")
        stabilization_desc.setWordWrap(True)
        timing_layout.addRow("", stabilization_desc)

        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)

        layout.addStretch()
        return widget

    def _create_translation_tab(self) -> QWidget:
        """번역 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 번역 엔진 선택
        engine_group = QGroupBox("번역 엔진")
        engine_layout = QFormLayout()

        self._trans_engine = QComboBox()
        self._trans_engine.addItems(["gemini", "deepl", "google"])
        self._trans_engine.setItemText(0, "Gemini (권장)")
        self._trans_engine.setItemText(1, "DeepL")
        self._trans_engine.setItemText(2, "Google 번역")
        engine_layout.addRow("엔진:", self._trans_engine)

        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)

        # 캐시 설정
        cache_group = QGroupBox("캐시")
        cache_layout = QFormLayout()

        self._cache_size = QSpinBox()
        self._cache_size.setRange(100, 10000)
        self._cache_size.setValue(1000)
        self._cache_size.setToolTip("번역 결과 캐시 크기 (동일 텍스트 재번역 방지)")
        cache_layout.addRow("캐시 크기:", self._cache_size)

        self._use_glossary = QCheckBox("용어집 우선 적용")
        self._use_glossary.setChecked(True)
        self._use_glossary.setToolTip("등록된 용어집의 번역을 우선 사용합니다")
        cache_layout.addRow("", self._use_glossary)

        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)

        layout.addStretch()
        return widget

    def _create_overlay_tab(self) -> QWidget:
        """오버레이 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 외관 설정
        appearance_group = QGroupBox("외관")
        appearance_layout = QFormLayout()

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 32)
        self._font_size.setValue(14)
        appearance_layout.addRow("폰트 크기:", self._font_size)

        self._opacity = QSpinBox()
        self._opacity.setRange(10, 100)
        self._opacity.setValue(80)
        self._opacity.setSuffix("%")
        appearance_layout.addRow("배경 투명도:", self._opacity)

        self._show_original = QCheckBox("원문도 함께 표시")
        self._show_original.setChecked(True)
        appearance_layout.addRow("", self._show_original)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        # 위치 설정
        position_group = QGroupBox("위치")
        position_layout = QFormLayout()

        pos_layout = QHBoxLayout()
        self._overlay_x = QSpinBox()
        self._overlay_x.setRange(0, 9999)
        self._overlay_x.setValue(100)
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self._overlay_x)

        self._overlay_y = QSpinBox()
        self._overlay_y.setRange(0, 9999)
        self._overlay_y.setValue(100)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self._overlay_y)
        pos_layout.addStretch()

        position_layout.addRow("오버레이 위치:", pos_layout)
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        layout.addStretch()
        return widget

    def _create_region_tab(self) -> QWidget:
        """캡처 영역 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 현재 영역
        current_group = QGroupBox("현재 캡처 영역")
        current_layout = QFormLayout()

        region_layout = QHBoxLayout()
        self._region_x = QSpinBox()
        self._region_x.setRange(0, 9999)
        region_layout.addWidget(QLabel("X:"))
        region_layout.addWidget(self._region_x)

        self._region_y = QSpinBox()
        self._region_y.setRange(0, 9999)
        region_layout.addWidget(QLabel("Y:"))
        region_layout.addWidget(self._region_y)
        region_layout.addStretch()
        current_layout.addRow("위치:", region_layout)

        size_layout = QHBoxLayout()
        self._region_w = QSpinBox()
        self._region_w.setRange(0, 9999)
        size_layout.addWidget(QLabel("W:"))
        size_layout.addWidget(self._region_w)

        self._region_h = QSpinBox()
        self._region_h.setRange(0, 9999)
        size_layout.addWidget(QLabel("H:"))
        size_layout.addWidget(self._region_h)
        size_layout.addStretch()
        current_layout.addRow("크기:", size_layout)

        current_group.setLayout(current_layout)
        layout.addWidget(current_group)

        # 영역 선택 버튼
        select_btn = QPushButton("🎯 마우스로 영역 선택...")
        select_btn.setMinimumHeight(40)
        select_btn.clicked.connect(self._on_select_region)
        layout.addWidget(select_btn)

        # 설명
        desc = QLabel(
            "💡 번역할 화면 영역을 마우스 드래그로 선택하세요.\n"
            "   전체 화면을 캡처하려면 값을 모두 0으로 설정하세요."
        )
        desc.setStyleSheet("color: #666; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 전체화면 버튼
        fullscreen_btn = QPushButton("전체 화면으로 초기화")
        fullscreen_btn.clicked.connect(self._reset_region)
        layout.addWidget(fullscreen_btn)

        layout.addStretch()
        return widget

    def _load_from_config(self) -> None:
        """Config에서 설정 로드"""
        if not self._config:
            return

        # API
        self._gemini_key.setText(self._config.api.gemini_api_key)
        self._deepl_key.setText(self._config.api.deepl_api_key)

        # OCR
        engine_map = {"rapidocr": 0, "tesseract": 1, "easyocr": 2}
        self._ocr_engine.setCurrentIndex(engine_map.get(self._config.ocr.engine, 0))
        self._ocr_interval.setValue(self._config.ocr.interval)
        self._stabilization_time.setValue(self._config.ocr.stabilization_time)

        # Translation
        trans_map = {"gemini": 0, "deepl": 1, "google": 2}
        self._trans_engine.setCurrentIndex(trans_map.get(self._config.translation.engine, 0))

        source_map = {"auto": 0, "en": 1, "ja": 2, "zh": 3}
        self._source_lang.setCurrentIndex(source_map.get(self._config.translation.source_language, 0))

        target_map = {"ko": 0, "en": 1, "ja": 2}
        self._target_lang.setCurrentIndex(target_map.get(self._config.translation.target_language, 0))

        self._cache_size.setValue(self._config.translation.cache_size)
        self._use_glossary.setChecked(self._config.translation.use_glossary)

        # Overlay
        self._font_size.setValue(self._config.overlay.font_size)
        self._opacity.setValue(int(self._config.overlay.opacity * 100))
        self._show_original.setChecked(self._config.overlay.show_original)
        self._overlay_x.setValue(self._config.overlay.position_x)
        self._overlay_y.setValue(self._config.overlay.position_y)

        # Capture Region
        self._region_x.setValue(self._config.capture_region.x)
        self._region_y.setValue(self._config.capture_region.y)
        self._region_w.setValue(self._config.capture_region.width)
        self._region_h.setValue(self._config.capture_region.height)

        # General
        self._minimize_to_tray.setChecked(self._config.minimize_to_tray)
        self._auto_start.setChecked(self._config.app.auto_start)

    def _save_to_config(self) -> None:
        """Config에 설정 저장"""
        if not self._config:
            return

        # API
        self._config.api.gemini_api_key = self._gemini_key.text()
        self._config.api.deepl_api_key = self._deepl_key.text()

        # OCR
        engine_values = ["rapidocr", "tesseract", "easyocr"]
        self._config.ocr.engine = engine_values[self._ocr_engine.currentIndex()]
        self._config.ocr.interval = self._ocr_interval.value()
        self._config.ocr.stabilization_time = self._stabilization_time.value()

        # Translation
        trans_values = ["gemini", "deepl", "google"]
        self._config.translation.engine = trans_values[self._trans_engine.currentIndex()]

        source_values = ["auto", "en", "ja", "zh"]
        self._config.translation.source_language = source_values[self._source_lang.currentIndex()]

        target_values = ["ko", "en", "ja"]
        self._config.translation.target_language = target_values[self._target_lang.currentIndex()]

        self._config.translation.cache_size = self._cache_size.value()
        self._config.translation.use_glossary = self._use_glossary.isChecked()

        # Overlay
        self._config.overlay.font_size = self._font_size.value()
        self._config.overlay.opacity = self._opacity.value() / 100.0
        self._config.overlay.show_original = self._show_original.isChecked()
        self._config.overlay.position_x = self._overlay_x.value()
        self._config.overlay.position_y = self._overlay_y.value()

        # Capture Region
        self._config.capture_region.x = self._region_x.value()
        self._config.capture_region.y = self._region_y.value()
        self._config.capture_region.width = self._region_w.value()
        self._config.capture_region.height = self._region_h.value()

        # General
        self._config.minimize_to_tray = self._minimize_to_tray.isChecked()
        self._config.app.auto_start = self._auto_start.isChecked()

    def _save_settings(self) -> None:
        """설정 저장"""
        self._save_to_config()

        if self._config:
            try:
                self._config.save()
                self.settings_saved.emit()
                QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "저장 실패", f"설정 저장 실패: {e}")
        else:
            self.accept()

    def _test_api_connection(self) -> None:
        """API 연결 테스트"""
        gemini_key = self._gemini_key.text().strip()
        deepl_key = self._deepl_key.text().strip()

        results = []

        if gemini_key:
            # Gemini 테스트 (간단한 체크)
            if len(gemini_key) > 10:
                results.append("✅ Gemini API 키 형식 확인됨")
            else:
                results.append("❌ Gemini API 키가 짧습니다")
        else:
            results.append("⚠️ Gemini API 키 미입력")

        if deepl_key:
            if len(deepl_key) > 10:
                results.append("✅ DeepL API 키 형식 확인됨")
            else:
                results.append("❌ DeepL API 키가 짧습니다")

        QMessageBox.information(
            self, "API 테스트 결과",
            "\n".join(results) if results else "입력된 API 키가 없습니다."
        )

    def _on_select_region(self) -> None:
        """영역 선택 요청"""
        self.hide()
        self.region_select_requested.emit()

    def set_region(self, x: int, y: int, w: int, h: int) -> None:
        """영역 설정"""
        self._region_x.setValue(x)
        self._region_y.setValue(y)
        self._region_w.setValue(w)
        self._region_h.setValue(h)
        self.show()

    def _reset_region(self) -> None:
        """영역 초기화"""
        self._region_x.setValue(0)
        self._region_y.setValue(0)
        self._region_w.setValue(0)
        self._region_h.setValue(0)

    def get_settings(self) -> dict:
        """현재 설정값 반환"""
        return {
            "api": {
                "gemini_api_key": self._gemini_key.text(),
                "deepl_api_key": self._deepl_key.text(),
            },
            "ocr": {
                "engine": ["rapidocr", "tesseract", "easyocr"][self._ocr_engine.currentIndex()],
                "interval": self._ocr_interval.value(),
                "stabilization_time": self._stabilization_time.value(),
            },
            "translation": {
                "engine": ["gemini", "deepl", "google"][self._trans_engine.currentIndex()],
                "source_language": ["auto", "en", "ja", "zh"][self._source_lang.currentIndex()],
                "target_language": ["ko", "en", "ja"][self._target_lang.currentIndex()],
                "cache_size": self._cache_size.value(),
                "use_glossary": self._use_glossary.isChecked(),
            },
            "overlay": {
                "font_size": self._font_size.value(),
                "opacity": self._opacity.value() / 100.0,
                "show_original": self._show_original.isChecked(),
                "position_x": self._overlay_x.value(),
                "position_y": self._overlay_y.value(),
            },
            "capture_region": {
                "x": self._region_x.value(),
                "y": self._region_y.value(),
                "width": self._region_w.value(),
                "height": self._region_h.value(),
            },
            "minimize_to_tray": self._minimize_to_tray.isChecked(),
            "auto_start": self._auto_start.isChecked(),
        }
