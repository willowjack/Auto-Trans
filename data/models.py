"""
데이터 모델 클래스

각 테이블에 대응하는 데이터 클래스 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Game:
    """게임 설정 모델"""
    id: Optional[int] = None
    name: str = ""
    process_name: Optional[str] = None
    source_language: str = "auto"
    target_language: str = "ko"
    capture_region_x: Optional[int] = None
    capture_region_y: Optional[int] = None
    capture_region_w: Optional[int] = None
    capture_region_h: Optional[int] = None
    ocr_interval: float = 0.5
    stabilization_time: float = 1.5
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def has_capture_region(self) -> bool:
        """캡처 영역이 설정되었는지 확인"""
        return all([
            self.capture_region_x is not None,
            self.capture_region_y is not None,
            self.capture_region_w is not None,
            self.capture_region_h is not None
        ])

    @property
    def capture_region(self) -> Optional[tuple[int, int, int, int]]:
        """캡처 영역 튜플 반환 (x, y, w, h)"""
        if self.has_capture_region:
            return (
                self.capture_region_x,
                self.capture_region_y,
                self.capture_region_w,
                self.capture_region_h
            )
        return None

    @capture_region.setter
    def capture_region(self, value: Optional[tuple[int, int, int, int]]) -> None:
        """캡처 영역 설정"""
        if value is None:
            self.capture_region_x = None
            self.capture_region_y = None
            self.capture_region_w = None
            self.capture_region_h = None
        else:
            self.capture_region_x = value[0]
            self.capture_region_y = value[1]
            self.capture_region_w = value[2]
            self.capture_region_h = value[3]


@dataclass
class HistoryEntry:
    """번역 히스토리 모델"""
    id: Optional[int] = None
    game_id: Optional[int] = None
    original_text: str = ""
    translated_text: str = ""
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None


@dataclass
class GlossaryTerm:
    """용어집 항목 모델"""
    id: Optional[int] = None
    game_id: Optional[int] = None
    original_term: str = ""
    translated_term: str = ""
    category: Optional[str] = None
    notes: Optional[str] = None
    is_global: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_game_specific(self) -> bool:
        """게임별 용어인지 확인"""
        return self.game_id is not None and not self.is_global
