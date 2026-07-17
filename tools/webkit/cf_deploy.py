# -*- coding: utf-8 -*-
"""jap-study-pilot 배포 페이지로 이동해 최신 빌드 상태 확인."""
from browser_core import attach_chrome, snap

ACCT = "6ee81334fcdc1f3c171044e8ad914f28"
URL = f"https://dash.cloudflare.com/{ACCT}/workers/services/view/jap-study-pilot/production/deployments"

with attach_chrome() as (browser, ctx):
    page = next((p for p in ctx.pages if "cloudflare" in p.url), None) or ctx.new_page()
    page.bring_to_front()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(5000)
    print("URL:", page.url)
    snap(page, "cf_deploy")
    # 핵심 텍스트만 뽑기
    body = page.inner_text("body")
    keys = [ln.strip() for ln in body.split("\n")
            if any(k in ln for k in ("build", "Build", "deploy", "Deploy", "failed", "Failed",
                                     "Success", "success", "workers.dev", "Retry", "Latest", "Active"))]
    print("\n--- 관련 텍스트 ---")
    for k in keys[:30]:
        print(" ", k[:100])
