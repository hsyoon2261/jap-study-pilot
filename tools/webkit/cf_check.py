# -*- coding: utf-8 -*-
"""전용 크롬에 붙어 현재 Cloudflare 상태 확인."""
from browser_core import attach_chrome, page_for, snap

with attach_chrome() as (browser, ctx):
    print("탭 목록:")
    for p in ctx.pages:
        print("  -", p.url[:90])
    page = next((p for p in ctx.pages if "cloudflare" in p.url), None)
    if page is None:
        page = page_for(ctx, "cloudflare", create_url="https://dash.cloudflare.com/")
    page.bring_to_front()
    print("\n현재 URL:", page.url)
    print("제목:", page.title())
    snap(page, "cf_now")
