# -*- coding: utf-8 -*-
from browser_core import attach_chrome
import json
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "subdomain" in p.url), None) or ctx.pages[0]
    page.bring_to_front()
    JS=r"""() => {
      const out=[];
      for(const inp of document.querySelectorAll('input, textarea, [contenteditable]')){
        const r=inp.getBoundingClientRect();
        out.push({tag:inp.tagName, type:inp.type||'', ph:inp.placeholder||'', x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height), vis:r.width>0&&r.height>0});
      }
      return {vw:innerWidth, dpr:devicePixelRatio, inputs:out};
    }"""
    print(json.dumps(page.evaluate(JS), ensure_ascii=False))
