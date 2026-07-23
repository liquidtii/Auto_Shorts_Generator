# 🎬 Auto Shorts Generator

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/yourusername/auto-shorts-generator.svg?style=social&label=Star)](https://github.com/yourusername/auto-shorts-generator)

*Read this in other languages: [English](README.md) | [한국어](README.ko.md).*

<p align="center">
  <img src="assets/demo1.png" width="32%" />
  <img src="assets/demo2.png" width="32%" />
  <img src="assets/demo3.png" width="32%" />
</p>

긴 원본 영상을 분석하여 가장 흥미로운 하이라이트("훅")를 찾아내고, 틱톡(TikTok), 유튜브 쇼츠(YouTube Shorts), 인스타그램 릴스(Reels) 등에 적합한 숏폼 비디오로 자동 편집해 주는 파이썬 툴입니다.

## ✨ 주요 기능

- **대화형 CLI**: 누구나 쉽게 사용할 수 있는 메뉴 방식의 터미널 인터페이스를 제공합니다.
- **스마트 훅 추출 (Hook Extraction)**: 대형 언어 모델(**Gemini** 또는 **OpenAI**)을 활용하여 영상의 텍스트를 분석하고 가장 바이럴 가능성이 높은 구간을 찾아냅니다.
- **고성능 음성 인식**: `faster-whisper`를 사용하여 빠르고 정확하게 음성을 텍스트로 변환합니다.
- **동적 얼굴 인식 트래킹**: 가로 비율(16:9) 영상에서 인물의 얼굴을 자동으로 인식하여, 화면의 중앙에 오도록 세로 비율(9:16)로 스마트하게 크롭(Crop)합니다.
- **바운싱 자막 (Bouncing Subtitles)**: 틱톡 스타일의 단어별 강조 자막(Word-by-word)과 역동적인 바운스 효과를 자동 생성합니다.
- **자동 배경 블러**: 원본 영상의 비율이 맞지 않는 빈 공간을 블러 처리된 원본 영상으로 채워 고급스러운 느낌을 줍니다.

## 🛠 필수 조건

1. **Python 3.12** 이상
2. **FFmpeg**: 시스템 PATH에 반드시 설치 및 등록되어 있어야 합니다.
3. **GPU (권장)**: Whisper의 빠른 음성 인식 및 영상 인코딩(NVENC)을 위해 NVIDIA GPU 사용을 적극 권장합니다.

## 📦 설치 방법

이 프로젝트는 빠르고 편리한 파이썬 패키지 매니저인 [uv](https://github.com/astral-sh/uv)를 사용합니다.

1. 레포지토리를 클론합니다:
   ```bash
   git clone https://github.com/yourusername/auto-shorts-generator.git
   cd auto-shorts-generator
   ```

2. 의존성 패키지를 설치합니다 (`pyproject.toml` 및 `uv.lock`을 기반으로 가상 환경을 자동 생성하고 설치합니다):
   ```bash
   uv sync
   ```

## 🚀 시작하기

`uv` 명령어를 사용하여 메인 스크립트를 실행합니다:

```bash
uv run main.py
```

### 초기 설정 (Initial Setup)
프로그램을 처음 실행하면 초기 설정 화면이 나타납니다. 다음 항목들을 입력해야 합니다:
- **LLM 제공자 (LLM Provider)**: `gemini` 또는 `openai` 중 하나를 선택하세요.
- **API Key**: 선택한 LLM 제공자의 API 키를 입력하세요.
- **기타 설정**: 결과물이 저장될 폴더, Whisper 모델 크기 (tiny, base, small, medium, large), 자막 폰트 설정 등.

*모든 설정은 `settings.json`에 저장되므로 매번 다시 입력할 필요가 없습니다.*

## 📂 프로젝트 구조

- `main.py`: 프로그램의 시작점입니다. 대화형 CLI 메뉴와 사용자 설정을 관리하며 비디오 생성 파이프라인을 통제합니다.
- `extractor.py`: 비디오에서 오디오를 추출하고, `faster-whisper`로 음성을 인식한 뒤, 선택한 LLM API를 통해 훅(Hook) 구간을 분석합니다.
- `video_editor.py`: `moviepy`와 `OpenCV`를 사용한 비디오 편집의 핵심 엔진입니다. 얼굴 트래킹, 9:16 크롭, 배경 블러, 오디오 믹싱, 그리고 단어 단위 자막 생성을 담당합니다.
- `requirements.txt`: 프로젝트 실행에 필요한 파이썬 패키지 목록입니다.

## ⚙️ 설정 (settings.json)
`settings.json` 파일을 직접 수정하거나, CLI 메뉴(2번 옵션)를 통해 설정을 변경할 수 있습니다.
- `llm_provider`: "gemini" 또는 "openai"
- `model_size`: Whisper 모델 크기 (기본값: "base")
- `max_duration`: 생성될 쇼츠의 최대 길이 (단위: 초, 기본값: 60)
- `highlight_color`: 자막에서 현재 말하고 있는 단어의 강조 색상 (기본값: "yellow")

## 🤷‍♂️ GPU 이슈 (GPU Issues)

**RTX 50XX 시리즈**
현재 NVIDIA RTX 50 시리즈 그래픽 카드의 경우 라이브러리 호환성 문제로 인해 Whisper 음성 인식 속도가 예상보다 상당히 느려지는 현상이 발생할 수 있습니다. 이는 기저 라이브러리들의 알려진 문제이며, 향후 라이브러리 업데이트를 통해 해결될 예정입니다.

## 📄 라이선스 (License)
이 프로젝트는 오픈 소스이며 MIT 라이선스를 따릅니다.
