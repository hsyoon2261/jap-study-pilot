# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
LIVE="https://jap-study-pilot.koto37.workers.dev"
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "koto37" in p.url or "cloudflare" in p.url), None) or ctx.pages[0]
    page.bring_to_front()
    try:
        page.goto(LIVE+"/drill?set=d2-6", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)
        b=page.inner_text("body")
        stub = "이식 예정" in b or "P2" in b
        q = ("/ " in b and "정답" in b) or any(c in b for c in ("눈·귀","다음","발음"))
        print("SSL/접속 OK. 스텁(구버전):", stub, "| 문제뜸:", q)
        print("본문 일부:", b.replace("\n"," ")[:120])
        snap(page,"live_drill")
    except Exception as e:
        print("접속 실패(빌드중/SSL대기?):", str(e)[:70])
