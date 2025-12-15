# Auto-Trans

실시간 화면 텍스트 번역 앱을 만들고 운용할 때 참고할 수 있는 실행 가이드입니다. Google Cloud Vision OCR과 Google AI Studio(혹은 DeepL) 번역기를 사용해 화면의 텍스트를 자동 감지·번역하고, 화자/문맥을 이어받아 표시하는 흐름을 정리했습니다.

## 사전 준비
1. **운영체제**: Windows 10 1903 이상(화면 캡처 API 필요).
2. **개발 환경**: Python 3.10+ 권장. 가상환경을 만들어 진행하세요.
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install --upgrade pip
   ```
3. **필수 라이브러리 설치**: 화면 캡처·OCR·번역 호출에 필요한 라이브러리를 설치합니다.
   ```bash
   pip install opencv-python-headless pillow numpy google-cloud-vision google-generativeai deepl
   ```
4. **Google Cloud Vision**
   - GCP 프로젝트 생성 후 Vision API 사용 설정.
   - 서비스 계정 키(JSON) 발급 후 `GOOGLE_APPLICATION_CREDENTIALS` 환경변수로 경로 지정.
5. **번역 키 설정**
   - **Google AI Studio**: API 키 발급 후 `GEMINI_API_KEY` 환경변수에 저장.
   - **DeepL**: API 키 발급 후 `DEEPL_API_KEY` 환경변수에 저장.

## 기본 실행 흐름
1. **화면 캡처 시작**
   - `winrt.windows.graphics.capture` 또는 Desktop Duplication API로 모니터/창을 실시간 캡처합니다.
   - 캡처 FPS와 해상도는 15~30fps, 1080p 이하로 시작해 리소스 상황에 따라 조정하세요.
2. **텍스트 변화 감지 및 디바운스**
   - 연속 프레임의 차이(예: SSIM 또는 `absdiff`)가 임계치 이상일 때만 OCR 대기열에 추가합니다.
   - 텍스트 변화가 멈춘 뒤 1초 동안 추가 변화가 없으면 마지막 캡처를 OCR로 보냅니다.
3. **OCR 호출**
   - Google Cloud Vision의 `text_detection`으로 이미지를 보내고, `fullTextAnnotation`을 받아 행/단락별 텍스트와 좌표를 추출합니다.
   - 결과에 타임스탬프와 프레임 ID를 붙여 번역 단계로 넘깁니다.
4. **번역 및 문맥 유지**
   - 번역 엔진은 설정에서 Gemini 또는 DeepL 중 선택합니다.
   - 직전 번역 5~10개의 히스토리를 프롬프트에 포함해 화자·말투를 일관되게 유지합니다.
   - 동일 좌표 영역에서 반복되는 텍스트는 동일 화자/등장인물로 태깅하여 용어/말투를 유지합니다.
5. **표시 및 저장**
   - 투명 오버레이 창을 항상-위로 띄워 번역문을 원문 근처에 렌더링합니다(화자별 색상/말풍선 권장).
   - SQLite 등 로컬 DB에 세션/캡처/OCR/번역/화자 정보를 저장하여 중단 후 재개가 가능하게 합니다.

## 실행 예시(템플릿)
아래 예시는 핵심 흐름을 담은 의사 코드에 가깝습니다. 실제 프로젝트 구조에 맞춰 함수만 연결하면 됩니다.
```python
from capture import capture_stream  # 화면 캡처 제너레이터
from vision import run_ocr          # Google Vision OCR 호출
from translate import translate     # Gemini 또는 DeepL 래퍼
from overlay import draw_overlay    # 투명 오버레이 렌더러
from context import Memory          # 화자/문맥 메모리

memory = Memory()
for frame in capture_stream(debounce_secs=1.0):
    ocr_blocks = run_ocr(frame.image)
    text_with_context = memory.attach_context(ocr_blocks)
    translated = translate(text_with_context, engine="gemini")
    memory.save(translated)
    draw_overlay(translated)
```

## 문제 해결 팁
- **성능**: 텍스트 변화가 적을 때는 캡처 FPS를 낮추고, OCR 입력 이미지를 720p로 축소하면 API 비용과 지연을 줄일 수 있습니다.
- **안정성**: 번역 API 429/5xx 응답 시 지수 백오프 후 재시도하고, 네트워크 장애 시 요청을 로컬 큐에 적재했다가 복구 시 처리하세요.
- **보안**: API 키는 `.env`나 Windows Credential Manager에 저장하고, 커밋되지 않도록 `.gitignore`에 추가합니다.

## 다음 단계
- UI(오버레이 + 설정 패널) 구현 후 단축키(일시정지/재개)를 추가하세요.
- 번역 로그에 화자/말투 메타데이터를 포함해 의역 품질을 높이고, 재시작 시 최근 히스토리를 자동 복원하세요.

## GitHub에 저장하는 방법 (체크리스트)
실제 구현을 진행한 뒤 결과물을 GitHub에 올리려면 아래 순서로 진행하세요.

1. **현재 상태 확인**
   ```bash
   git status
   ```
   수정 파일이 맞는지, 불필요한 파일(환경설정, 캐시, 키 파일 등)이 포함되지 않았는지 확인하세요.

2. **Git 초기화/원격 설정**
   - 아직 Git이 초기화되지 않았다면: `git init`
   - 새 원격 저장소를 만들고 HTTPS/SSH URL을 `origin`으로 추가하세요.
   ```bash
   git remote add origin <your-repo-url>
   ```

3. **커밋 작성**
   ```bash
   git add .
   git commit -m "Add initial real-time translation app"  # 또는 변경 요약 메시지
   ```
   서비스 계정 키나 `.env` 파일은 반드시 `.gitignore`에 넣어 커밋하지 않도록 합니다.

4. **브랜치 푸시**
   ```bash
   git push -u origin main  # 또는 사용 중인 브랜치 이름
   ```
   권한 오류가 나면 GitHub Personal Access Token(HTTPS) 또는 SSH 키 설정을 확인하세요.

5. **배포/릴리스 준비**
   - 동작 확인 후 태그를 추가하거나 Release를 생성해 배포 패키지를 관리합니다.
   - CI가 있는 경우(예: GitHub Actions) 기본 테스트가 통과하는지 확인하세요.

> 번역 로그나 화면 캡처처럼 민감한 데이터는 공개 저장소에 올리지 말고, 필요 시 전용 프라이빗 리포를 사용하세요.
