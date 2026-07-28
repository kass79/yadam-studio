---
name: publish_to_threads
description: 생성된 마크다운 텍스트 초안을 로컬 크롬 디버깅 포트와 연동하여 Threads 웹 UI 상에서 자동으로 게시하거나 예약하는 스킬입니다.
---

# 🚀 쓰레드 자동 포스팅 스킬 (publish_to_threads)

이 스킬은 백그라운드 API 호출의 한계(예약 미노출, 컨테이너 만료 등)를 극복하기 위해, **Playwright**를 활용하여 로컬에서 실행 중인 Chrome 브라우저(포트 9222)에 직접 연결해 Threads 웹 UI(`https://www.threads.net/`)를 사람처럼 제어하여 포스팅(또는 예약)을 완벽하게 수행하는 워크플로우입니다.

---

## 1. 사용 도구 및 요구사항 (Requirements)
* **Python 스크립트**: `.agents/skills/publish_to_threads/scripts/web_publish.py`
* **Python 패키지**: `playwright` (설치: `python3 -m pip install playwright && playwright install chromium`)
* **선행 구동**: `setup.py` 스크립트를 통해 `--remote-debugging-port=9222` 옵션으로 크롬 브라우저가 사전에 열려 있어야 하며, 사용자가 Threads에 미리 로그인해 두어야 합니다.

---

## 2. 사용법 및 파라미터 (Usage)

터미널에서 Python을 이용해 아래와 같은 인자(Arguments)를 주어 실행합니다.

### [즉시 발행 (Immediate Publishing)]
추출된 마크다운 초안 파일(텍스트)과 이미지 파일을 지정하여 대기 없이 웹 UI에서 즉시 '게시(Post)'를 누릅니다.
```bash
python3 .agents/skills/publish_to_threads/scripts/web_publish.py \
  --text-file "output/260529_0830/260529_twitter_1.md" \
  --image-file "output/260529_0830/260529_twitter_1.png"
```

### [네이티브 UI 예약 발행 (Scheduled Publishing)]
`--schedule` 파라미터를 추가하면, Threads 웹 UI에 있는 **시계 아이콘(예약)**을 직접 클릭하여 달력을 띄우고 전달받은 시간(YYYY-MM-DD HH:MM)으로 정확하게 세팅한 뒤 예약(Schedule) 버튼을 클릭합니다.
```bash
# 2026년 6월 1일 오후 3시 30분 예약 예시
python3 .agents/skills/publish_to_threads/scripts/web_publish.py \
  --text-file "output/260529_0830/260529_twitter_2.md" \
  --image-file "output/260529_0830/260529_twitter_2.png" \
  --schedule "2026-06-01 15:30"
```

---

## 3. 핵심 자동화 로직 (Playwright Workflow)

1. **디버깅 포트 연결**: `playwright.chromium.connect_over_cdp`를 통해 기존 열려 있는 브라우저의 탭(Context)을 그대로 활용하여 로그인 세션을 유지합니다.
2. **작성창 제어**: Threads 메인 페이지로 이동한 뒤, 텍스트 입력 영역(`contenteditable`)에 초안을 타이핑하고, 숨겨진 `<input type="file">`에 로컬 이미지 경로를 주입합니다.
3. **달력/시간 제어 (DatePicker)**: 예약 인자가 존재할 시, `aria-label` 등 웹 표준 속성을 활용해 달력 팝업을 열고, 목표 날짜까지 월(Month)을 넘긴 후 일(Day)을 클릭합니다. 시간(Hour, Min, AM/PM)은 `Tab` 키 포커스 이동을 통해 정확하게 타이핑합니다.
4. **종료**: UI 토스트 메시지가 완료됨을 알리면 새롭게 열었던 탭을 닫고 깔끔하게 스크립트를 종료합니다.

> **💡 장점**: Threads 앱 내에서 진짜 예약 큐(Queue)에 등록되기 때문에, 언제든 모바일 앱을 켜서 예약 내역을 직접 확인하고 수정하거나 취소할 수 있습니다.
