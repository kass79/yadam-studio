---
name: create_twitter_image
description: 큐레이션된 마크다운 트위터(X) 초안의 내용을 바탕으로 첨부할 학술적이고 깔끔한 개념도(다이어그램/그래프) 이미지를 생성하는 스킬입니다.
---

# 🎨 트위터(X) 첨부용 개념도 이미지 생성 스킬 (create_twitter_image)

이 스킬은 텍스트로만 이루어진 트위터 초안에 시각적인 깊이와 신뢰성을 더하기 위해, 에이전트가 직접 포스트의 핵심 내용을 분석하여 '학술적 다이어그램' 스타일의 이미지를 생성하는 절차를 규정합니다.

---

## 1. 프롬프트 작성 가이드라인 (Image Generation Prompt)
에이전트는 큐레이션된 본문(핵심 인사이트, 시사점 등)을 분석하여 아래의 공통 텍스트를 반드시 덧붙여 프롬프트를 구성해야 합니다.

### [필수 스타일 프롬프트]
> **"Academic figure, IEEE/CVPR paper style, schematic, clean lines, white background"**
(학술 그림, IEEE/CVPR 논문 스타일, 개략도, 깔끔한 선, 흰색 배경)

### [프롬프트 예시]
1. **다이어그램(Diagram) 예시**:
   `A conceptual diagram showing 5 interconnected nodes representing different language skills (Reading, Writing, Listening, Speaking, Vocabulary), Academic figure, IEEE/CVPR paper style, schematic, clean lines, white background`
2. **그래프(Graph) 예시**:
   `A graph showing the forgetting curve and the effect of spaced repetition on vocabulary retention, Academic figure, IEEE/CVPR paper style, schematic, clean lines, white background`

---

## 2. 이미지 생성 워크플로우 (Workflow)

1. **포스트 선정**: 작성 완료된 `twitter_{YYMMDD_HHMM}.md` 또는 `twitter_influencer_{YYMMDD_HHMM}.md` 파일에서 이미지가 필요한 핵심 포스트를 1~5개 선정합니다.
2. **개념 설계**: 각 포스트의 핵심 팩트(예: AI 프롬프트 캐시 구조, Trust-by-default DB 접근 방식 등)를 도식화(Diagram)하거나 그래프(Graph)로 표현할 영어 프롬프트를 작성합니다.
3. **이미지 생성**: 에이전트 내장 이미지 생성 툴(`generate_image` 등)을 호출하여 이미지를 생성합니다.
4. **저장 및 네이밍 규약 (Naming Convention)**:
   - 생성된 이미지는 대상 마크다운 파일이 존재하는 폴더(예: `output/{YYMMDD_HHMM}/`)에 직접 저장합니다.
   - **일반 포스트**: `twitter_{포스트 번호}.png` (예: `twitter_8.png`)
   - **인플루언서 포스트**: `twitter_influencer_{포스트 번호}.png` (예: `twitter_influencer_2.png`)
