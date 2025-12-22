"""
플랫폼 유틸리티 - OS별 경로 및 기능 처리

Windows와 macOS에서 적절한 경로를 반환합니다.
"""

import sys
import os
from pathlib import Path
from enum import Enum


class Platform(Enum):
    """플랫폼 열거형"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


def get_platform() -> Platform:
    """현재 플랫폼 반환"""
    if sys.platform == "win32":
        return Platform.WINDOWS
    elif sys.platform == "darwin":
        return Platform.MACOS
    elif sys.platform.startswith("linux"):
        return Platform.LINUX
    return Platform.UNKNOWN


def is_windows() -> bool:
    """Windows 여부"""
    return get_platform() == Platform.WINDOWS


def is_macos() -> bool:
    """macOS 여부"""
    return get_platform() == Platform.MACOS


def is_linux() -> bool:
    """Linux 여부"""
    return get_platform() == Platform.LINUX


def get_data_dir() -> Path:
    """
    데이터 디렉토리 경로 반환

    Windows: %LOCALAPPDATA%/AutoTrans
    macOS: ~/Library/Application Support/AutoTrans
    Linux: ~/.local/share/AutoTrans
    """
    platform = get_platform()

    if platform == Platform.WINDOWS:
        base = os.environ.get("LOCALAPPDATA", "")
        if not base:
            base = os.path.expanduser("~")
        return Path(base) / "AutoTrans"

    elif platform == Platform.MACOS:
        return Path.home() / "Library" / "Application Support" / "AutoTrans"

    else:  # Linux 및 기타
        xdg_data = os.environ.get("XDG_DATA_HOME", "")
        if xdg_data:
            return Path(xdg_data) / "AutoTrans"
        return Path.home() / ".local" / "share" / "AutoTrans"


def get_config_dir() -> Path:
    """
    설정 디렉토리 경로 반환

    Windows: %APPDATA%/AutoTrans
    macOS: ~/Library/Preferences/AutoTrans
    Linux: ~/.config/AutoTrans
    """
    platform = get_platform()

    if platform == Platform.WINDOWS:
        base = os.environ.get("APPDATA", "")
        if not base:
            base = os.path.expanduser("~")
        return Path(base) / "AutoTrans"

    elif platform == Platform.MACOS:
        return Path.home() / "Library" / "Preferences" / "AutoTrans"

    else:  # Linux 및 기타
        xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg_config:
            return Path(xdg_config) / "AutoTrans"
        return Path.home() / ".config" / "AutoTrans"


def get_cache_dir() -> Path:
    """
    캐시 디렉토리 경로 반환

    Windows: %LOCALAPPDATA%/AutoTrans/Cache
    macOS: ~/Library/Caches/AutoTrans
    Linux: ~/.cache/AutoTrans
    """
    platform = get_platform()

    if platform == Platform.WINDOWS:
        return get_data_dir() / "Cache"

    elif platform == Platform.MACOS:
        return Path.home() / "Library" / "Caches" / "AutoTrans"

    else:  # Linux 및 기타
        xdg_cache = os.environ.get("XDG_CACHE_HOME", "")
        if xdg_cache:
            return Path(xdg_cache) / "AutoTrans"
        return Path.home() / ".cache" / "AutoTrans"


def get_log_dir() -> Path:
    """
    로그 디렉토리 경로 반환

    Windows: %LOCALAPPDATA%/AutoTrans/Logs
    macOS: ~/Library/Logs/AutoTrans
    Linux: ~/.local/share/AutoTrans/logs
    """
    platform = get_platform()

    if platform == Platform.WINDOWS:
        return get_data_dir() / "Logs"

    elif platform == Platform.MACOS:
        return Path.home() / "Library" / "Logs" / "AutoTrans"

    else:
        return get_data_dir() / "logs"


def ensure_dirs() -> None:
    """필요한 디렉토리들을 생성"""
    dirs = [
        get_data_dir(),
        get_config_dir(),
        get_cache_dir(),
        get_log_dir()
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
