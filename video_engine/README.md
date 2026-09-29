# 🎬 video_engine — 공용 편집 엔진

여러 유튜브 채널이 **같이 쓰는 영상 조립 엔진**입니다.
에피소드 설계도(매니페스트 YAML) 한 장을 주면 → **본편 mp4 + 자막 srt**, 원하는 구간의 **쇼츠(9:16) mp4**가 나옵니다.

- 첫 사용처: 매일 올리는 숏폼 코미디 드라마 **「부아콤(옆집 부산아재)」** → 프리셋 `buakom`
- 조용한 채널(예수님말씀 · 임사체험 · 한밤야담) → 프리셋 `calm` (효과 최소, 부드러운 페이드, 느린 켄번즈)
- 효과는 전부 **플러그인 함수**라서, 새 효과는 파일 하나에 함수 하나로 추가됩니다.

---

## 1. 설치 (윈도우 PC, 한 번만)

1. **Python 3.11** — https://www.python.org/downloads/ (설치 첫 화면에서 "Add python.exe to PATH" 체크)
2. **ffmpeg** — PowerShell에서
   ```powershell
   winget install Gyan.FFmpeg
   ```
   설치 후 새 PowerShell 창에서 `ffmpeg -version` 이 나오면 성공.
   (winget이 안 되면 https://www.gyan.dev/ffmpeg/builds/ 에서 받아 압축을 풀고, `config.yaml`의 `engine.ffmpeg`에 `ffmpeg.exe` 경로를 적어도 됩니다.)
3. **파이썬 부품** — 이 저장소 폴더(`yadam-studio`)에서
   ```powershell
   pip install -r video_engine/requirements.txt
   ```
4. **폰트** (없으면 맑은 고딕으로 자동 대체되지만, 설치 권장)
   - 자막: [Pretendard](https://github.com/orioncactus/pretendard/releases) — `Pretendard-Bold/Regular/Black` 설치
   - 속마음 손글씨: 나눔손글씨 펜 (`NanumPen.ttf`) 또는 Google Fonts의 *Nanum Pen Script*
   - 폰트 파일은 `C:/Windows/Fonts` 나 사용자 폰트 폴더(`%LOCALAPPDATA%/Microsoft/Windows/Fonts`)에 있으면 자동으로 찾습니다.
5. **내 PC 설정** — `video_engine/config.example.yaml`을 복사해 `config.yaml`로 이름을 바꾸고 필요한 곳만 고칩니다.
   RTX 5080이면 `video.encoder: h264_nvenc` 로 최종 인코딩이 훨씬 빨라집니다.

## 2. 빠른 시작 (데모로 전체 기능 확인)

저장소 폴더(`yadam-studio`)에서:

```powershell
python -m video_engine demo-assets                                   # 가짜 소스(단색 그림, 사인파 음성, BGM) 생성
python -m video_engine check    video_engine/examples/ep_demo.yaml   # 타임라인·경고만 확인 (몇 초)
python -m video_engine snapshot video_engine/examples/ep_demo.yaml   # 컷별 앞·중간·뒤 장면 한 장 (눈검수)
python -m video_engine render   video_engine/examples/ep_demo.yaml   # 본편 mp4 + srt
python -m video_engine shorts   video_engine/examples/ep_demo.yaml --cuts 2-7   # 쇼츠
```

결과물은 `video_engine/examples/out/`에 생깁니다.

| 명령 | 하는 일 |
|---|---|
| `render ep.yaml` | 본편 mp4(H.264 + AAC) + 같은 이름의 srt |
| `shorts ep.yaml --cuts 8-27` | 컷 8~27 → 9:16 쇼츠 mp4 + srt. `--hook "문구"`로 상단 훅 자막 지정 |
| `check ep.yaml` | 렌더 없이 컷 길이·평균 컷 길이·경고 표 |
| `snapshot ep.yaml [--cuts 3-5]` | 초안 화질로 컷을 만들고 장면 모음 jpg (렌더 전 눈검수용) |
| `effects` | 사용 가능한 효과·전환과 기본값 목록 |
| `clean ep.yaml` | 작업 폴더(`_work`) 삭제 |

공통 옵션: `--draft`(절반 해상도·빠른 인코딩 초안), `--config 경로`.

**캐시**: 컷마다 만든 영상은 `_work/` 폴더에 저장되고, 다음 렌더 때 **바뀐 컷만 다시** 만듭니다. 자막 한 줄 고치고 다시 렌더하면 그 컷만 새로 렌더됩니다.

---

## 3. 매니페스트 작성법

```yaml
meta:
  title: "부아콤 12화"
  fps: 30
  size: [1920, 1080]        # 16:9 기본
  preset: buakom            # buakom | calm | presets 폴더의 다른 파일 이름 | yaml 경로
  output: out/부아콤_12.mp4  # 생략하면 out/<파일이름>.mp4
  overrides:                # 이 에피소드만 프리셋 값 바꾸기 (선택)
    subtitle: {size: 70}

bgm:                        # BGM 트랙 (이름 → 파일)
  main:  {file: bgm/코믹_01.wav, volume_db: 0}
  dream: {file: bgm/설렘.wav, volume_db: -2, loop: true}

sfx:                        # (선택) 이 에피소드만 효과음 파일 지정
  dingdong: 'D:/효과음/딩동.wav'

speakers:                   # (선택) 화자 스타일 덮어쓰기
  동철: {keywords: [아따, 뭇나]}

shorts:
  hook_text: "옆집 아재가 새벽에 던진 한마디"

cuts:
  - id: 1
    type: lip                       # lip | vo | insert
    media: clips/c01.mp4            # mp4 또는 png/jpg
    audio: voice/c01.wav            # 선택 (lip mp4 안에 음성이 있으면 생략 가능)
    speaker: 동철
    subtitle: "아따, 새벽부터 와이리 *시끄럽노*?"
    effects:
      - punch_zoom: {at: 0.5}
    sfx:
      - {name: pop, at: 1.2}
    transition: {type: door_wipe, to: "새벽 4시역"}
    bgm_cue: main
```

### 컷 필드

| 필드 | 뜻 |
|---|---|
| `id` | 컷 번호/이름 (쇼츠 `--cuts 8-27`에서 사용) |
| `type` | `lip` 립싱크 영상 / `vo` 속마음(입 다문 정지 그림 + 음성) / `insert` 대사 없는 인서트 |
| `media` | 그림(png·jpg) 또는 영상(mp4). 해상도·프레임레이트가 달라도 자동으로 맞춤 |
| `audio` | 대사 wav/mp3 (선택) |
| `speaker` | 화자 이름 → 프리셋 `speakers:`의 스타일 적용 |
| `subtitle` | 자막. 여러 장이면 리스트 `["첫 줄", "둘째 줄"]` (대사 길이에 글자 수 비율로 나눔) |
| `effects` | 효과 목록 (아래) |
| `sfx` | `{name, at, gain_db}` — `at`은 컷 시작 기준 초 |
| `transition` | 이전 컷 → 이 컷 전환 (`cut`, `fade`, `dip`, `door_wipe`) |
| `bgm_cue` | 이 컷에서 BGM 바꾸기: 트랙 이름 / `stop` / `fade_out` / `{track, at, fade_in, offset, volume_db}` |
| `duration` | 컷 길이 강제 (없으면 대사·영상 길이로 자동) |
| `focus` | 얼굴 위치 `[가로, 세로]` 0~1 (급줌이 여기로 들어감, 기본은 프리셋 `camera.focus`) |
| `emphasis` | 자막에서 노랗게 칠할 단어 목록 |
| `no_auto` | 자동 효과 빼기, 예: `[vo_cloud]` |
| `lead` / `tail` | 대사 앞/뒤 여백(초) 직접 지정 |

### 자막 표기

- `*강조*` → 노랑 · `[사투리]` → 주황 · 화자 `keywords`에 있는 단어는 자동 주황
- 속마음(`vo`) 컷은 buakom에서 자동으로 **구름 말풍선 + 손글씨 + 하늘색**
- 줄바꿈은 YAML에서 `"첫 줄\n둘째 줄"`, 길면 자동 줄바꿈(`subtitle.max_chars`)

### 효과 적는 법 (3가지 모두 가능)

```yaml
effects:
  - fantasy                               # 이름만 (기본값)
  - punch_zoom: {at: 0.5, scale: 1.4}     # 이름: {파라미터}
  - dialect_note: "뭇나 = 먹었나"          # 이름: 대표값 하나
```

파라미터 우선순위: **효과 기본값 < 프리셋 `effects.<이름>` < 매니페스트**.

---

## 4. 효과 목록 (buakom 기본값)

| # | 이름 | 하는 일 | 예시 |
|---|---|---|---|
| 1 | `kenburns` | 정지 그림 천천히 줌인/아웃(컷마다 번갈아). buakom은 3초마다 화각을 바꿔 **3초 넘게 멈춰 있지 않음**. 정지 그림 컷에 자동 적용 | `- kenburns: {zoom: 0.15, direction: in}` |
| 2 | `punch_zoom` | 얼굴 쪽 1.3배 급줌(0.08초) + 0.3초 화면 흔들림 + "휙" | `- punch_zoom: {at: 0.5}` |
| 3 | `vo_cloud` | 속마음: 가장자리 비네팅 + 구름 말풍선 자막(손글씨, 하늘색). `vo` 컷 자동 | (자동) / `no_auto: [vo_cloud]`로 끄기 |
| 4 | `fantasy` | 핑크 필터 + 가장자리 분홍 빛 + 반짝이 파티클 + 심장박동 | `- fantasy: {at: 0.3, dur: 2}` |
| 5 | `dialect_note` | 사투리 자막 아래 작은 주석 | `- dialect_note: "뭇나 = 먹었나"` → `(*뭇나 = 먹었나)` |
| 6 | `freeze_sticker` | 화면 정지(채도 다운 + 번쩍 + 찰칵) + 굵은 스티커 자막 | `- freeze_sticker: "배동철, 47세.\n오해 중."` |
| 7 | `orom_sil` | 한 팔 번쩍! 슬로모션(2.5배) + 번쩍 플래시 + 회전하는 방사형 빛 + 징글 | `- orom_sil: {at: 0.35}` |
| 8 | `assa_gaori` | "뽁" + 가오리 스티커가 화면을 오른쪽→왼쪽으로 헤엄쳐 지나감 (PNG 없으면 코드로 그린 실루엣) | `- assa_gaori: {sprite: 스티커/가오리.png}` |
| 9 | `wall_voice` | 벽 너머 대사: 로우패스/하이패스 + 짧은 울림, 자막 회색 | `- wall_voice` |
| 10 | 전환 `door_wipe` | 전동차 문이 양쪽에서 닫힘 + "딩동" → 노선도식 역 카드(●새벽 4시역 → ●오후 2시역) → 문 열림 | `transition: {type: door_wipe, to: "오후 2시역"}` (`from`은 직전 역 자동) |
| 11 | `brake_scratch` | 레코드 스크래치 + BGM이 턴테이블 멈추듯 느려지며 뚝 끊김 (다음 `bgm_cue`까지 무음) | `- brake_scratch: {at: 0.0}` |
| 12 | 자막 스타일 | 큰 흰 글씨 + 검은 테두리, 강조 노랑, 사투리 주황, 속마음 하늘색. 화자별은 `speakers:` | 프리셋 `subtitle:`, `speakers:` |

그 밖의 전환: `cut`(그냥 붙이기), `fade`(크로스페이드, calm 기본), `dip`(검정으로 페이드).
`python -m video_engine effects` 로 모든 파라미터 기본값을 볼 수 있습니다.

### 프리셋에서 켜고 끄기

```yaml
# presets/buakom.yaml
effects:
  fantasy: {enabled: false}      # 끄면 매니페스트에 적혀 있어도 건너뜀 (check에 안내 표시)
auto_effects:
  still: [kenburns]              # 정지 그림 컷 전부
  vo: [vo_cloud]                 # 속마음 컷 전부
```

`calm` 프리셋은 개그 효과가 전부 꺼져 있고, 느린 켄번즈(5%, 부드러운 가속), 0.8초 크로스페이드,
차분한 하단 자막(페이드 인/아웃, 그림자)이 기본입니다. **같은 매니페스트를 `preset: calm`으로 바꾸기만 해도** 조용한 버전이 나옵니다.

---

## 5. 오디오 (예전에 겪은 문제 대응)

흐름: 대사 버스 / BGM 버스 / 효과음 버스(모두 float WAV) → **대사 loudnorm(-14 LUFS, 2패스 선형)** → BGM·효과음 덕킹 → 합치기 → **리미터(-1.5 dBTP, 192kHz 오버샘플)** → 최종 mux에서 **AAC 딱 한 번 인코딩**.

- **(a) AAC 두 번 인코딩으로 true peak 0dBFS 초과** → 중간 결과는 전부 무손실 WAV, AAC는 마지막 mux 한 번뿐. 리미터는 loudnorm **뒤**. 완성 후 실제 true peak를 측정해 -0.5 dBTP를 넘으면 리미터 천장을 낮춰 **오디오만** 다시 인코딩(영상은 복사)합니다.
- **(b) sidechaincompress가 대사 끝나는 순간 BGM을 잘라먹음** → 대사를 `asplit` 해서 **키(key) 쪽에만 `apad`**. 출력 길이는 BGM 쪽이 결정합니다. (`tests/test_render.py`의 `test_sidechain_does_not_cut_bgm_after_dialogue`가 확인)
- BGM은 트랙마다 라우드니스를 재서 `audio.bgm_lufs`(buakom -27)에 맞춘 뒤, 대사가 나오면 자동으로 눌립니다(`audio.duck`).
- 효과음은 피크 -8 dBFS 기준 + 대사에 약하게 덕킹(`audio.sfx_duck`) → 대사를 가리지 않음.
- 렌더가 끝나면 `완성: ... -14.x LUFS, true peak -x.x dBTP` 가 표시됩니다.

## 6. 쇼츠

`python -m video_engine shorts ep.yaml --cuts 8-27 --hook "상단 훅 문구"`

- 컷 8~27을 **다시 조립**합니다 (본편을 잘라내는 게 아님) → 자막·스티커·말풍선이 세로 화면에 맞는 크기/위치로 새로 배치
- 장면은 16:9로 찍은 뒤 **가운데 9:16 크롭** (인물이 화면 중앙에 있다는 전제)
- **상단 훅 자막**: 처음 1초 (`shorts.hook_hold`, `all`이면 끝까지)
- **루프 처리**: 앞 0.4초를 떼어 끝에 크로스페이드로 겹침 → 유튜브에서 반복 재생될 때 끝이 처음으로 자연스럽게 이어짐 (영상·소리 모두)
- 구간 시작 시점에 흐르던 BGM을 이어서 틀어줌

---

## 7. 새 효과 추가하기 (플러그인)

`video_engine/effects/` 폴더에 파일을 하나 만들고 함수 하나만 쓰면 자동 등록됩니다.

```python
# video_engine/effects/my_effects.py
from ..util import fnum
from .registry import effect

@effect("glitch", defaults={"at": 0.0, "dur": 0.25, "sfx": "whoosh"}, primary="at")
def glitch(plan, p):
    """화면이 지직거림."""
    en = plan.enable(p["at"], p["at"] + p["dur"])
    plan.post.append(f"noise=alls=60:allf=t:enable='{en}'")   # ffmpeg 필터 한 줄
    plan.add_sfx(p["sfx"], p["at"])
```

`plan`(컷 계획서)에 쓸 수 있는 것:

| API | 용도 |
|---|---|
| `plan.add_zoom(식, 최대값)` / `plan.add_pan(x식, y식)` | 카메라 줌·이동 (시간 변수 `t`) |
| `plan.post.append("ffmpeg 필터")` | 색/화면 필터 |
| `plan.add_layer(png, x식, y식, 시작, 끝, filters=[...], z=...)` | 그림 오버레이 (자막 60, 스티커 70, 전환 90) |
| `plan.add_sfx(이름, 초)` | 효과음 |
| `plan.audio_filters.append("lowpass=f=800")` | 이 컷 대사에 오디오 필터 |
| `plan.bgm_events.append({...})` | BGM 제어 |
| `plan.subtitle["style"]`, `["notes"]`, `["kind"]` | 자막 스타일 바꾸기 |
| `timing=함수` + `plan.add_warp("freeze"/"slow", ...)` | 컷 길이를 바꾸는 효과 (정지, 슬로모션) |
| `plan.canvas`, `plan.unit`, `plan.vertical` | 화면 크기, 1080p 대비 배율, 쇼츠 여부 |

전환은 `video_engine/transitions.py`에 `@transition("이름")` + `def 이름(prev, cur, p)`.
효과가 ffmpeg 없이 계획서만 바꾸기 때문에 단위 테스트가 쉽습니다 (`tests/test_effects.py` 참고).

테스트 실행: `python -m pytest video_engine/tests -q` (ffmpeg가 없으면 렌더 테스트는 자동 건너뜀)

---

## 8. 윈도우 경로 주의점

- YAML 안의 경로는 **슬래시(`/`)** 로 쓰는 게 제일 안전합니다: `media: D:/부아콤/12화/c01.png`
- 역슬래시를 쓰려면 **작은따옴표**로: `media: 'D:\부아콤\12화\c01.png'`
  큰따옴표(`"D:\부아콤\..."`)는 YAML이 `\부`… 를 특수문자로 해석해 오류가 납니다.
- 상대경로는 **매니페스트 파일이 있는 폴더 기준**입니다. 에피소드 폴더에 `ep.yaml`과 소스를 같이 두면 편합니다.
- 한글 폴더·파일 이름, 띄어쓰기 모두 괜찮습니다 (ffmpeg에 경로를 필터 문자열이 아닌 입력으로만 넘기기 때문).
- `%USERPROFILE%`, `~` 같은 환경변수 경로도 됩니다.
- PowerShell에서 한글이 깨지면: `chcp 65001` 후 다시 실행.
- 경로가 너무 길면(260자) 윈도우가 거부할 수 있으니 `D:/부아콤/12화/` 처럼 짧은 폴더를 권장합니다.
- 작업 폴더 `_work/`는 용량을 먹습니다(컷 캐시). 에피소드를 올린 뒤 `clean` 명령으로 지우세요.

---

## 9. 가정한 것들 (막힌 부분은 이렇게 정했습니다)

1. **자막은 PNG로 그려 올림** — ffmpeg `subtitles`(libass) 대신 Pillow로 그린 그림을 오버레이. 윈도우에서 폰트 폴더/경로 이스케이프(`C\:`) 문제를 원천 차단하고, 단어별 색·구름 말풍선·스티커를 한 방식으로 처리하기 위함. srt 파일은 따로 만들어 유튜브 자막용으로 씁니다.
2. **"대사 기준 -14 LUFS"** = 대사만 모은 버스를 -14 LUFS로 맞춤(2패스 loudnorm, 선형). BGM·효과음이 더해져 전체는 -14 근처가 됩니다. 전체 믹스 기준이 필요하면 `audio.normalize: program`.
3. **립싱크 컷의 음성**은 영상 0초에 맞물려 있다고 가정 (`lead` 0). `audio`가 없으면 mp4 안의 음성을 씀.
4. **정지/슬로모션(freeze_sticker, orom_sil)은 영상만** 늘리고 대사는 늘리지 않습니다. 그래서 기본값은 대사가 끝난 뒤 정지(`at: end`)이고, `orom_sil`은 대사 없는 동작 순간에 쓰는 것을 전제로 했습니다.
5. **effects/sfx의 `at`** 은 컷 시작 기준 초(효과로 늘어난 뒤의 시간).
6. **transition은 "이전 컷 → 이 컷"** 으로 들어오는 방식. `door_wipe`는 문이 닫히는 시간만큼 앞 컷 끝, 열리는 시간만큼 이 컷 앞에 여백을 자동으로 더해서 대사가 문에 가려지지 않게 합니다.
7. **쇼츠는 가운데 크롭** (인물이 중앙). 인물이 한쪽에 있는 컷은 `focus: [0.3, 0.4]`로 조정.
8. **효과음·가오리 스티커가 없으면** 엔진이 코드로 만든 임시 소리/그림을 씀 → 나중에 config에 파일만 적으면 교체.
9. **최종 영상 인코딩은 한 번 더** 합니다(컷별 중간 파일 → 최종). 중간 파일은 CRF 12의 고화질이라 차이는 거의 없고, 대신 컷 캐시·병렬 렌더가 가능합니다. 오디오는 한 번만 인코딩.
10. 켄번즈는 ffmpeg `zoompan`으로 하고, 정지 그림은 2배 크게 준비해 느린 줌에서도 떨림을 줄였습니다(`camera.supersample`).

## 10. 문제 해결

| 증상 | 해결 |
|---|---|
| `ffmpeg를 찾을 수 없습니다` | `config.yaml`에 `engine: {ffmpeg: 'C:/ffmpeg/bin/ffmpeg.exe'}` |
| `없는 파일이 있습니다` | 목록에 나온 경로 확인 (상대경로는 매니페스트 폴더 기준) |
| `모르는 효과 'xxx'` | 철자 확인, `python -m video_engine effects`로 목록 보기 |
| 손글씨체가 아니라 고딕으로 나옴 | 손글씨 폰트 설치 또는 `fonts.handwriting` 경로 지정 |
| 렌더가 느림 | `--draft`로 확인 → 최종만 원래 화질, `video.encoder: h264_nvenc`, `engine.jobs` 조정 |
| 자세한 오류 | 환경변수 `VIDEO_ENGINE_VERBOSE=1` 로 실행하면 ffmpeg 명령까지 표시 |

## 폴더 구조

```
video_engine/
  cli.py            명령줄 (render/shorts/check/snapshot/effects/demo-assets/clean)
  pipeline.py       전체 흐름 (컷 렌더 → 오디오 → 합치기 → 측정)
  manifest.py       매니페스트 읽기/검증, 쇼츠 구간 선택
  config.py         설정 병합 (기본값 < 프리셋 < config.yaml < 매니페스트), 폰트 찾기
  timeline.py       컷 길이·시작 시각 계산, 효과/전환 적용 순서
  plan.py           컷 계획서(CutPlan) — 효과가 적는 곳
  effects/          효과 플러그인 (camera, looks, text_fx, comedy) + registry
  transitions.py    전환 플러그인 (cut, fade, dip, door_wipe)
  subtitles.py      자막 스타일/PNG/srt
  graphics/         Pillow 그림 (글자, 구름, 스티커, 역 카드, 전동차 문, 가오리, 빛살, 반짝이)
  render/           ffmpeg 명령 조립 (segment: 컷, audio: 믹스)
  sfx_synth.py      임시 효과음 합성
  demo_assets.py    가짜 테스트 소스
  presets/          buakom.yaml, calm.yaml
  examples/         ep_demo.yaml (부아콤 1화 앞부분 흉내 10컷)
  tests/            pytest
```
