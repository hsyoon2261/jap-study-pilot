# -*- coding: utf-8 -*-
"""계정 서브도메인 변경 위치 찾기."""
from browser_core import attach_chrome, snap

ACCT = "6ee81334fcdc1f3c171044e8ad914f28"
URL = f"https://dash.cloudflare.com/{ACCT}/workers-and-pages"

with attach_chrome() as (browser, ctx):
    page = next((p for p in ctx.pages if "cloudflare" in p.url), None) or ctx.new_page()
    page.bring_to_front()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    print("URL:", page.url)
    # "Subdomain" 근처 요소 찾기
    body = page.inner_text("body")
    print("서브도메인 표시 있음:", "workers.dev" in body, "/ Subdomain 텍스트:", "Subdomain" in body)
    snap(page, "cf_sub", full=True)
