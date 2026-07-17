# -*- coding: utf-8 -*-
"""라이브 주소가 앱을 제대로 띄우는지 확인."""
from browser_core import attach_chrome, snap

LIVE = "https://jap-study-pilot.szpdkss3.workers.dev/"

with attach_chrome() as (browser, ctx):
    page = next((p for p in ctx.pages if "cloudflare" in p.url), None) or ctx.new_page()
    page.bring_to_front()
    page.goto(LIVE, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(6000)  # onMount 콘텐츠 로드 대기
    print("URL:", page.url)
    print("제목:", page.title())
    snap(page, "cf_live")
    body = page.inner_text("body")
    for kw in ("일본어 학습", "오늘의 세트", "덱", "Day 2", "가나"):
        print(f"  '{kw}' 있음:", kw in body)
