"""
Utils 모듈 - 유틸리티 함수 및 클래스

- platform: OS별 경로 및 기능 처리
- config: 설정 관리
"""

from utils.platform import (
    get_platform,
    get_data_dir,
    get_config_dir,
    get_cache_dir,
    get_log_dir,
    ensure_dirs,
    is_windows,
    is_macos,
    is_linux
)
from utils.config import Config, APIConfig, CaptureRegion

__all__ = [
    "get_platform", "get_data_dir", "get_config_dir", "get_cache_dir",
    "get_log_dir", "ensure_dirs",
    "is_windows", "is_macos", "is_linux",
    "Config", "APIConfig", "CaptureRegion"
]
