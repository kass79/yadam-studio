---
name: edu-video
description: 안전교육 자료(운전정보 공문 사진, 사고사례, 수칙 텍스트)로 1~2분 교육영상을 만든다. 카스가 "교육영상 만들어줘", "사고사례 영상", "이 공문으로 영상" 같은 요청과 함께 자료 사진/텍스트를 주면 이 스킬을 쓴다. 카드형 슬라이드 + 차분한 남성 나레이션 + 잔잔한 BGM으로 MP4를 렌더링한다. 슬기로운 승무생활 앱의 교육영상 카테고리에 올리는 용도.
---

# 안전교육 영상 제작 (슬기로운 승무생활용)

공문 사진/텍스트 → **60~120초 교육영상 MP4**. 티저(story-teaser)와 목적이 다르다:
궁금하게 만드는 게 아니라 **끝까지 정확하게 전달**하는 것. 결말 숨기기 금지 규칙 없음.

공통 환경 절차(폰트 설치, TTS 프록시 인증서, 렌더 검증 루프)는
**story-teaser 스킬과 동일**하니 그쪽 SKILL.md를 함께 참고할 것.

## 작업 순서

### 1. 자료 읽기

- 공문 사진이면 `Read`로 읽고 내용을 구조화한다: **발생개요 → 원인 → 대책/수칙**.
- 사진 속 표·그래프는 영상에 넣지 않는다 (화질 나쁨). 내용을 텍스트 카드로 재구성.
- 날짜·역명·열차번호 같은 사실관계는 공문 그대로. 지어내지 말 것.
- 개인 식별 정보(기관사 이름·사번)는 공문에 있어도 **영상에 넣지 않는다**.

### 2. 구성 짜기 (기본 틀)

1. `title` — 문서번호 + 사건명 + "사고사례 교육" 킥커
2. `text` ×1~2 — 발생개요 (언제·어디서·무슨 일)
3. `rules` — 원인 (1차/2차)
4. `rules` — 재발방지 수칙 (핵심 3개 이내)
5. `steps` — 절차가 있으면 (조치 순서, 지적확인환호 4단계 등)
6. `end` — 한 줄 다짐 + "신정승무사업소" CTA

문장은 공문투를 구어로 다듬되 용어(PSD, 관제보고, 지적확인환호)는 그대로 쓴다.
나레이션용 문장에서는 영문 약어를 소리나는 대로 적는다 (PSD→피에스디, HMI→에이치엠아이).

### 3. 프로젝트 + spec

```bash
npx hyperframes init edu --non-interactive --example=blank && cd edu && npm install gsap --silent
```

`edu_spec.json`: `{"title", "duration", "accent", "slides":[...]}`.
슬라이드 필드는 `scripts/build_edu.py` 상단 주석 참고. `accent` 기본값은
2호선 초록(#00A84D) — 노선이 다른 사례면 해당 노선 색으로.

### 4. 나레이션 먼저 → 타이밍 확정 (티저와 같은 원칙)

슬라이드당 나레이션 1문장씩 voice.json으로 만들어 story-teaser의 make_voice.py로 합성:

```bash
python3 <story-teaser>/scripts/make_voice.py voice.json --voice ko-KR-InJoonNeural --rate=-8% --out voice
```

silencedetect로 실제 발화 길이 재고 → **슬라이드 dur = 발화 + 1.5~2초**로 확정.
슬라이드 시작 +0.4초에 나레이션 배치 (adelay = start×1000 + 400).

### 5. 생성 → 검증 → 렌더 → 믹스

```bash
S=<이 스킬 경로>/scripts
python3 $S/build_edu.py edu_spec.json > index.html
python3 $S/make_edu_bgm.py edu_spec.json bgm.wav
npx hyperframes check && npx hyperframes snapshot --at <슬라이드 중간들>  # Read로 눈검수
npx hyperframes render
# 믹스: BGM 0.30, 나레이션 adelay 배치 — 명령은 story-teaser SKILL.md와 동일 패턴
```

30MB 넘으면 `-crf 23`으로 재인코딩 (카드 영상이라 화질 손실 거의 없음).
완성본은 SendUserFile로 보내고, 카스가 앱 글쓰기 → 교육영상 카테고리에 첨부한다.

## 하지 말 것

- 사고 당사자를 특정하거나 비난하는 표현 (교육 목적, 사람 아닌 행동에 초점)
- 90초 초과 시 내용 삭제보다 슬라이드 분할을 먼저 검토
- 스냅샷 눈검수 없이 렌더링
