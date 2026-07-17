# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
ACCT="6ee81334fcdc1f3c171044e8ad914f28"
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "cloudflare" in p.url), None) or ctx.pages[0]
    page.bring_to_front()
    page.goto(f"https://dash.cloudflare.com/{ACCT}/workers-and-pages", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    sub = page.evaluate(r"""() => {
      for(const e of document.querySelectorAll('*')){
        const t=(e.textContent||'').trim();
        if(/^[a-z0-9-]+\.workers\.dev$/.test(t) && e.children.length<=1){
          const r=e.getBoundingClientRect(); if(r.height>5) return t;
        }
      }
      return '?';
    }""")
    print("현재 계정 서브도메인:", sub)
    # 새 주소 시도
    NEW="https://jap-study-pilot.koto37.workers.dev/"
    try:
        page.goto(NEW, wait_until="domcontentloaded", timeout=30000); page.wait_for_timeout(5000)
        title=page.title(); ok="일본어 학습" in page.inner_text("body")
        print(f"새 주소 {NEW} → 제목 '{title}' / 앱뜸 {ok}")
    except Exception as e:
        print("새 주소 아직(전파 대기):", str(e)[:60])
    snap(page,"cf_verify")
