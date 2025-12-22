"""
RapidOCR 엔진 구현체

RapidOCR: 가볍고 빠른 오프라인 OCR 라이브러리
- ONNX Runtime 기반으로 빠른 추론
- 한국어, 영어, 일본어, 중국어 지원
- GPU 가속 지원 (선택적)

https://github.com/RapidAI/RapidOCR
"""

import time
from typing import Optional, List
import numpy as np

from core.interfaces.ocr_engine import OCREngine, OCRResult, TextBox, Language


class RapidOCREngine(OCREngine):
    """
    RapidOCR 기반 OCR 엔진

    특징:
    - ONNX Runtime 사용으로 빠른 추론
    - 텍스트 검출 + 인식 파이프라인
    - 한국어, 영어, 일본어, 중국어 기본 지원

    성능 팁:
    - GPU 사용 시 onnxruntime-gpu 설치
    - 이미지 해상도가 너무 크면 리사이즈 고려
    """

    # 언어별 RapidOCR 설정 매핑
    LANGUAGE_CONFIG = {
        "ko": {"rec_model_dir": None},  # 기본 모델 (한중일영 통합)
        "en": {"rec_model_dir": None},
        "ja": {"rec_model_dir": None},
        "zh-cn": {"rec_model_dir": None},
        "zh-tw": {"rec_model_dir": None},
        "auto": {"rec_model_dir": None},
    }

    def __init__(
        self,
        use_gpu: bool = False,
        det_use_cuda: bool = False,
        rec_use_cuda: bool = False,
        print_verbose: bool = False
    ):
        """
        Args:
            use_gpu: GPU 사용 여부 (CUDA)
            det_use_cuda: 텍스트 검출에 CUDA 사용
            rec_use_cuda: 텍스트 인식에 CUDA 사용
            print_verbose: 상세 로그 출력
        """
        self._engine = None
        self._initialized = False
        self._use_gpu = use_gpu
        self._det_use_cuda = det_use_cuda or use_gpu
        self._rec_use_cuda = rec_use_cuda or use_gpu
        self._print_verbose = print_verbose

        # 성능 통계
        self._total_recognitions = 0
        self._total_time_ms = 0.0

    @property
    def name(self) -> str:
        return "RapidOCR"

    @property
    def supported_languages(self) -> list[str]:
        return ["ko", "en", "ja", "zh-cn", "zh-tw", "auto"]

    @property
    def avg_processing_time_ms(self) -> float:
        """평균 처리 시간 (밀리초)"""
        if self._total_recognitions == 0:
            return 0.0
        return self._total_time_ms / self._total_recognitions

    def initialize(self) -> None:
        """RapidOCR 엔진 초기화"""
        if self._initialized:
            return

        try:
            from rapidocr_onnxruntime import RapidOCR

            # RapidOCR 초기화 옵션
            self._engine = RapidOCR(
                det_use_cuda=self._det_use_cuda,
                rec_use_cuda=self._rec_use_cuda,
                print_verbose=self._print_verbose
            )
            self._initialized = True

            if self._print_verbose:
                print(f"[RapidOCR] 초기화 완료 (GPU: {self._use_gpu})")

        except ImportError:
            raise ImportError(
                "RapidOCR이 설치되지 않았습니다.\n"
                "설치: pip install rapidocr_onnxruntime\n"
                "GPU 사용: pip install onnxruntime-gpu"
            )
        except Exception as e:
            raise RuntimeError(f"RapidOCR 초기화 실패: {e}")

    def recognize(self, image: np.ndarray, language: Optional[str] = None) -> OCRResult:
        """
        이미지에서 텍스트 인식

        Args:
            image: numpy 배열 형태의 이미지 (BGR, HWC 형식)
            language: 언어 코드 (현재는 자동 감지만 지원)

        Returns:
            OCRResult: 인식 결과 (텍스트, 박스, 신뢰도 등)
        """
        if not self._initialized:
            self.initialize()

        start_time = time.perf_counter()

        # 이미지 전처리
        processed_image = self.preprocess_image(image)

        # OCR 수행
        try:
            result, elapse = self._engine(processed_image)
        except Exception as e:
            print(f"[RapidOCR] 인식 오류: {e}")
            return OCRResult(text="", boxes=[], confidence=0.0)

        # 결과 파싱
        if result is None or len(result) == 0:
            processing_time = (time.perf_counter() - start_time) * 1000
            return OCRResult(
                text="",
                boxes=[],
                confidence=0.0,
                processing_time_ms=processing_time
            )

        boxes: List[TextBox] = []
        texts: List[str] = []
        total_confidence = 0.0

        for line in result:
            # line 형식: [box_points, text, confidence]
            # box_points: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            box_points, text, confidence = line

            # 4점 좌표를 바운딩 박스로 변환
            x_coords = [p[0] for p in box_points]
            y_coords = [p[1] for p in box_points]

            x = int(min(x_coords))
            y = int(min(y_coords))
            width = int(max(x_coords) - min(x_coords))
            height = int(max(y_coords) - min(y_coords))

            # 폴리곤 좌표 저장 (회전된 텍스트용)
            polygon = [(int(p[0]), int(p[1])) for p in box_points]

            text_box = TextBox(
                text=text,
                x=x,
                y=y,
                width=width,
                height=height,
                confidence=confidence,
                polygon=polygon
            )

            boxes.append(text_box)
            texts.append(text)
            total_confidence += confidence

        # 처리 시간 계산
        processing_time = (time.perf_counter() - start_time) * 1000

        # 통계 업데이트
        self._total_recognitions += 1
        self._total_time_ms += processing_time

        # 평균 신뢰도 계산
        avg_confidence = total_confidence / len(result) if result else 0.0

        # 언어 감지 (간단한 휴리스틱)
        detected_language = self._detect_language("\n".join(texts))

        return OCRResult(
            text="\n".join(texts),
            boxes=boxes,
            confidence=avg_confidence,
            language=detected_language,
            processing_time_ms=processing_time
        )

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        이미지 전처리

        게임 화면에 최적화된 전처리를 수행합니다:
        - 너무 큰 이미지는 리사이즈
        - 필요시 그레이스케일 변환
        """
        if image is None or image.size == 0:
            return image

        # 이미지가 너무 크면 리사이즈 (성능 최적화)
        max_dimension = 1920
        h, w = image.shape[:2]

        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)

            try:
                import cv2
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            except ImportError:
                # cv2 없으면 그냥 사용
                pass

        return image

    def _detect_language(self, text: str) -> str:
        """
        간단한 언어 감지

        문자 유니코드 범위를 기반으로 주요 언어를 감지합니다.
        """
        if not text:
            return "auto"

        # 문자 카운트
        korean = 0
        japanese = 0
        chinese = 0
        english = 0

        for char in text:
            code = ord(char)

            # 한글
            if 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
                korean += 1
            # 일본어 (히라가나, 카타카나)
            elif 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
                japanese += 1
            # 한자 (CJK)
            elif 0x4E00 <= code <= 0x9FFF:
                chinese += 1  # 한중일 공통이지만 일단 중국어로
            # 영어
            elif 0x0041 <= code <= 0x007A:
                english += 1

        # 가장 많은 문자 유형으로 판단
        counts = {
            "ko": korean,
            "ja": japanese,
            "zh-cn": chinese,
            "en": english
        }

        max_lang = max(counts, key=counts.get)

        # 충분한 문자가 없으면 auto
        if counts[max_lang] < 3:
            return "auto"

        return max_lang

    def cleanup(self) -> None:
        """리소스 정리"""
        self._engine = None
        self._initialized = False

        if self._print_verbose:
            print(f"[RapidOCR] 정리 완료 (총 {self._total_recognitions}회, "
                  f"평균 {self.avg_processing_time_ms:.1f}ms)")

    def reset_stats(self) -> None:
        """성능 통계 초기화"""
        self._total_recognitions = 0
        self._total_time_ms = 0.0

    def get_stats(self) -> dict:
        """성능 통계 반환"""
        return {
            "total_recognitions": self._total_recognitions,
            "total_time_ms": self._total_time_ms,
            "avg_time_ms": self.avg_processing_time_ms
        }
