---
name: ingest-raw-posts
description: 실행일 기준 어제 날짜(D-1)를 기준으로 Apify의 X(Twitter) Scraper API를 호출해 실시간 테크/AI 트렌드 포스팅들을 수집하고, output 디렉토리 하위에 실시간 타임스탬프 폴더(YYMMDD_HHMM)를 자동 생성하여 정규화된 규격의 raw 마크다운 파일(*_raw_*.md)을 생성해 주는 에이전트 전용 데이터 수집 스킬입니다.
---

# 🌀 X(Twitter) Raw 포스팅 수집 및 폴더 생성 스킬 (ingest-raw-posts)

이 스킬은 에이전트가 외부 소셜 플랫폼(X)의 최신 바이럴 테크 정보를 API 통신으로 자동 크롤링하고, 가공 스킬이 바로 읽을 수 있는 명밀한 raw 마크다운 파일과 output 폴더 구조를 실시간 기동 구축하기 위한 규격 매뉴얼입니다.

---

## 1. 수집 스케줄 및 타겟 날짜 생성 (Target Date)
* **타겟팅 기준**: 실행일(오늘) 기준 **D-1 어제 날짜**의 하루치 트렌드 수집.
* **[중요 - 날짜 및 시간 크로스체크 의무 룰]**:
  - 에이전트는 크롤링 타겟 날짜를 설정하기 전에, **반드시 시스템 타임스탬프와 환경 메타데이터를 상호 검증**하십시오.
  - 필요한 경우, 터미널 환경에서 `date` 혹은 `date +%Y-%m-%d` 명령어를 직접 1회 실행하여 **물리적인 현재 날짜와 시간 정보가 메타데이터와 오차가 없는지 직접 실증**하십시오.
  - 수집 프로세스 기동 직후에는 콘솔 로그에 `현재 시각: {지금 시각}` 및 `타겟 계산 날짜: {계산된 D-1 날짜}`를 데코레이션 로그 형태로 칼같이 뿌려 에이전트가 인지하고 있음을 확인시켜 주어야 합니다.
* **날짜 생성 공식 (JavaScript/Node.js 예시)**:
  ```javascript
  const getYesterdayDateString = () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yyyy = yesterday.getFullYear();
    const mm = String(yesterday.getMonth() + 1).padStart(2, '0');
    const dd = String(yesterday.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`; // 예: "2026-05-26"
  };
  ```

---

## 2. Apify Scraper 실행 및 데이터 수집 프로토콜 (API Ingestion)

에이전트는 `.env` 파일에 기록된 `APIFY_TOKEN_X` 토큰을 확보하여 다음의 Apify Actor 엔드포인트를 호출합니다.

### 2-1. X (Twitter) 수집 프로토콜
* **사용 Actor ID**: `danek/twitter-scraper-ppr` (또는 지정된 X Scraper Actor)
* **POST 요청 엔드포인트**: `https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs` 또는 direct Actor run
* **파라미터 규격**:
  - `query`: `(AI agent)` (AND 조건 검색)
  - `onlyQuery`: true
  - `since`: 어제 날짜 (`YYYY-MM-DD`)
  - `until`: 오늘 날짜 (`YYYY-MM-DD`)
  - `maxItems`: 최소 20개 이상 수집 설정

---

## 3. output 폴더 생성 및 raw 파일 조립 규격 (Output Directory & File Assembly)

### 3-1. 폴더 생성 (Directory Creation)
* **생성 경로**: `output/{YYMMDD_HHMM}`
  - `YYMMDD`: 년/월/일 각 2자리 (예: `260527`)
  - `HHMM`: 현재 실행 시각의 시/분 2자리 (예: 13시 15분 실행 시 `1315`)
  - **합산 폴더명 예시**: `output/260527_1315`

### 3-2. Raw 파일 조립 규격 (File Formatting)
수집된 데이터셋(JSON 배열)을 파싱하여 아래의 엄격히 통일된 마크다운 마스터 규격으로 조립하여 써냅니다.

#### **X (Twitter) Raw 파일 규격 (`twitter_raw_{YYMMDD_HHMM}.md`)**
```markdown
# 🐦 X(Twitter) Raw 수집 데이터 ({YYMMDD_HHMM})

- **수집 일시**: {월/일/년, 시:분:초 AM/PM}
- **총 수집 개수**: {N}개

---

## [1] @{작성자_ID} (좋아요: {좋아요수} | 댓글: {댓글수})
- **작성일**: {ISO_타임스탬프}
- **URL**: [링크 이동]({게시글_X_URL})
- **본문 내용**:
> {게시글 본문 원문 텍스트 (줄바꿈이 있을 경우 인용구 기호 '>'를 라인마다 장착할 것)}

---

## [2] @{작성자_ID} ...
```

---

## 4. 에이전트 자율 점검망 (Verification Gate)
1. **중복 배제**: 각 포스팅의 중복 수집을 원천적으로 막기 위해, 고유 ID 또는 URL을 기준으로 유일성(Deduplication) 필터를 반드시 적용합니다.
2. **폴더 무결성**: 폴더를 생성할 때 부모 디렉토리가 부재하면 재귀적 생성(`fs.mkdirSync(dir, { recursive: true })`)을 수행해 충돌을 방지합니다.
3. **네이밍 검증**: 생성된 파일명이 `_raw_` 규격을 칼같이 준수하는지 최종 확인합니다.
