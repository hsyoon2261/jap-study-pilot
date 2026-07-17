# -*- coding: utf-8 -*-
"""CI 자동배포 확인: 최근 빌드 + 라이브 주소에 새 문구 반영됐는지."""
import sys
from browser_core import attach_chrome, snap

ACCT = "6ee81334fcdc1f3c171044e8ad914f28"
DEPLOY = f"https://dash.cloudflare.com/{ACCT}/workers/services/view/jap-study-pilot/production/deployments"
LIVE = "https://jap-study-pilot.szpdkss3.workers.dev/"

with attach_chrome() as (browser, ctx):
    page = next((p for p in ctx.pages if "cloudflare" in p.url or "workers.dev" in p.url), None) or ctx.new_page()
    page.bring_to_front()
    # 1) 배포 페이지 최근 빌드
    page.goto(DEPLOY, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    body = page.inner_text("body")
    print("--- 최근 빌드 관련 ---")
    for ln in body.split("\n"):
        if any(k in ln for k in ("CI 테스트", "남은 개수", "ago", "Building", "Deploying", "Queued", "Success", "failed")):
            s = ln.strip()
            if s and len(s) < 90:
                print(" ", s)
    snap(page, "cf_ci_builds")
    # 2) 라이브 주소에 새 문구 반영?
    page.goto(LIVE, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(6000)
    live = page.inner_text("body")
    changed = "개 남음" in live
    print("\n라이브에 '개 남음' 반영:", changed)
