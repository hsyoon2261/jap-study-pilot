# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
ACCT="6ee81334fcdc1f3c171044e8ad914f28"
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "cloudflare" in p.url or "koto37" in p.url), None) or ctx.pages[0]
    page.bring_to_front()
    # 1) 최신 빌드 상태
    page.goto(f"https://dash.cloudflare.com/{ACCT}/workers/services/view/jap-study-pilot/production/deployments", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    b=page.inner_text("body")
    for ln in b.split("\n"):
        s=ln.strip()
        if any(k in s for k in ("P2","드릴","Building","Deploying","failed","Failed","Queued","Success")) and len(s)<95:
            print("빌드:", s)
    # 2) 라이브 드릴
    page.goto("https://jap-study-pilot.koto37.workers.dev/audio/manifest.json", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    mt=page.inner_text("body")[:60]
    print("manifest 접근:", ("wav" in mt or "mp3" in mt or "{" in mt), "|", mt[:50])
