import os
import re
import time
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
NOTICE_URL = "https://www.gersang.co.kr/news/notice.gs?GSbid=1001"
LAST_TITLE_FILE = Path("last_title.txt")


def now_kst():
    return time.strftime("%Y-%m-%d %H:%M", time.localtime())


def normalize_title(title: str) -> str:
    title = re.sub(r"^\(수정\)\s*", "", title or "")
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def load_last_title():
    if LAST_TITLE_FILE.exists():
        try:
            return LAST_TITLE_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""


def save_last_title(title: str):
    LAST_TITLE_FILE.write_text(title, encoding="utf-8")


def fetch_top_notice_title():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NOTICE_URL, timeout=60000, wait_until="domcontentloaded")

        title_el = page.query_selector("div.list-tb div.tr:nth-of-type(2) div.td.box-subject p")
        if not title_el:
            browser.close()
            raise RuntimeError("상단 공지 제목을 찾지 못했습니다.")

        raw_title = title_el.inner_text().strip()
        browser.close()

    return normalize_title(raw_title)


def send_notice_alert(notice_title: str):
    embed = {
        "title": "📢 거상 새 공지",
        "url": NOTICE_URL,
        "description": notice_title,
        "color": 0x2B6CFF,
        "footer": {
            "text": f"확인 시각: {now_kst()}"
        }
    }

    r = requests.post(
        WEBHOOK_URL + "?wait=true",
        json={"embeds": [embed]},
        timeout=20
    )
    r.raise_for_status()
    print(f"✅ 디스코드 전송 완료: {notice_title}")


def main():
    current_title = fetch_top_notice_title()
    saved_title = load_last_title()

    print(f"현재 상단 공지: {current_title}")
    print(f"저장된 제목: {saved_title if saved_title else '(없음)'}")

    # 최초 실행 시 저장만 하고 종료
    if not saved_title:
        save_last_title(current_title)
        print("ℹ 최초 실행: 현재 상단 공지 저장만 함")
        return

    if current_title != saved_title:
        print("🆕 새 공지 감지")
        send_notice_alert(current_title)
        save_last_title(current_title)
    else:
        print("변경 없음")


if __name__ == "__main__":
    main()
