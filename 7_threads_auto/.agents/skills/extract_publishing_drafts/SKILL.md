---
name: extract_publishing_drafts
description: curate_raw_posts 스킬을 통해 생성된 큐레이션 마크다운 파일(일반 트렌드, 인플루언서 트렌드)에서 상위 1~3번 포스트의 '순수 발행 초안 본문'과 '참고 URL'만을 추출하여 총 6개의 독립된 md 파일로 분리 저장하는 스킬입니다.
---

# ✂️ 트위터 발행 초안 추출기 (extract_publishing_drafts)

이 스킬은 완성된 큐레이션 마크다운 파일에서 제목이나 불필요한 메타데이터를 완벽히 걷어내고, 복사-붙여넣기(또는 자동 API 발행)에 즉시 사용할 수 있는 **순도 100%의 발행 초안 텍스트**만을 발췌해 내는 에이전트 자율 워크플로우입니다.

---

## 1. 작업 대상 및 입출력 규약 (I/O Specification)

### 입력 (Input Files)
에이전트는 사용자가 지정한(또는 가장 최신의) 타겟 폴더 `output/{YYMMDD_시간}/` 내부에 있는 다음 두 파일을 읽어야 합니다.
- `twitter_{YYMMDD_시간}.md` (일반 트렌드)
- `twitter_influencer_{YYMMDD_시간}.md` (인플루언서)

### 출력 (Output Files)
동일한 폴더 내부에 아래의 네이밍 컨벤션에 따라 **총 6개의 분할된 파일**을 생성하여 저장(`write_to_file`)해야 합니다. (YYMMDD는 원본 파일명에 기재된 날짜를 그대로 씁니다.)
- **일반 트렌드 1~3번 추출본**:
  - `{YYMMDD}_twitter_1.md`
  - `{YYMMDD}_twitter_2.md`
  - `{YYMMDD}_twitter_3.md`
- **인플루언서 1~3번 추출본**:
  - `{YYMMDD}_twitter_influencer_1.md`
  - `{YYMMDD}_twitter_influencer_2.md`
  - `{YYMMDD}_twitter_influencer_3.md`

---

## 2. 정밀 텍스트 추출 가이드라인 (Extraction Rules)

각 원본 파일에서 상위 3개의 포스트 블록만을 타겟팅하여 총 3개의 추출본을 생성합니다.

### 🚫 [콘텐츠 필터링 (Content Filtering)]
- 원본 포스트 내용이 너무 짧거나 의미 없는 단순 코멘트(예: "it’s time to lock in", "yes", 이모지만 있는 경우 등)인 경우, 해당 포스트는 과감히 건너뛰고 **그다음 순위의 포스트를 선택**하여 항상 정보가 꽉 찬 유의미한 3개의 초안을 확보해야 합니다.

### 🚫 [절대 제외해야 할 내용]
- 포스트 번호 제목 (`## [1] @username 포스팅 분석` 등)
- 번역 섹션 및 제목 (`### 1. 한국어 번역` 등)
- 내용 정리 섹션 및 제목 (`### 2. 핵심 내용 정리` 등)
- **발행 초안 섹션의 제목 행 전체 (`### 3. 트위터(X) 발행 초안 (안 A)` 등)** -> 이 줄은 텍스트에 포함시키지 마십시오.

### ✅ [반드시 포함해야 할 내용]
- 발행 초안 섹션 제목 바로 아랫줄부터 시작되는 **실제 본문(초안) 텍스트 전체**
- 초안 본문에 포함된 팩트/시사점 글머리 기호 리스트
- 포스트 맨 마지막의 **`참고 URL : https://...` 텍스트 라인**

### 💡 [추출 예시]

**원본 내용 일부**:
```markdown
### 3. 트위터(X) 발행 초안 (안 A)
최근 해외 테크 씬에서 주목받고 있는 방식에 대해 정리해 봤어.
단순한 도구 소개를 넘어서, 실무 파이프라인에 어떻게 적용될 수 있을지가 핵심인 것 같아.

👉 실무 시사점 (최대 3개)
- Claude Opus 4.8에서는 프롬프트 캐시를 깨지 않고도 작업 중간에 지시사항을 변경할 수 있음

참고 URL : https://x.com/swyx/status/2060044644193624253
```

**추출하여 새 파일에 저장할 내용**:
```markdown
최근 해외 테크 씬에서 주목받고 있는 방식에 대해 정리해 봤어.
단순한 도구 소개를 넘어서, 실무 파이프라인에 어떻게 적용될 수 있을지가 핵심인 것 같아.

👉 실무 시사점 (최대 3개)
- Claude Opus 4.8에서는 프롬프트 캐시를 깨지 않고도 작업 중간에 지시사항을 변경할 수 있음

참고 URL : https://x.com/swyx/status/2060044644193624253
```

---

## 3. 이미지 생성 가이드라인 (Image Generation)

에이전트는 텍스트 추출이 끝난 6개의 초안 본문을 각각 분석하여 내용에 어울리는 다이어그램/그래프 이미지를 함께 생성해야 합니다.

### [필수 스타일 프롬프트]
> **"Academic figure, IEEE/CVPR paper style, schematic, clean lines, white background"**
(학술 그림, IEEE/CVPR 논문 스타일, 개략도, 깔끔한 선, 흰색 배경)

### [프롬프트 예시]
1. **다이어그램(Diagram) 예시**:
   `A conceptual diagram showing 5 interconnected nodes representing different language skills (Reading, Writing, Listening, Speaking, Vocabulary), Academic figure, IEEE/CVPR paper style, schematic, clean lines, white background`
2. **그래프(Graph) 예시**:
   `A graph showing the forgetting curve and the effect of spaced repetition on vocabulary retention, Academic figure, IEEE/CVPR paper style, schematic, clean lines, white background`

### [이미지 저장 규약 (Naming Convention)]
이미지는 텍스트 파일과 1:1로 매칭되도록 동일 폴더에 `.png` 확장자로 저장합니다.
- `{YYMMDD}_twitter_1.png`
- `{YYMMDD}_twitter_2.png`
- `{YYMMDD}_twitter_3.png`
- `{YYMMDD}_twitter_influencer_1.png`
- `{YYMMDD}_twitter_influencer_2.png`
- `{YYMMDD}_twitter_influencer_3.png`

---

## 4. 에이전트 자율 실행 (Execution Step)

1. 사용자가 타겟 폴더를 주면 해당 폴더의 2개 파일을 읽습니다.
2. 위 추출 규칙을 완벽하게 적용하여 6개의 개별 마크다운 파일로 각각 `write_to_file` 을 수행합니다.
3. 6개의 추출된 본문에서 핵심 팩트를 파악한 뒤, 영어 프롬프트를 설계합니다.
4. 에이전트 내장 툴(`generate_image` 등)을 호출하여 각 본문과 짝을 이루는 6개의 이미지를 생성해 저장합니다.
5. 모든 텍스트와 이미지 세트(총 12개 파일)가 예쁘게 생성되었는지 검증하고 작업 완료를 보고합니다.
