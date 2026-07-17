# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
NEW="koto37"
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "subdomain" in p.url), None) or ctx.pages[0]
    page.bring_to_front(); page.wait_for_timeout(400)
    # 보이는 text input (사이드바 옆, w>300)
    JS=r"""() => {
      for(const i of document.querySelectorAll('input[type=text]')){
        const r=i.getBoundingClientRect();
        if(r.width>300 && r.height>10) return {x:r.x+r.width/2, y:r.y+r.height/2};
      }
      return {err:'no'};
    }"""
    res=page.evaluate(JS); print("입력칸:",res)
    page.mouse.click(res["x"], res["y"]); page.wait_for_timeout(300)
    page.keyboard.type(NEW, delay=40); page.wait_for_timeout(600)
    print("타이핑:", NEW)
    try:
        page.get_by_role("button", name="Continue").click(); print("Continue 클릭")
    except Exception as e:
        print("Continue role 실패:", e)
    page.wait_for_timeout(4000); snap(page,"cf_set_step2")
    b=page.inner_text("body")
    print("단서:", [k for k in ("available","not available","taken","Confirm","already","Update subdomain","valid","error") if k in b])
