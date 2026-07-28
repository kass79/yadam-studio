# 🪟 윈도우(Windows) 설치 가이드 — 비개발자용

이 문서는 개발 경험이 없어도 따라할 수 있도록 순서대로 정리한 윈도우 전용 설치 안내서입니다.
(코드는 이미 윈도우에서 돌아가도록 수정되어 있습니다.)

---

## 1단계. 필수 프로그램 설치 (한 번만 하면 됨)

아래 3개를 공식 사이트에서 내려받아 설치하세요. 전부 "다음 → 다음 → 설치"로 진행하면 됩니다.

| 프로그램 | 내려받는 곳 | 설치 시 주의사항 |
|---|---|---|
| **Node.js** (LTS 버전) | https://nodejs.org | 기본 옵션 그대로 설치 |
| **Python** (3.10 이상) | https://www.python.org/downloads | ⚠️ 설치 첫 화면에서 **"Add Python to PATH"** 체크박스 반드시 체크! |
| **Chrome** | https://www.google.com/chrome | 이미 설치되어 있으면 생략 |

설치 후 확인: **시작 버튼 → "cmd" 입력 → 명령 프롬프트 실행** 후 아래 두 줄을 입력했을 때 버전 번호가 나오면 성공입니다.

```
node -v
python --version
```

---

## 2단계. 프로젝트 폴더에서 의존성 설치 (한 번만 하면 됨)

명령 프롬프트(cmd)에서 이 폴더(`7_threads_auto`)로 이동한 뒤 순서대로 입력:

```
cd 7_threads_auto 폴더의 실제 경로
npm install
pip install playwright
playwright install chromium
```

> 💡 폴더 경로를 쉽게 넣는 법: 탐색기에서 `7_threads_auto` 폴더를 연 뒤, 주소창에 `cmd` 라고 입력하고 엔터를 치면 그 폴더에서 바로 명령 프롬프트가 열립니다.

---

## 3단계. API 키 설정 (한 번만 하면 됨)

1. 이 폴더 안의 `.env.example` 파일을 복사해서 이름을 `.env` 로 바꿉니다.
2. 메모장으로 열어 각 항목에 실제 키를 붙여넣습니다.
   - `GEMINI_API_KEY`: https://aistudio.google.com 에서 무료 발급
   - `RAPIDAPI_KEY`, `APIFY_TOKEN_*`: 각 서비스 가입 후 발급 (수집 기능용)
   - `THREADS_ACCESS_TOKEN` 등: Meta 개발자 계정 (댓글 자동응답 기능용 — 없어도 기본 포스팅은 가능)

> ⚠️ `.env` 파일에는 비밀 키가 들어가므로 절대 남에게 보내거나 GitHub에 올리지 마세요.

---

## 4단계. 실행하기 (쓸 때마다)

**① 크롬을 자동화 모드로 켜기** — 명령 프롬프트에서:

```
python setup.py
```

크롬 창이 새로 뜹니다. 그 창에서 **Threads(threads.net)에 로그인**해 두세요. (처음 한 번만 로그인하면 유지됩니다)

**② 수집·큐레이션 파이프라인 실행:**

```
node start.js
```

**③ 포스팅/예약 발행** (예: 2시간 뒤 예약):

```
python .agents\skills\publish_to_threads\scripts\web_publish.py --text-file 글파일.md --schedule 2
```

---

## 자주 나는 오류

| 증상 | 해결법 |
|---|---|
| `'python'은(는) 내부 또는 외부 명령...` | Python 설치 시 "Add Python to PATH"를 안 체크한 것. Python을 재설치하며 체크 |
| `연결 실패! setup.py로 크롬이...` | ①번(`python setup.py`)을 먼저 실행하지 않은 것 |
| 붙여넣은 한글이 깨짐 | 이 저장소의 최신 버전을 다시 받기 (윈도우용 클립보드 수정이 포함된 버전) |
| API 키 오류 | `.env` 파일의 키 값에 따옴표나 공백이 들어가지 않았는지 확인 |
