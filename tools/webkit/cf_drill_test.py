# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "koto37" in p.url or "cloudflare" in p.url), None) or ctx.pages[0]
    page.bring_to_front()
    page.goto("https://jap-study-pilot.koto37.workers.dev/drill?set=d2-1", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3500)
    prompt = page.evaluate("() => document.querySelector('.prompt')?.textContent || ''")
    nch = page.evaluate("() => document.querySelectorAll('.choice').length")
    stub = "이식 예정" in page.inner_text("body")
    print(f"문제 프롬프트: '{prompt}' / 보기 수: {nch} / 스텁: {stub}")
    if nch>=4:
        # 정답 보기 클릭 (내부적으로 _correct는 없지만 아무거나 눌러 채점 확인)
        page.evaluate("() => document.querySelectorAll('.choice')[0].click()")
        page.wait_for_timeout(800)
        fb = page.evaluate("() => document.querySelector('.feedback')?.textContent || ''")
        print("채점 피드백:", fb[:70])
    snap(page,"live_drill_work")
