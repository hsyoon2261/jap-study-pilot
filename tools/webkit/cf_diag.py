# -*- coding: utf-8 -*-
from browser_core import attach_chrome
ACCT = "6ee81334fcdc1f3c171044e8ad914f28"
URL = f"https://dash.cloudflare.com/{ACCT}/workers-and-pages"
JS = r"""() => {
  const out = {vw: innerWidth, vh: innerHeight, dpr: devicePixelRatio, hits: []};
  for (const e of document.querySelectorAll('*')) {
    const t = (e.textContent||'').trim();
    if (t === 'szpdkss3.workers.dev' && e.children.length <= 1) {
      e.scrollIntoView({block:'center'});
      const r = e.getBoundingClientRect();
      // 이 값 요소의 부모 행에서 svg/버튼 찾기
      let row = e; for(let i=0;i<4 && row.parentElement;i++) row=row.parentElement;
      const icons = [...row.querySelectorAll('svg,button,[role=button]')].map(x=>{
        const rr=x.getBoundingClientRect(); return {tag:x.tagName, x:Math.round(rr.x), y:Math.round(rr.y), w:Math.round(rr.width)};
      });
      out.hits.push({tag:e.tagName, x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), icons});
    }
  }
  return out;
}"""
with attach_chrome() as (browser, ctx):
    page = next((p for p in ctx.pages if "cloudflare" in p.url), None) or ctx.new_page()
    page.bring_to_front()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4500)
    import json
    print(json.dumps(page.evaluate(JS), ensure_ascii=False, indent=1))
