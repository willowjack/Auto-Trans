"""
RapidOCR 엔진 구현체

RapidOCR: 가볍고 빠른 오프라인 OCR 라이브러리
https://github.com/RapidAI/RapidOCR
"""

from typing import Optional
import numpy as np

from core.interfaces.ocr_engine import OCREngine, OCRResult


class RapidOCREngine(OCREngine):
    """RapidOCR 기반 OCR 엔진"""

    def __init__(self):
        self._engine = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "RapidOCR"

    @property
    def supported_languages(self) -> list[str]:
        return ["ko", "en", "ja", "zh"]

    def initialize(self) -> None:
        """RapidOCR 엔진 초기화"""
        if self._initialized:
            return

        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            self._initialized = True
        except ImportError:
            raise ImportError(
                "RapidOCR이 설치되지 않았습니다. "
                "'pip install rapidocr_onnxruntime' 명령어로 설치하세요."
            )

    def recognize(self, image: np.ndarray, language: Optional[str] = None) -> OCRResult:
        """
        이미지에서 텍스트 인식

        Args:
            image: numpy 배열 형태의 이미지
            language: 언어 코드 (RapidOCR은 자동 감지)

        Returns:
            OCRResult: 인식 결과
        """
        if not self._initialized:
            self.initialize()

        result, elapse = self._engine(image)

        if result is None:
            return OCRResult(text="", confidence=0.0, bounding_boxes=[])

        texts = []
        boxes = []
        total_confidence = 0.0

        for line in result:
            box_points, text, confidence = line
            texts.append(text)
            total_confidence += confidence

            # 바운딩 박스 변환 (4점 -> x,y,w,h)
            x_coords = [p[0] for p in box_points]
            y_coords = [p[1] for p in box_points]
            boxes.append({
                "x": int(min(x_coords)),
                "y": int(min(y_coords)),
                "w": int(max(x_coords) - min(x_coords)),
                "h": int(max(y_coords) - min(y_coords)),
                "text": text
            })

        avg_confidence = total_confidence / len(result) if result else 0.0

        return OCRResult(
            text="\n".join(texts),
            confidence=avg_confidence,
            bounding_boxes=boxes
        )

    def cleanup(self) -> None:
        """리소스 정리"""
        self._engine = None
        self._initialized = False
