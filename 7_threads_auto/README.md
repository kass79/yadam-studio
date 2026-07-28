# Threads Autonomous Curation & Hybrid Automation Pipeline (v4.0)

본 에이전트는 다양한 소셜 및 테크 플랫폼(X, Threads, Hacker News, GitHub)에서 가장 바이럴되는 최신 AI 트렌드와 인사이트를 API로 똑똑하게 수집하고, 대형 언어 모델(Gemini 2.5)을 사용해 고품격 큐레이션 콘텐츠로 재구성한 뒤, **Playwright 브라우저 자동화(CDP)를 연동해 웹 UI 상에서 안전하게 예약 포스팅 및 'AI' 카테고리 설정까지 무결하게 완수**하는 **최첨단 하이브리드 자동화 에이전트**입니다.

과거의 불안정한 공식 API 포스팅 sleep 방식을 완전히 극복하고, 로컬에서 실행 중인 Chrome 디버깅 포트(9222)와 직접 CDP(Chrome DevTools Protocol) 연동을 취하여 실제 Threads 예약 및 카테고리 엔진을 네이티브하게 제어합니다.

---

## 🌟 주요 특징 (Key Features)

1. **하이브리드 아키텍처 (API Ingestion + Playwright CDP Publishing)**: 
   - 데이터 수집은 가볍고 신속한 **API-Driven 비동기 파이프라인**을 고수합니다.
   - 포스팅 발행은 공식 API의 예약 기능 부재 및 토큰 한계를 극복하고자 **Playwright 기반의 안전한 웹 디버깅 크롬 제어 방식**을 채택했습니다.
2. **상대 시간 기반 실시간 예약 연산 고안**:
   - CLI 인자로 `"2"` 또는 `"4"` 와 같이 정수 시간만 넘겨주면, 스크립트가 브라우저 내에서 자바스크립트로 **현지 크롬 브라우저의 실시간 시각을 100% 무결하게 직접 조회**하여 시차 오차 없이 정확히 +2시간, +4시간 뒤로 자동 예약 입력을 진행합니다.
3. **클립보드 고속 붙여넣기 (`pbcopy` + `Cmd+V`)**:
   - 텍스트 입력 시 한 글자씩 타이핑하는 방식 대신, 본문을 시스템 클립보드에 안전하게 복사한 뒤 브라우저에 단축키(`Cmd+V`)로 즉시 붙여넣는 기법을 탑재했습니다. 속도가 비약적으로 단축되었으며, 인간의 일반적인 긴 글 포스팅 방식과 완벽히 일치하여 봇 우회 시인성을 극대화합니다.
4. **달력 오늘 날짜 오선택/토글 방지 로직**:
   - 달력 팝업 오픈 시 이미 오늘 날짜가 기본으로 선택되어 있는 점을 활용, `hh`/`mm` 시간 인풋창이 활성화되어 있다면 불필요하게 날짜 버튼을 다시 누르지 않도록 설계되었습니다. (재클릭 시 선택이 해제되어 인풋창이 꺼지는 버그를 완벽히 해결)
5. **주제(카테고리) 'AI' 자동 설정**:
   - 스레드 작성 시 프로필 옆의 `커뮤니티 또는 주제` 버튼을 물리적으로 클릭하고, 팝업된 옵션창에서 화면에 활성화된 `AI` 카테고리를 정확히 식별해 자동 설정함으로써 노출과 알고리즘 분류 점수를 극대화합니다.
6. **초경량 내장 Webhook 대댓글 응대**:
   - 포스팅 발행은 웹 UI 디버깅을 사용하되, 유저 댓글 실시간 대댓글 소통은 Meta 공식 API의 실시간 Webhook POST 및 **Node.js http 내장 초경량 웹훅 서버**를 연동하여 가볍고 친근한 반말 톤으로 즉시 대응합니다.
7. **에러 고립화 및 Graceful Degradation 기술**: 
   - 특정 소셜 미디어 크롤러 API가 차단되거나 속도 제한에 걸리더라도, 정상적으로 구동된 다른 플랫폼의 정보만 모아 발행 파이프라인으로 매끄럽게 전달하며, 최악의 경우 사전에 준비된 Mock 테크 데이터가 가동되어 파이프라인의 붕괴를 원천 방어합니다.

---

## 📂 폴더 구조 (Project Directory Structure)

본 프로젝트는 고도의 모듈성, 에러 격리성(Fault Isolation), 그리고 **자율 에이전트의 이해 용이성(Agentic Semantics)**을 극대화하기 위해 설계된 엄격한 7계층 구조를 따릅니다.

```text
threads_from_x/
├── start.js             # 메인 API-Driven 수집 오케스트레이터 및 실행 스케줄러 (동작 조율)
├── setup.py             # 사용자 실제 크롬 프로필을 복제해 9222 디버깅 포트로 안전하게 실행하는 스크립트
├── package.json         # 프로젝트 의존성 라이브러리 및 실행 스크립트 정의
├── package-lock.json    # 의존성 패키지 무결성 보장을 위한 락 파일
├── .env                 # API 키, 토큰, 환경변수 및 시스템 모드 관리 저장소 (로컬 전용)
├── README.md            # [본 문서] 설치 방법, 사용 방법, 상세 폴더 아키텍처 안내서
├── AGENTS.md            # 에이전트용 심화 아키텍처 및 복구 가이드 (Operations Playbook)
├── plan_checklist.md    # 프로젝트 라이프사이클의 정밀 진척도와 세부 일감 리스트
├── history.md           # 수행 완료된 모든 인프라/엔지니어링 작업에 대한 누적 로그북
│
├── .agents/             # 지능형 자율 에이전트 협업 및 오퍼레이션 영역
│   ├── skills/          # AI 에이전트가 자율적으로 프로젝트 업무를 실행할 때 로딩하는 전용 규격 스킬셋
│   │   ├── ingest_raw_posts/  # [수집 스킬] 어제 날짜(D-1) 기준 X/Threads 트렌드 크롤링 및 로컬 저장 명세
│   │   │   └── SKILL.md       # 수집 도구, 파라미터, 폴더명 규칙(YYMMDD_HHMM) 및 저장 규칙 선언
│   │   ├── curate_raw_posts/  # [가공 스킬] 수집된 raw 마크다운의 명품 큐레이션 정제 및 가공 명세
│   │   │   └── SKILL.md       # 딥리딩 모듈 기동, 번역 퀄리티 제어, 다정한 반말 톤앤매너 프롬프팅 지침
│   │   ├── extract_publishing_drafts/ # [추출 스킬] 큐레이션된 파일에서 상위 초안을 추출하고 개념도 이미지 생성 명세
│   │   │   └── SKILL.md       # 1~3번 포스트 분할 파일 생성 및 create_twitter_image 연동 가이드
│   │   └── publish_to_threads/ # [발행 스킬] Playwright CDP를 활용한 Threads Web UI 자동 포스팅 및 예약 명세
│   │       ├── SKILL.md       # 브라우저 원격 조작, 달력 DatePicker 제어, 토글-프루프 UI 핸들링 가이드
│   │       └── scripts/
│   │           └── web_publish.py # Playwright CDP 기반 실시간 포스팅 및 시간 동적 예약 실행 파이썬 핵심 코어
│   │
│   └── workflows/        # 에이전트 자율 워크플로우 정의 영역
│       └── auto_trend_pipeline.md # [통합 워크플로우] 수집부터 가공, 6개 초안 분할 및 2시간 간격 예약 발행 풀 파이프라인
│
├── lib/                 # 도메인별 핵심 로직 및 비동기 엔진 서브시스템
│   ├── ingestion/       # 이기종 소셜/테크 데이터 병렬 수집 파이프라인
│   │   ├── twitter_threads.js  # Apify Actor를 연동해 X 및 Threads의 급상승 트렌드 추출
│   │   ├── opinions.js         # 글로벌 오피니언 리더 3인의 최신 AI 기술 타임라인 밀착 트래킹
│   │   └── tech_deepdive.js    # Hacker News 공식 Firebase API 및 GitHub Search API 딥다이브 엔진
│   │
│   └── logger.js        # 콘솔 가시성 및 디버깅 시인성을 극대화한 다채로운 로거 모듈
│
└── output/              # 타임스탬프 기반 수집/가공/초안 완제품 결과물들이 보관되는 물리 저장소
```

---

## 🛠️ 설치 및 사용 준비 (Setup & Installation)

이 프로젝트는 Python(Playwright) 브라우저 자동화와 Node.js API 백그라운드 서버 환경이 조화롭게 융합되어 작동합니다.

### 1. 의존성 패키지 설치
```bash
# Node.js 의존성 다운로드
npm install

# Python 및 Playwright 브라우저 환경 설정
pip install playwright
playwright install chromium
```

### 2. 크롬 디버깅 모드 구동 (매우 중요)
자동화 발행을 시작하기 전, 실제 사용 중인 Chrome 브라우저의 프로필을 복제하여 9222 포트가 열린 상태로 구동해야 합니다. 
```bash
python3 setup.py
```
* Chrome이 디버깅 모드로 자동 켜지면, **Threads 홈페이지(www.threads.net)에 접속하여 로그인**을 한 번 마쳐 둡니다. 로그인 세션은 디버깅 프로필 내에 영구적으로 안전하게 보관됩니다.

### 3. 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 다음과 같이 설정합니다.
```env
# AI Curation API
GEMINI_API_KEY=your_gemini_api_key_here

# 데이터 수집 크롤러 API (RapidAPI / Apify)
RAPIDAPI_KEY=your_rapidapi_key_here
APIFY_TOKEN_X=your_apify_token_x_here
APIFY_TOKEN_THREADS=your_apify_token_threads_here

# 웹훅 및 실시간 대댓글용 (공식 API 자격증명)
THREADS_ACCESS_TOKEN=your_threads_access_token_here
THREADS_USER_ID=your_threads_user_id_here
WEBHOOK_VERIFY_TOKEN=your_custom_verify_token
PORT=3000
```

---

## 🚀 사용 방법 (Usage)

### 1. 통합 자동화 풀 파이프라인 작동 (`/auto_trend_pipeline`)
에이전트에게 `/auto_trend_pipeline` 워크플로우 작동을 명령하면, 수집부터 가공, 이미지 생성 및 2시간 간격 예약 발행 릴레이까지 100% 무개입 자율 모드로 다음과 같이 차례대로 실행됩니다:

1. **Step 1**: `ingest_raw_posts` 스킬 가동 ➡️ 어제자(D-1) X/Threads raw 파일 수집.
2. **Step 2**: `curate_raw_posts` 스킬 가동 ➡️ 딥리딩 및 Gemini 2.5를 통한 고품격 한국어 번역 가공 및 초안 템플릿 생성.
3. **Step 3**: `extract_publishing_drafts` 스킬 가동 ➡️ 상위 3개 콘텐츠를 총 6개의 쪼개진 텍스트+이미지 세트로 분할 빌드.
4. **Step 4**: `publish_to_threads` 스킬 가동 ➡️ `web_publish.py`를 6회 릴레이 구동하여 2시간 단위 예약 대기열 안착 완료!

### 2. 수동 포스팅 및 예약 개별 호출
원하는 텍스트와 이미지 파일을 타겟해 개별적으로 발행하거나 2시간 뒤 예약을 설정할 때는 아래와 같이 터미널에 입력하여 안전하게 실행합니다.

* **즉시 발행**:
  ```bash
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/260531_0524/260531_twitter_3.md" --image-file "output/260531_0524/260531_twitter_3.png"
  ```
* **동적 예약 발행 (숫자 변수로 간편히 제어)**:
  ```bash
  # 현재 브라우저 시각을 기준으로 정확히 2시간 뒤에 예약 포스팅 진행
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/260531_0524/260531_twitter_3.md" --image-file "output/260531_0524/260531_twitter_3.png" --schedule "2"
  
  # 현재 브라우저 시각을 기준으로 정확히 4시간 뒤에 예약 포스팅 진행
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/260531_0524/260531_twitter_3.md" --image-file "output/260531_0524/260531_twitter_3.png" --schedule "4"
  ```

---

## 📖 추가 아키텍처 지침서
에이전트의 상세 비동기 7계층 아키텍처 다이어그램, 9222 크롬 포트 충돌 및 팝업 딜레이 대응 지침 등 심화 기술 노하우는 [AGENTS.md](AGENTS.md) 문서에 심화 기술되어 있습니다.
