"""
설정 관리 - JSON 기반 설정 파일 관리
"""

import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from utils.platform import get_config_dir


@dataclass
class OCRConfig:
    """OCR 설정"""
    engine: str = "rapidocr"
    interval: float = 0.5
    stabilization_time: float = 1.5


@dataclass
class TranslationConfig:
    """번역 설정"""
    engine: str = "google"
    source_language: str = "auto"
    target_language: str = "ko"
    cache_size: int = 1000
    use_glossary: bool = True


@dataclass
class OverlayConfig:
    """오버레이 설정"""
    font_size: int = 14
    opacity: float = 0.8
    show_original: bool = True
    position_x: int = 100
    position_y: int = 100


@dataclass
class AppConfig:
    """전체 앱 설정"""
    ocr: OCRConfig = field(default_factory=OCRConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    minimize_to_tray: bool = False
    auto_start: bool = False
    current_game_id: Optional[int] = None


class Config:
    """설정 관리 클래스"""

    DEFAULT_FILENAME = "config.json"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: 설정 파일 경로 (None이면 기본 경로)
        """
        if config_path is None:
            config_path = get_config_dir() / self.DEFAULT_FILENAME
        self._path = config_path
        self._config = AppConfig()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def ocr(self) -> OCRConfig:
        return self._config.ocr

    @property
    def translation(self) -> TranslationConfig:
        return self._config.translation

    @property
    def overlay(self) -> OverlayConfig:
        return self._config.overlay

    @property
    def app(self) -> AppConfig:
        return self._config

    def load(self) -> None:
        """설정 파일 로드"""
        if not self._path.exists():
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._apply_dict(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"설정 로드 실패: {e}")

    def save(self) -> None:
        """설정 파일 저장"""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        data = self._to_dict()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _to_dict(self) -> dict:
        """설정을 딕셔너리로 변환"""
        return {
            "ocr": asdict(self._config.ocr),
            "translation": asdict(self._config.translation),
            "overlay": asdict(self._config.overlay),
            "minimize_to_tray": self._config.minimize_to_tray,
            "auto_start": self._config.auto_start,
            "current_game_id": self._config.current_game_id
        }

    def _apply_dict(self, data: dict) -> None:
        """딕셔너리에서 설정 적용"""
        if "ocr" in data:
            for k, v in data["ocr"].items():
                if hasattr(self._config.ocr, k):
                    setattr(self._config.ocr, k, v)

        if "translation" in data:
            for k, v in data["translation"].items():
                if hasattr(self._config.translation, k):
                    setattr(self._config.translation, k, v)

        if "overlay" in data:
            for k, v in data["overlay"].items():
                if hasattr(self._config.overlay, k):
                    setattr(self._config.overlay, k, v)

        if "minimize_to_tray" in data:
            self._config.minimize_to_tray = data["minimize_to_tray"]

        if "auto_start" in data:
            self._config.auto_start = data["auto_start"]

        if "current_game_id" in data:
            self._config.current_game_id = data["current_game_id"]

    def get(self, key: str, default: Any = None) -> Any:
        """점 표기법으로 설정값 조회 (예: 'ocr.interval')"""
        parts = key.split(".")
        obj: Any = self._config

        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return default
        return obj

    def set(self, key: str, value: Any) -> None:
        """점 표기법으로 설정값 변경"""
        parts = key.split(".")
        obj: Any = self._config

        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return

        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
