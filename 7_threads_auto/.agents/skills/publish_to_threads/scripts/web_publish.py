import argparse
import sys
import os
import time
import random
import platform
import subprocess
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError

IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

# ───────────────────────────────────────────────
# 🧑 사람처럼 행동하기 위한 헬퍼 함수
# ───────────────────────────────────────────────
def human_delay(min_sec=0.8, max_sec=2.2):
    """랜덤 딜레이 - 사람이 잠깐 생각하는 것처럼 자연스럽게"""
    delay = random.uniform(min_sec, max_sec)
    print(f"   ⏸  ({delay:.1f}초 자연 대기...)")
    time.sleep(delay)

def clipboard_paste(page, text):
    """클립보드에 텍스트 복사 후 붙여넣기 — 맥(pbcopy+Cmd+V) / 윈도우(clip+Ctrl+V) 모두 지원"""
    if IS_MAC:
        subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        page.keyboard.press('Meta+v')
    elif IS_WINDOWS:
        # clip.exe는 UTF-16(BOM 포함)으로 넣어야 한글이 깨지지 않음
        subprocess.run('clip', input=text.encode('utf-16'), check=True)
        page.keyboard.press('Control+v')
    else:
        # 리눅스 등: 클립보드 도구 없이 에디터에 직접 입력
        page.keyboard.insert_text(text)

def human_click(locator, page=None):
    """클릭 직전 짧은 망설임 후 클릭"""
    time.sleep(random.uniform(0.3, 0.8))
    locator.click(force=True)

def run(text_file, image_file, schedule_str):
    with open(text_file, 'r', encoding='utf-8') as f:
        text_content = f.read()

    with sync_playwright() as p:
        print("🔌 Chrome 디버깅 포트(9222)에 연결 중...")
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"❌ 연결 실패! setup.py로 크롬이 실행되어 있는지 확인하세요: {e}")
            sys.exit(1)

        contexts = browser.contexts
        context = contexts[0] if contexts else browser.new_context()
        page = context.new_page()

        try:
            print("🌐 Threads 홈페이지로 이동 중...")
            page.goto("https://www.threads.net/")
            page.wait_for_load_state("networkidle")
            human_delay(2.5, 4.0)  # 페이지 로드 후 충분히 대기

            print("📝 작성(Create) 창 여는 중...")
            create_btn = page.locator('div[role="button"]:has-text("새로운 스레드"), button:has-text("새로운 스레드"), div[role="navigation"] a[href*="write"]').first
            try:
                create_btn.wait_for(state="visible", timeout=5000)
            except Exception:
                pass
            human_delay(0.5, 1.2)  # 버튼 발견 후 잠깐 망설임
            human_click(create_btn)
            human_delay(2.0, 3.5)  # 다이얼로그 열림 대기

            # 작성 다이얼로그 캡처 (가장 중요: 모든 내부 컴포넌트 조작은 이 안에서만 수행)
            print("🔒 작성 다이얼로그(div[role='dialog']) 대기 및 캡처...")
            dialog = page.locator('div[role="dialog"]').first
            dialog.wait_for(state="visible", timeout=8000)

            print("✍️ 텍스트 입력 중 (사람처럼 타이핑)...")
            editor = dialog.locator('div[contenteditable="true"]').first
            human_delay(0.6, 1.3)  # 에디터 발견 후 잠깐
            editor.click()
            human_delay(0.3, 0.7)  # 포커스 후 잠깐
            clipboard_paste(page, text_content)  # 클립보드 복붙 (빠르고 자연스러움)
            human_delay(0.8, 1.5)  # 붙여넣기 후 잠깐 검토

            if image_file:
                print(f"🖼️ 이미지 첨부 중... ({image_file})")
                abs_path = os.path.abspath(image_file)
                if not os.path.exists(abs_path):
                    print(f"❌ 이미지 파일을 찾을 수 없습니다: {abs_path}")
                    sys.exit(1)
                
                file_input = dialog.locator('input[type="file"]').first
                file_input.set_input_files(abs_path)
                human_delay(3.0, 5.0)  # 이미지 업로드 완료 대기 (크기에 따라 가변)

            # '커뮤니티 또는 주제' 클릭하여 'AI' 선택
            print("🎯 '커뮤니티 또는 주제' 클릭 및 'AI' 주제 선택 시도...")
            topic_input = dialog.locator('input[placeholder="커뮤니티 또는 주제"], [placeholder="커뮤니티 또는 주제"]').first
            if topic_input.is_visible():
                human_delay(0.8, 1.5)
                human_click(topic_input)
                human_delay(1.5, 2.5)  # 드롭다운 열림 대기
                
                ai_options = page.locator('text="AI"')
                ai_option = None
                for i in range(ai_options.count()):
                    candidate = ai_options.nth(i)
                    if candidate.is_visible():
                        ai_option = candidate
                        break
                
                if ai_option:
                    print("✅ 'AI' 주제 옵션 선택 완료!")
                    human_delay(0.4, 0.9)
                    human_click(ai_option)
                    human_delay(1.0, 2.0)
                else:
                    print("⚠️ 'AI' 주제 옵션을 찾지 못해 계속 진행합니다.")
            else:
                print("⚠️ '커뮤니티 또는 주제' 영역이 없어 계속 진행합니다.")

            if schedule_str:
                print(f"⏰ 예약 세팅 시작 ({schedule_str})...")
                
                # 상대 시간(정수 시간 변수) 처리 고안
                is_relative = False
                delay_hours = 0
                clean_str = schedule_str.strip().lower().replace("+", "").replace("h", "")
                if clean_str.isdigit():
                    is_relative = True
                    delay_hours = int(clean_str)
                
                if is_relative:
                    print(f"🕒 상대적 시간 변수 감지! ({schedule_str}) 브라우저 Javascript로 현재 시간을 질의하여 {delay_hours}시간 뒤로 세팅합니다.")
                    js_time_str = page.evaluate("""() => {
                        const d = new Date();
                        const offset = d.getTimezoneOffset() * 60000;
                        const localISOTime = (new Date(d - offset)).toISOString().slice(0, 19).replace('T', ' ');
                        return localISOTime;
                    }""")
                    print(f"🌐 브라우저 기준 실제 현재 시간: {js_time_str}")
                    current_dt = datetime.strptime(js_time_str, "%Y-%m-%d %H:%M:%S")
                    target_dt = current_dt + timedelta(hours=delay_hours)
                    print(f"🎯 최종 동적 계산된 예약 시간: {target_dt.strftime('%Y-%m-%d %H:%M')}")
                else:
                    target_dt = datetime.strptime(schedule_str, "%Y-%m-%d %H:%M")
                
                # 다이얼로그 내부의 '더 보기'(점 3개) 버튼을 직접 정밀 타겟팅
                more_btn = dialog.locator('div[role="button"]:has-text("더 보기"), [aria-label="더 보기"]').first
                if not more_btn.is_visible():
                    print("❌ '더 보기' 버튼을 찾을 수 없습니다.")
                    sys.exit(1)
                
                # 토글 프루프 메뉴 오픈
                schedule_menu_item = page.locator('div[role="menuitem"]:has-text("예약...")').first
                if not schedule_menu_item.is_visible():
                    human_delay(0.5, 1.0)
                    more_btn.click(force=True)
                    human_delay(1.5, 2.5)  # 메뉴 애니메이션 대기
                    schedule_menu_item = page.locator('div[role="menuitem"]:has-text("예약...")').first
                
                if not schedule_menu_item.is_visible():
                    print("❌ '예약...' 메뉴 아이템을 찾을 수 없습니다.")
                    sys.exit(1)
                
                human_delay(0.4, 0.9)
                human_click(schedule_menu_item)
                human_delay(2.0, 3.0)  # 달력 팝업 열림 대기

                # 날짜/시간 세팅 UI (DatePicker) 제어
                # Threads의 DatePicker는 월(Month)을 넘기는 기능과 일(Day)을 클릭하는 구조입니다.
                target_month_en = target_dt.strftime("%B %Y") # "June 2026"
                target_month_kr = f"{target_dt.year}년 {target_dt.month}월" # "2026년 6월" (%-m은 윈도우 미지원)
                target_day = str(target_dt.day)

                print("📅 달력 열림 확인 — hh/mm 인풋 먼저 체크...")
                hour_input   = page.locator('input[placeholder="hh"]').first
                minute_input = page.locator('input[placeholder="mm"]').first

                # ★ 핵심: 달력이 열리면 오늘 날짜가 이미 선택되어 hh/mm 인풋이 바로 보임
                # 날짜를 또 클릭하면 토글로 선택 해제 → 인풋이 사라지는 버그!
                # → 먼저 인풋이 보이는지 확인 후, 없을 때만 날짜 클릭
                inputs_visible = False
                try:
                    hour_input.wait_for(state="visible", timeout=2500)
                    inputs_visible = True
                    print("✅ hh/mm 인풋 이미 보임! (오늘 날짜 기본 선택) — 날짜 클릭 생략")
                except Exception:
                    print(f"🎯 hh/mm 미표시 — 날짜({target_day}일) 클릭 시도...")

                if not inputs_visible:
                    # 오늘이 아닌 날짜를 목표로 할 때만 날짜 클릭
                    day_btn = page.get_by_role("button", name=target_day, exact=True).first
                    if not day_btn.is_visible():
                        day_btn = page.locator(f'div[role="button"]').get_by_text(target_day, exact=True).first
                    human_delay(0.4, 1.0)
                    day_btn.click(force=True)
                    human_delay(1.5, 2.5)
                    try:
                        hour_input.wait_for(state="visible", timeout=5000)
                        inputs_visible = True
                        print("✅ 날짜 클릭 후 hh/mm 인풋 감지!")
                    except Exception:
                        print("⚠️ 날짜 클릭 후에도 시간 인풋 미표시...")

                print("🕒 시간 설정 — 24시간 형식 입력...")
                # 24시간 형식으로 입력 (Threads UI가 24시간 형식 사용 확인됨)

                hour_24_str = target_dt.strftime("%H")   # "13", "09" 등 24시간
                minute_str  = target_dt.strftime("%M")   # "00"~"59"

                hour_input   = page.locator('input[placeholder="hh"]').first
                minute_input = page.locator('input[placeholder="mm"]').first

                try:
                    hour_input.wait_for(state="visible", timeout=5000)
                    minute_input.wait_for(state="visible", timeout=5000)
                    print(f"✅ hh/mm 인풋 감지! → {hour_24_str}시 {minute_str}분 입력")
                except Exception:
                    print("⚠️ 시간 인풋 로딩 대기 시간 초과, 계속 폴백 시도...")

                if hour_input.is_visible() and minute_input.is_visible():
                    # 시간 인풋 클릭 전 잠깐 망설임
                    human_delay(0.5, 1.0)
                    hour_input.click(click_count=3)
                    human_delay(0.2, 0.5)
                    hour_input.fill(hour_24_str)
                    human_delay(0.4, 0.9)  # 시 입력 후 잠깐

                    minute_input.click(click_count=3)
                    human_delay(0.2, 0.5)
                    minute_input.fill(minute_str)
                    human_delay(0.4, 0.8)  # 분 입력 후 잠깐

                    h_val = hour_input.input_value()
                    m_val = minute_input.input_value()
                    print(f"✅ 입력 확인 — hh: '{h_val}', mm: '{m_val}'")
                else:
                    print("⚠️ hh/mm 인풋창 미표시 — 키보드 탭 폴백 작동...")
                    page.keyboard.press("Tab")
                    page.keyboard.type(hour_24_str)
                    page.keyboard.press("Tab")
                    page.keyboard.type(minute_str)

                # 달력 팝업 내 완료(Done) 버튼 — page 전체 스코프에서 탐색 (Portal 레이어 대응)
                done_btn = page.locator('div[role="button"]:has-text("완료"), div[role="button"]:has-text("Done")').first
                try:
                    done_btn.wait_for(state="visible", timeout=5000)
                except Exception:
                    pass
                if done_btn.is_visible():
                    human_delay(0.5, 1.0)  # 완료 클릭 전 검토하는 척
                    done_btn.click(force=True)
                    print("✅ 완료 버튼 클릭 완료!")
                else:
                    print("⚠️ 완료 버튼 미발견 — 계속 진행")
                print("⏳ 달력 팝업 닫힘 및 예약 버튼 전환 대기 중...")
                human_delay(3.0, 4.5)  # 게시→예약 버튼 전환 충분히 대기

                print("🚀 최종 예약(Schedule) 버튼 클릭...")
                # 완료 후 버튼이 '게시' → '예약'으로 전환됨 — 반드시 '예약' 버튼 클릭
                final_btn = dialog.locator('div[role="button"]:has-text("예약"), button:has-text("예약"), [aria-label="예약"]').first
                if final_btn.is_visible():
                    human_delay(0.5, 1.2)  # 최종 전송 직전 마지막 망설임
                    human_click(final_btn)
                else:
                    print("⚠️ 최종 예약 버튼을 직접 찾지 못해 visible 예약 요소를 순회 탐색합니다.")
                    final_options = dialog.locator('text="예약"')
                    clicked = False
                    for i in range(final_options.count()):
                        btn = final_options.nth(i)
                        if btn.is_visible():
                            human_delay(0.3, 0.8)
                            btn.click(force=True)
                            clicked = True
                            break
                    if not clicked:
                        print("❌ 최종 예약 버튼 클릭 실패")
                        sys.exit(1)
                
            else:
                print("🚀 최종 게시(Post) 버튼 클릭...")
                post_btn = dialog.locator('div[role="button"]:has-text("Post"), div[role="button"]:has-text("게시")').first
                if post_btn.is_visible():
                    human_delay(0.5, 1.2)  # 게시 직전 마지막 망설임
                    human_click(post_btn)
                else:
                    human_delay(0.5, 1.0)
                    dialog.locator('text="게시"').last.click()

            print("⏳ 전송 완료 및 다이얼로그 닫힘 대기 중...")
            dialog.wait_for(state="hidden", timeout=15000)
            print("✅ 다이얼로그가 정상적으로 닫혔습니다! 전송 성공!")
            human_delay(2.5, 4.0)  # 전송 후 피드 정착 대기
            print("✅ 작업 완료! 브라우저 탭을 닫습니다.")
            page.close()

        except Exception as e:
            print(f"❌ 실행 중 에러 발생: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Threads Web UI Publisher via Playwright")
    parser.add_argument("--text-file", required=True, help="Path to the markdown text file")
    parser.add_argument("--image-file", required=False, help="Path to the image file (optional)")
    parser.add_argument("--schedule", required=False, help="Format: YYYY-MM-DD HH:MM (e.g. 2026-06-01 15:30)")
    args = parser.parse_args()
    run(args.text_file, args.image_file, args.schedule)
