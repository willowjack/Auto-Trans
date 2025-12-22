"""
설정 다이얼로그 - 애플리케이션 설정 관리
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QLabel, QGroupBox
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    """설정 다이얼로그"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 구성"""
        self.setWindowTitle("설정")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        # 탭 위젯
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "일반")
        tabs.addTab(self._create_ocr_tab(), "OCR")
        tabs.addTab(self._create_translation_tab(), "번역")
        tabs.addTab(self._create_overlay_tab(), "오버레이")
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

    def _create_general_tab(self) -> QWidget:
        """일반 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 언어 설정
        lang_group = QGroupBox("언어 설정")
        lang_layout = QFormLayout()

        self._source_lang = QComboBox()
        self._source_lang.addItems(["자동 감지", "영어", "일본어", "중국어"])
        lang_layout.addRow("원본 언어:", self._source_lang)

        self._target_lang = QComboBox()
        self._target_lang.addItems(["한국어", "영어", "일본어"])
        lang_layout.addRow("번역 언어:", self._target_lang)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # 시작 설정
        startup_group = QGroupBox("시작 설정")
        startup_layout = QVBoxLayout()

        self._minimize_to_tray = QCheckBox("시작 시 트레이로 최소화")
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
        self._ocr_engine.addItems(["RapidOCR (기본)", "Tesseract", "EasyOCR"])
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
        timing_layout.addRow("OCR 간격:", self._ocr_interval)

        self._stabilization_time = QDoubleSpinBox()
        self._stabilization_time.setRange(0.5, 5.0)
        self._stabilization_time.setSingleStep(0.1)
        self._stabilization_time.setValue(1.5)
        self._stabilization_time.setSuffix(" 초")
        timing_layout.addRow("텍스트 안정화 시간:", self._stabilization_time)

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
        self._trans_engine.addItems(["Google 번역 (무료)", "DeepL", "Papago"])
        engine_layout.addRow("엔진:", self._trans_engine)

        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)

        # 캐시 설정
        cache_group = QGroupBox("캐시")
        cache_layout = QFormLayout()

        self._cache_size = QSpinBox()
        self._cache_size.setRange(100, 10000)
        self._cache_size.setValue(1000)
        cache_layout.addRow("캐시 크기:", self._cache_size)

        self._use_glossary = QCheckBox("용어집 우선 적용")
        self._use_glossary.setChecked(True)
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
        appearance_layout.addRow("투명도:", self._opacity)

        self._show_original = QCheckBox("원문도 함께 표시")
        self._show_original.setChecked(True)
        appearance_layout.addRow("", self._show_original)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        layout.addStretch()
        return widget

    def _save_settings(self) -> None:
        """설정 저장"""
        # TODO: 설정값을 저장
        self.accept()

    def load_settings(self, settings: dict) -> None:
        """설정 불러오기"""
        # TODO: 설정값을 UI에 반영
        pass

    def get_settings(self) -> dict:
        """현재 설정값 반환"""
        return {
            "source_language": self._source_lang.currentText(),
            "target_language": self._target_lang.currentText(),
            "ocr_interval": self._ocr_interval.value(),
            "stabilization_time": self._stabilization_time.value(),
            "font_size": self._font_size.value(),
            "opacity": self._opacity.value() / 100.0,
            "show_original": self._show_original.isChecked(),
            "use_glossary": self._use_glossary.isChecked(),
        }
