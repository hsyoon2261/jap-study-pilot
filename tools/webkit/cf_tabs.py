# -*- coding: utf-8 -*-
from browser_core import attach_chrome
with attach_chrome() as (browser, ctx):
    for i,p in enumerate(ctx.pages):
        try:
            has = "Change account subdomain" in p.inner_text("body")
        except Exception:
            has = "?"
        n_in = len(p.query_selector_all("input"))
        print(f"[{i}] change페이지={has} inputs={n_in} | {p.url[:80]}")
