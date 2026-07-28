# 🎬 야담 스튜디오 (yadam-studio)

야담·사연·임사체험 유튜브 채널의 **영상 제작 작업소**입니다.
Claude 세션을 이 저장소로 열면 아래 자동화들이 바로 장착됩니다.

## 사용법 (딱 이것만 기억)

1. claude.ai/code에서 새 작업 시작
2. 저장소: **yadam-studio** / 환경: **영상제작** (☁️ 구름 아이콘에서 선택)
3. 대본(docx)과 그림 4장을 첨부하고:

> **"티저 만들어줘"**

끝. 훅 선정 → 자막 연출 → 켄번즈 줌 → 사운드 합성(→ TTS 나레이션) → MP4 완성까지 자동입니다.

## 이 저장소에 들어있는 것

| 폴더 | 역할 |
|---|---|
| `.claude/skills/story-teaser` | ⭐ "티저 만들어줘" 자동화 — 대본+그림 → 6~15초 티저 MP4 |
| `.claude/skills/auto-edit` | 화면 녹화 + 얼굴 촬영 폴더 → 자동 편집 (템플릿 기반) |
| `.claude/skills/watch` | 영상 분석 — 유튜브 링크/영상 파일을 프레임+자막으로 분석 |
| `7_threads_auto/` | Threads 자동 포스팅 도구 (윈도우 PC에서 실행) |
| `HYPERFRAMES_설치가이드.md` | HTML→영상 렌더링 도구 설치법 (윈도우/비개발자용) |

## 자주 쓰는 말

- `티저 만들어줘. 여자 목소리로` — 나레이션 목소리 변경
- `티저 만들어줘. 10초로 짧게` — 길이 조절
- `티저 만들어줘. 쇼츠용 세로로` — 9:16 비율 (기본은 16:9)
- `이 영상 분석해줘 + 링크/파일` — 참고 영상 분석 (환경에 YouTube 도메인 허용 필요)

## 환경 설정 (한 번만)

"영상제작" 클라우드 환경의 Network access를 **Custom**으로 하고 아래 도메인 허용:

```
speech.platform.bing.com
*.youtube.com
youtube.com
youtu.be
*.googlevideo.com
*.ytimg.com
```

- 첫 줄: TTS 나레이션용 / 나머지: 유튜브 영상 분석용
- "Also include default list of common package managers" 체크 필수

설정 스크립트 (세션 시작 시 도구 자동 설치 — 티저 제작이 3분 빨라짐):

```bash
#!/bin/bash
apt-get update -qq && apt-get install -y -qq ffmpeg fonts-noto-cjk fonts-noto-cjk-extra
pip install --break-system-packages -q numpy edge-tts
```
