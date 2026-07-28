# 🎬 HyperFrames 설치 가이드 (윈도우 / 비개발자용)

HyperFrames는 **HTML/CSS로 영상(MP4)을 만드는** 오픈소스 도구입니다.
앞서 설치한 `/watch`가 "영상을 보는 능력"이라면, 이건 **"영상을 만드는 능력"**입니다.

제품 소개 영상, 자막 영상, 슬라이드쇼, 데이터 차트 애니메이션 같은 걸 Claude에게 말로 시켜서 만들 수 있습니다.

---

## 설치 전 준비물

| 필요한 것 | 확인 방법 | 없을 때 |
|---|---|---|
| **Node.js 22 이상** | cmd에서 `node -v` → `v22.x` 이상 | https://nodejs.org 에서 LTS 설치 |
| **FFmpeg** | cmd에서 `ffmpeg -version` | 아래 명령어로 설치 |

FFmpeg 설치 (명령 프롬프트에서):
```
winget install Gyan.FFmpeg
```
설치 후 **명령 프롬프트를 껐다가 다시 켜야** 인식됩니다.

> 💡 FFmpeg는 실제로 영상을 뽑아낼 때(렌더링) 필요합니다. 스킬 설치 자체는 없어도 되지만,
> 영상을 만들려면 반드시 있어야 합니다.

---

## 설치 (딱 한 줄)

명령 프롬프트를 열고 아래 한 줄만 입력하세요. 폴더는 어디서 실행하든 상관없습니다.

```
npx hyperframes skills update
```

처음 실행하면 패키지를 내려받느라 몇 분 걸릴 수 있습니다.
`Installed 8 skills` 라고 나오면 성공입니다.

### 설치되는 것 (핵심 스킬 8개)

| 스킬 | 역할 |
|---|---|
| `hyperframes` | **라우터** — "영상 만들어줘" 요청을 받아 알맞은 작업 흐름을 고름 |
| `hyperframes-core` | 영상 구성의 기본 문법 |
| `hyperframes-animation` | 애니메이션 처리 |
| `hyperframes-keyframes` | 키프레임(장면 전환 시점) 제어 |
| `hyperframes-cli` | 미리보기·렌더링 명령 실행 |
| `hyperframes-creative` | 디자인·연출 가이드 |
| `hyperframes-registry` | 재사용 가능한 블록 목록 |
| `media-use` | 이미지·영상·음악 소재 다루기 |

나머지 11개 워크플로우(제품 출시 영상, PR 영상, 슬라이드쇼, 음악 영상 등)는
**필요할 때 라우터가 알아서 자동으로 받아옵니다.** 미리 설치할 필요 없습니다.

설치 위치는 `C:\Users\사용자이름\.claude\skills\` 이며,
**모든 프로젝트에서** 사용할 수 있습니다.

---

## 사용법

설치 후 Claude에게 이렇게 말하면 됩니다:

```
/hyperframes 로 10초짜리 제품 소개 영상 만들어줘.
제목이 페이드인으로 나타나고, 배경 영상이 깔리고, 잔잔한 배경음악이 있으면 좋겠어.
```

또는 그냥 평범하게 말해도 됩니다:

> "신정승무 안전앱 소개하는 15초 홍보 영상 만들어줘"

Claude가 영상을 구성하고 → HTML로 작성하고 → 미리보기를 만들고 → MP4로 뽑아줍니다.

### 직접 명령어로 쓰고 싶을 때

```
npx hyperframes init 내영상       (새 영상 프로젝트 만들기)
cd 내영상
npx hyperframes preview          (브라우저에서 미리보기)
npx hyperframes render           (MP4로 뽑기)
```

---

## 나중에 최신으로 업데이트

```
npx hyperframes skills update
```

설치할 때와 같은 명령어입니다. 이미 있는 건 최신으로 갱신되고,
설치 안 한 워크플로우를 몰래 추가로 받아오지는 않습니다.

---

## 자주 나는 문제

| 증상 | 해결법 |
|---|---|
| `'npx'은(는) 내부 또는 외부 명령...` | Node.js가 설치 안 됨 → nodejs.org에서 LTS 설치 |
| `Node.js 22+ required` | Node 버전이 낮음 → nodejs.org에서 최신 LTS로 재설치 |
| 렌더링 중 `ffmpeg not found` | `winget install Gyan.FFmpeg` 실행 후 cmd 재시작 |
| 설치는 됐는데 Claude가 스킬을 못 찾음 | Claude Code를 껐다 켜기 |

---

## 참고

- 공식 문서: https://hyperframes.heygen.com/introduction
- 예제 모음: https://hyperframes.heygen.com/showcase
- 라이선스: Apache 2.0 (무료, 상업적 이용 가능)
