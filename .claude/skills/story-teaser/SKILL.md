---
name: story-teaser
description: 사연·임사체험·야담 롱폼 스크립트와 일러스트 몇 장으로 6~15초 하이라이트 티저(예고편) 영상을 만든다. 사용자가 대본(docx/txt/붙여넣기)과 이미지를 주며 "하이라이트 만들어줘", "티저 만들어줘", "쇼츠용 예고편", "이걸로 짧은 영상" 같은 요청을 하면 이 스킬을 쓴다. 자막 연출·켄번즈 줌·번개 효과·자체 합성 BGM까지 넣어 MP4로 렌더링한다.
---

# 사연/야담 하이라이트 티저 제작

롱폼 대본 + 일러스트 → **6~15초 티저 MP4**. 본편 유도가 목적이므로
"궁금하게 만들고 끊는" 것이 최우선이다. 카스는 비개발자다 — 진행은 쉬운 말로 보고한다.

## 준비 (없을 때만)

```bash
which ffmpeg || (apt-get update -qq && apt-get install -y -qq ffmpeg)
python3 -c "import numpy" || pip install --break-system-packages -q numpy
ls ~/.claude/skills/hyperframes >/dev/null || npx hyperframes skills update
# 한글 명조 폰트 — 없으면 자막이 고딕 대체로 렌더링돼 스타일이 죽는다 (실측 2026-07)
fc-match "Noto Serif CJK KR" | grep -qi "Noto Serif" || \
  (apt-get install -y -qq fonts-noto-cjk fonts-noto-cjk-extra && fc-cache -f)
```

## 작업 순서

### 1. 소재 확보

- **대본**: docx면 `/docx` 스킬로 읽는다. `pandoc`은 이 환경에 없으니 쓰지 말 것.
- **이미지**: 채팅에 붙여넣은 그림은 파일로 저장되지 않는다. 세션 기록에서 추출한다:

```bash
python3 <<'EOF'
import json, base64
from pathlib import Path
jl = Path("~/.claude/projects/<프로젝트>/<세션id>.jsonl").expanduser()
out = Path("assets"); out.mkdir(exist_ok=True)
n = 0
for line in jl.open(encoding="utf-8"):
    if '"image"' not in line: continue
    try: obj = json.loads(line)
    except Exception: continue
    for item in (obj.get("message") or {}).get("content") or []:
        if isinstance(item, dict) and item.get("type") == "image":
            src = item.get("source", {}); d = src.get("data")
            if d:
                n += 1
                ext = {"image/png":"png","image/jpeg":"jpg","image/webp":"webp"}.get(
                    src.get("media_type",""), "png")
                (out / f"img{n}.{ext}").write_bytes(base64.b64decode(d))
print(n, "장 추출")
EOF
```

세션에 이전 티저의 그림이 남아 있으면 다 뽑히니, **이번에 첨부된 마지막 N장만**
쓴다 (`imgs[-4:]`). 추출 직후 `Read`로 한 장씩 보고 무엇이 그려졌는지 확인할 것.

**그림에 글씨가 박혀 있는 경우** (썸네일용으로 만든 그림이면 흔하다):
자막과 겹쳐 이중으로 보이므로 **글씨 띠를 잘라내고 16:9로 다시 만든다.**
행별 밝은 픽셀 수로 글씨 띠 위치를 찾은 뒤 crop → Lanczos 확대 → 언샵으로 복원한다:

```python
from PIL import Image, ImageFilter
im = Image.open("assets/img1.webp").convert("RGB").crop((x0, y0, x1, y1))  # 16:9 비율로
im = im.resize((1920, 1080), Image.LANCZOS)
im.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=3)).save("assets/img1_c.jpg", quality=95)
```

이렇게 만든 그림은 이미 1920×1080이므로 `source_size`를 `[1920, 1080]`,
`focus`를 `0.5`로 둔다. 크롭 후 **반드시 `Read`로 확인** — 글씨 잔상이 위아래
가장자리에 남기 쉽고, 인물 얼굴이 잘리기도 한다.

**글씨가 띠가 아니라 그림 곳곳에 흩어져 있으면** (도표형 썸네일 — 크롭 불가):
cv2 인페인팅으로 글자만 지운다 (실측 2026-08, 지구단면 도표에서 성공):

1. 글자 위치는 세로 띠를 잘라 눈금 그려 `Read`로 확인 후 상자 좌표를 잡는다
2. 상자 안 밝은 픽셀(`gray > 205`)만 마스크 → `dilate(5×5)×2` → `cv2.inpaint(..., 6, INPAINT_TELEA)`
3. 남은 얼룩은 `medianBlur(41)` 배경과의 차(>12) 마스크로 1~2회 더 지운다
4. **상자 전체를 통째로 채우는 INPAINT_NS는 금지** — 밝은 줄무늬 사각형이 생긴다
5. 옅은 잔광 얼룩은 완벽히 안 지워져도 된다 — 줌·그레인·어두운 그레이딩에 묻힌다

**배경이 밝은 그림**(하늘·설경·흰 배경)은 흰 자막이 묻힌다. 그 그림에만
하단 어둡기를 구워 넣는다 (다른 그림은 이미 어두우니 건드리지 말 것):

```python
import numpy as np
a = np.asarray(im).astype(np.float32); h = a.shape[0]
k = np.clip((np.arange(h, dtype=np.float32)/h - 0.40) / 0.50, 0, 1) ** 1.25
Image.fromarray(np.clip(a * (1 - 0.72*k)[:, None, None], 0, 255).astype("uint8")).save(out, quality=95)
```

### 2. 훅 선정 (가장 중요한 단계)

대본을 읽고 **결말을 알려주지 않으면서 가장 궁금하게 만드는** 문장 3~4개를 뽑는다.
각 문장은 이미지 한 장에 대응한다. 원칙:

- 마지막 자막은 **반드시 미완결**로 끝낸다 (결말 공개 금지)
- 문장당 강조어 1개를 정한다 — 감정의 정점이거나 반전을 암시하는 단어
- 한 줄은 짧게. 2줄 구성(`line1` 평서 → `line2` 강조 포함)이 기본
- 이미지 순서는 대본 시간순을 따르되, 가장 강한 그림을 마지막 바로 앞에 배치

**이미지와 자막의 내용이 어긋나면 안 된다.** 그림에 없는 장면을 자막으로 말하지 말 것.
등장인물의 성별·나이도 확인한다 — 그림 속 인물이 대본의 주인공과 다르면
(예: 여성 주인공 이야기인데 그림은 현대 남성) 3인칭 대신 **시청자를 부르는 문장**으로
바꾸면 그림과도 맞고 몰입도 올라간다 (「彼女の後ろに」→「あなたの後ろにも」).

### 3. 프로젝트 스캐폴드

```bash
npx hyperframes init teaser --non-interactive --example=blank
cd teaser && npm install gsap --silent
mkdir -p assets && cp <이미지들> assets/
```

### 4. spec.json 작성

`references/spec-example.json`을 복사해 채운다. 필드 설명은 그 파일 주석 참고.
`focus`는 이미지에서 **인물 얼굴의 가로 위치**(0=왼쪽 끝, 1=오른쪽 끝)다 —
이미지를 직접 `Read`해서 눈으로 확인하고 정할 것. 잘못 잡으면 얼굴이 잘린다.

### 5. 생성 → 검증 → 렌더링

```bash
S=<이 스킬 경로>/scripts
python3 $S/build_teaser.py spec.json > index.html
python3 $S/make_bgm.py spec.json bgm.wav    # build가 넣는 <audio src="bgm.wav">가 이 파일을 참조

export PUPPETEER_EXECUTABLE_PATH=/opt/pw-browsers/chromium
npx hyperframes check                       # 0 error 나올 때까지
npx hyperframes snapshot --at 1.5,7.5,10.2  # 반드시 Read로 눈으로 확인
npx hyperframes render                      # 3~5분 소요
```

check가 `gsap_exit_missing_hard_kill` 오류를 내면: 어떤 자막의 끝(start+dur)이
샷의 start와 0.1초 이내로 물려 있는 경우다. 자막 `dur`를 0.2초쯤 줄여서 띄운다
(실측 2026-08). `overlapping_gsap_tweens`·`track_too_dense` 경고는 정상이다.

**스냅샷을 반드시 `Read`로 직접 볼 것.** check가 통과해도 얼굴이 잘리거나
자막이 인물을 가리는 건 잡히지 않는다.

### 6. 오디오 합치기 → 납품

```bash
ffmpeg -y -i renders/<렌더된>.mp4 -i bgm.wav -c:v copy -c:a aac -b:a 192k -shortest 최종.mp4
```

나레이션 음성(`voice.wav`)이 있으면 BGM을 깔개로 낮춰 함께 믹스한다:

```bash
ffmpeg -y -i renders/<렌더된>.mp4 -i voice.wav -i bgm.wav \
  -filter_complex "[2:a]volume=0.35[b];[1:a][b]amix=inputs=2:duration=longest:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest 최종.mp4
```

완성 파일은 `SendUserFile`로 보낸다.

## 스타일 3종

`spec.json`의 `style` 값으로 고른다. 상세는 `references/styles.md`.

| 값 | 이름 | 어울리는 소재 |
|---|---|---|
| `cinematic` | 시네마틱 미스터리 (기본) | 사연, 임사체험 — 어두운 톤, 붉은 강조 |
| `scroll` | 야담 두루마리 | 전설, 옛날 이야기 — 세피아, 강한 그레인 |
| `punchy` | 킬러 쇼츠 훅 | 알고리즘 노출용 — 노란 강조, 굵은 고딕 |

## 화면 비율

`aspect`: `"16:9"`(기본, 카스 선호) 또는 `"9:16"`(쇼츠·릴스).
생성기가 자막 크기·위치·비네트를 비율에 맞춰 자동 조정한다.

## 자막 언어

`lang`: `"ko"`(기본) / `"ja"` / `"zh"`. 한자는 언어마다 자형이 달라
(예: 直·骨·令) 맞는 글꼴을 써야 원어민에게 자연스럽다. 이 값이 `<html lang>`과
글꼴(Noto Serif CJK **KR/JP/SC**)을 함께 바꾼다. 폰트는 `fonts-noto-cjk` 한 패키지에
세 언어가 다 들어 있으니 추가 설치는 필요 없다.

목소리도 언어에 맞춰 바꾼다 — `make_voice.py --voice=<이름>`:

| 언어 | 남성 | 여성 |
|---|---|---|
| 한국어 | `ko-KR-InJoonNeural` (차분), `ko-KR-HyunsuNeural` | `ko-KR-SunHiNeural` |
| 일본어 | `ja-JP-KeitaNeural` (성우 톤, 남성은 이것뿐) | `ja-JP-NanamiNeural` |

일본어는 한국어보다 조금 빠르게 읽히므로 `--rate=-10%` 정도가 알맞다.
자막도 일본어가 더 짧게 끝나니 문장을 한 뼘 더 길게 잡아도 된다.

## 나레이션 음성 (TTS) — 매번 자동 시도할 것

티저 제작 때마다 **edge-tts 접근을 먼저 시도한다** (환경 허용 도메인에
`speech.platform.bing.com`이 추가되어 있으면 성공한다):

```bash
pip install --break-system-packages -q edge-tts
# 이 환경의 프록시가 TLS를 가로채므로 프록시 인증서를 certifi에 먼저 추가해야 한다.
# 안 하면 CERTIFICATE_VERIFY_FAILED로 실패한다 (실측 2026-07: 추가하면 성공).
python3 - <<'EOF'
import certifi, pathlib
ca = pathlib.Path("/root/.ccr/ca-bundle.crt")
b = pathlib.Path(certifi.where())
if ca.exists() and ca.read_text() not in b.read_text():
    b.write_text(b.read_text() + "\n" + ca.read_text())
EOF
timeout 30 python3 <스킬경로>/scripts/make_voice.py spec.json --out voice
```

각 mp3 꼬리에 ~1.3초 무음이 붙는다. 배치 계산은 `ffprobe` 전체 길이가 아니라
`silencedetect`로 잰 **실제 발화 길이**로 할 것 — 15초 안에 4문장이 들어간다.
문장이 길면 자막 두 줄을 다 읽히지 말고 **핵심 구절만** 따로 뽑아 합성한다
(spec과 별개의 voice용 json을 만들어 `make_voice.py`에 넘기면 된다).

**나레이션은 자막 `line2`(강조 줄)만 읽게 하는 것이 기본이다.** `line1`은 눈으로
읽는 배경 설명, `line2`는 귀로 듣는 한 방 — 이렇게 나누면 4컷 + 엔드카드가
15초에 정확히 들어간다. 다섯 문장이 모두 들어가야 하므로 길이 예산을 먼저 잡을 것:

- 한국어 발화 길이 ≈ **글자수 × 0.20초**, 문장부호(쉼표·마침표)마다 **+0.4초**
- 쉼표를 하나 지우면 0.4초가 빈다 — 길이가 모자랄 때 가장 먼저 손댈 곳
- 발화 총합이 12초를 넘으면 숨 쉴 틈이 없다. 넘으면 문장을 더 줄인다
  (실측 예: 13자 "그 강단 앞에서 쓰러졌습니다." → 2.57초)

합성 → 측정 → **측정값에 맞춰 spec 타이밍을 정한다.** 반대 순서로 하지 말 것.

**성공하면 (voice/ 에 mp3 생성됨) — 전자동 나레이션 믹스:**

1. 각 mp3 길이를 `ffprobe`로 재고, 문장이 자막 표시 시간보다 길면
   `spec.json`의 해당 자막 `dur`(과 이후 타이밍)을 음성 길이 +0.4초로 늘려 재빌드한다.
2. 문장별 mp3를 자막 시작 시각에 `adelay`로 배치하고, BGM은 -10dB로 덕킹해 믹스:

```bash
ffmpeg -y -i renders/<렌더>.mp4 \
  -i voice/01.mp3 -i voice/02.mp3 -i voice/03.mp3 -i voice/04.mp3 -i voice/05_end.mp3 \
  -i bgm.wav -filter_complex "\
[1:a]adelay=400|400[v1];[2:a]adelay=3500|3500[v2];[3:a]adelay=6500|6500[v3];\
[4:a]adelay=9400|9400[v4];[5:a]adelay=11800|11800[v5];\
[6:a]volume=0.32[b];[v1][v2][v3][v4][v5][b]amix=inputs=6:duration=longest:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest 최종.mp4
```
(adelay 값 = 각 자막 start × 1000ms. spec이 바뀌면 같이 바꿀 것.
`duration=first`는 첫 음성이 끝나는 순간 오디오가 잘리므로 쓰지 말 것 — `longest` + `-shortest` 조합이 맞다)

기본 목소리 `ko-KR-InJoonNeural`(차분한 남성), 속도 `-8%`. 사용자가 원하면 변경.

**실패하면 (타임아웃/403) — 조용히 BGM만으로 진행한다.** 매번 사용자에게
TTS 안 된다고 반복해 알리지 말 것. 사용자가 음성을 원할 때만: 환경 설정
Network access → Custom에 `speech.platform.bing.com` 추가(새 세션부터 적용)를
안내하거나, 카스 PC에서 `scripts/make_voice.py`를 돌려 mp3를 받는다.
(참고: `hyperframes tts`의 Kokoro 모델은 한국어 미지원이라 대안이 못 된다)

## 하지 말 것

- 결말을 자막으로 공개하기 (티저의 존재 이유가 사라짐)
- 15초 초과 (쇼츠 훅으로서의 기능 상실)
- 스냅샷 확인 없이 렌더링 (3~5분을 날린다)
- `pandoc` 사용 (이 환경에 없음)
