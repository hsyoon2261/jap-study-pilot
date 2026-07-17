# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "subdomain" in p.url), None) or ctx.pages[0]
    page.bring_to_front(); page.wait_for_timeout(400)
    try:
        page.get_by_role("button", name="Update", exact=True).click(); print("Update 클릭")
    except Exception as e:
        print("Update role 실패:", e)
    page.wait_for_timeout(5000); snap(page,"cf_updated")
    b=page.inner_text("body")
    print("결과단서:", [k for k in ("koto37.workers.dev","success","Success","updated","Subdomain") if k in b][:6])
