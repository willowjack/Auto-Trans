"""
OCR 엔진 인터페이스 (전략 패턴)

새로운 OCR 엔진을 추가하려면 OCREngine 클래스를 상속받아 구현하세요.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import numpy as np


class Language(Enum):
    """지원 언어"""
    KOREAN = "ko"
    ENGLISH = "en"
    JAPANESE = "ja"
    CHINESE_SIMPLIFIED = "zh-cn"
    CHINESE_TRADITIONAL = "zh-tw"
    AUTO = "auto"

    @classmethod
    def from_string(cls, s: str) -> "Language":
        """문자열에서 Language 생성"""
        mapping = {
            "ko": cls.KOREAN, "korean": cls.KOREAN, "한국어": cls.KOREAN,
            "en": cls.ENGLISH, "english": cls.ENGLISH, "영어": cls.ENGLISH,
            "ja": cls.JAPANESE, "japanese": cls.JAPANESE, "일본어": cls.JAPANESE,
            "zh-cn": cls.CHINESE_SIMPLIFIED, "chinese": cls.CHINESE_SIMPLIFIED,
            "zh-tw": cls.CHINESE_TRADITIONAL,
            "auto": cls.AUTO, "자동": cls.AUTO
        }
        return mapping.get(s.lower(), cls.AUTO)


@dataclass
class TextBox:
    """
    인식된 텍스트 박스

    OCR로 인식된 개별 텍스트 영역의 정보를 담습니다.
    """
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float

    # 원본 4점 좌표 (폴리곤) - 회전된 텍스트용
    polygon: Optional[List[tuple[int, int]]] = None

    @property
    def center(self) -> tuple[int, int]:
        """박스 중심점"""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        """박스 면적"""
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        """가로세로 비율"""
        return self.width / max(self.height, 1)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "w": self.width,
            "h": self.height,
            "confidence": self.confidence,
            "polygon": self.polygon
        }

    def contains_point(self, px: int, py: int) -> bool:
        """점이 박스 내부에 있는지 확인"""
        return (self.x <= px < self.x + self.width and
                self.y <= py < self.y + self.height)

    def __str__(self) -> str:
        return f"TextBox('{self.text[:20]}...' @ ({self.x},{self.y}) {self.width}x{self.height})"


@dataclass
class OCRResult:
    """
    OCR 결과 데이터 클래스

    전체 인식 결과와 개별 텍스트 박스 정보를 포함합니다.
    """
    text: str                          # 전체 텍스트 (줄바꿈으로 연결)
    boxes: List[TextBox] = field(default_factory=list)  # 개별 텍스트 박스들
    confidence: float = 0.0            # 평균 신뢰도
    language: Optional[str] = None     # 감지된 언어
    processing_time_ms: float = 0.0    # 처리 시간 (밀리초)

    @property
    def is_empty(self) -> bool:
        """결과가 비어있는지 확인"""
        return not self.text.strip()

    @property
    def line_count(self) -> int:
        """인식된 라인 수"""
        return len(self.boxes)

    @property
    def char_count(self) -> int:
        """총 문자 수"""
        return len(self.text.replace("\n", "").replace(" ", ""))

    @property
    def word_count(self) -> int:
        """총 단어 수 (공백 기준)"""
        return len(self.text.split())

    @property
    def bounding_boxes(self) -> list[dict]:
        """하위 호환성을 위한 딕셔너리 리스트"""
        return [box.to_dict() for box in self.boxes]

    def get_text_at(self, x: int, y: int) -> Optional[TextBox]:
        """특정 좌표의 텍스트 박스 반환"""
        for box in self.boxes:
            if box.contains_point(x, y):
                return box
        return None

    def filter_by_confidence(self, min_confidence: float) -> "OCRResult":
        """최소 신뢰도 이상의 박스만 필터링"""
        filtered_boxes = [b for b in self.boxes if b.confidence >= min_confidence]
        filtered_text = "\n".join(b.text for b in filtered_boxes)

        avg_conf = 0.0
        if filtered_boxes:
            avg_conf = sum(b.confidence for b in filtered_boxes) / len(filtered_boxes)

        return OCRResult(
            text=filtered_text,
            boxes=filtered_boxes,
            confidence=avg_conf,
            language=self.language,
            processing_time_ms=self.processing_time_ms
        )

    def merge_nearby_boxes(self, max_gap: int = 10) -> "OCRResult":
        """
        가까운 박스들을 병합 (같은 줄로 추정되는 텍스트)

        Args:
            max_gap: 병합할 최대 간격 (픽셀)
        """
        if not self.boxes:
            return self

        # Y좌표로 정렬
        sorted_boxes = sorted(self.boxes, key=lambda b: (b.y, b.x))
        merged: List[TextBox] = []
        current_line: List[TextBox] = [sorted_boxes[0]]

        for box in sorted_boxes[1:]:
            last_box = current_line[-1]

            # 같은 줄인지 확인 (Y좌표 차이가 높이의 절반 이내)
            y_diff = abs(box.y - last_box.y)
            if y_diff < last_box.height * 0.5:
                current_line.append(box)
            else:
                # 현재 줄 병합
                merged.append(self._merge_line(current_line))
                current_line = [box]

        # 마지막 줄 병합
        if current_line:
            merged.append(self._merge_line(current_line))

        merged_text = "\n".join(b.text for b in merged)
        avg_conf = sum(b.confidence for b in merged) / len(merged) if merged else 0.0

        return OCRResult(
            text=merged_text,
            boxes=merged,
            confidence=avg_conf,
            language=self.language,
            processing_time_ms=self.processing_time_ms
        )

    def _merge_line(self, boxes: List[TextBox]) -> TextBox:
        """한 줄의 박스들을 병합"""
        if len(boxes) == 1:
            return boxes[0]

        # X좌표로 정렬
        sorted_boxes = sorted(boxes, key=lambda b: b.x)

        merged_text = " ".join(b.text for b in sorted_boxes)
        min_x = min(b.x for b in sorted_boxes)
        min_y = min(b.y for b in sorted_boxes)
        max_x = max(b.x + b.width for b in sorted_boxes)
        max_y = max(b.y + b.height for b in sorted_boxes)
        avg_conf = sum(b.confidence for b in sorted_boxes) / len(sorted_boxes)

        return TextBox(
            text=merged_text,
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            confidence=avg_conf
        )

    def __str__(self) -> str:
        preview = self.text[:50].replace("\n", " ")
        return f"OCRResult({len(self.boxes)} boxes, conf={self.confidence:.2f}, '{preview}...')"


class OCREngine(ABC):
    """
    OCR 엔진 추상 클래스 (Strategy Interface)

    모든 OCR 엔진 구현체는 이 클래스를 상속받아야 합니다.

    구현 예시:
        class MyOCREngine(OCREngine):
            def recognize(self, image: np.ndarray) -> OCRResult:
                # OCR 로직 구현
                pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """엔진 이름 반환"""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """지원 언어 목록 반환"""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """엔진 초기화 (모델 로딩 등)"""
        pass

    @abstractmethod
    def recognize(self, image: np.ndarray, language: Optional[str] = None) -> OCRResult:
        """
        이미지에서 텍스트 인식

        Args:
            image: numpy 배열 형태의 이미지 (BGR 또는 RGB)
            language: 인식할 언어 코드 (None이면 자동 감지)

        Returns:
            OCRResult: 인식 결과
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """리소스 정리"""
        pass

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        이미지 전처리 (선택적 오버라이드)

        기본 구현은 원본 이미지를 그대로 반환합니다.
        필요시 서브클래스에서 오버라이드하세요.
        """
        return image

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
