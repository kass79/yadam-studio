---
name: auto_trend_pipeline
description: 트위터(X) 트렌드 수집부터 내용 큐레이션, 발행 초안 추출 및 이미지 생성, 그리고 2시간 간격 쓰레드 릴레이 자동 포스팅까지 원스톱으로 처리하는 통합 워크플로우입니다.
---

# 🚀 쓰레드 자동화 풀 파이프라인 (Auto Trend Pipeline)

본 워크플로우는 사용자의 개입 없이 에이전트 자율 모드로 **트렌드 수집 ➡️ 큐레이션 ➡️ 발행물 준비(이미지 포함) ➡️ 최종 자동 포스팅**까지의 전 과정을 4단계에 걸쳐 논스톱으로 수행하는 가이드라인입니다.

---

## 🔁 파이프라인 실행 순서 (4-Step)

에이전트는 이 워크플로우가 트리거되면 반드시 아래 순서대로 스킬을 순차 실행해야 합니다. 앞 단계가 실패하면 즉시 중단하고 보고합니다.

### Step 1: 데이터 수집 (Ingestion)
* **사용 스킬**: `ingest_raw_posts`
* **동작**: 어제(D-1) 기준 X(Twitter) Scraper API를 구동하여 실시간 테크/AI 트렌드 raw 데이터를 가져옵니다.
* **결과물**: `output/{YYMMDD_HHMM}` 폴더 및 내부에 `*_raw_*.md` 파일 생성

### Step 2: 큐레이션 및 정제 (Curation)
* **사용 스킬**: `curate_raw_posts`
* **동작**: Step 1에서 생성된 폴더 내의 raw 파일들을 읽어, 딥리딩 및 Gemini 2.5를 통해 다정한 반말 톤의 명품 마크다운 결과물로 정제/번역합니다.
* **결과물**: 동일 폴더 내에 큐레이션 완제품 파일(일반 트렌드, 인플루언서 트렌드) 생성

### Step 3: 발행물 초안 쪼개기 및 이미지 생성 (Extraction & Image Generation)
* **사용 스킬**: `extract_publishing_drafts`
* **동작**: Step 2의 결과물에서 상위 1~3번 포스트만 떼어내 총 6개의 쪼개진 텍스트 파일(`{YYMMDD}_twitter_*.md`)을 만듭니다. 동시에 내장 프롬프트를 활용해 6개의 학술적 다이어그램 이미지(`.png`)를 1:1로 함께 생성합니다.
* **결과물**: 동일 폴더 내에 발행용 텍스트 6개 + 매칭 이미지 6개 안착

### Step 4: 릴레이 자동 포스팅 장전 (Publishing Orchestration)
* **사용 스킬**: `publish_to_threads` (`web_publish.py` 사용)
* **동작**:
  Step 3에서 분할된 6개의 명품 요약 텍스트와 이미지 세트 경로를 확인하고, `web_publish.py` 스크립트를 순차적으로 6번 호출하여 Threads 대기열에 예약합니다.
  이때 `--schedule` 인자값으로 상대 시간 변수(2, 4, 6, 8, 10)를 사용하면 브라우저의 현재 시간대를 실시간 조회하여 2시간 간격 릴레이를 무결하게 빌드합니다.

  ```bash
  # [사전 준비] setup.py로 크롬 디버깅 포트 9222를 열고 Threads 로그인을 마쳐야 작동합니다.
  # 1번째 포스트 (즉시 게시)
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_1.md" --image-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_1.png"
  
  # 2번째 포스트 (2시간 뒤 예약)
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_2.md" --image-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_2.png" --schedule "2"
  
  # 3번째 포스트 (4시간 뒤 예약)
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_3.md" --image-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_3.png" --schedule "4"
  
  # 4번째 포스트 (6시간 뒤 예약)
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_4.md" --image-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_4.png" --schedule "6"
  
  # 5번째 포스트 (8시간 뒤 예약)
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_5.md" --image-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_5.png" --schedule "8"
  
  # 6번째 포스트 (10시간 뒤 예약)
  python3 .agents/skills/publish_to_threads/scripts/web_publish.py --text-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_6.md" --image-file "output/{YYMMDD_HHMM}/{YYMMDD}_twitter_6.png" --schedule "10"
  ```
* **결과물**: 6개의 명품 요약 콘텐츠와 학술적 다이어그램 png 이미지가 Threads 실제 예약 대기열에 2시간 간격으로 오차 없이 안착하며 풀 파이프라인이 성공적으로 종료됩니다.

