# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
ACCT = "6ee81334fcdc1f3c171044e8ad914f28"
URL = f"https://dash.cloudflare.com/{ACCT}/workers-and-pages"
JS = r"""() => {
  let label=null;
  for (const e of document.querySelectorAll('*')) {
    if (e.children.length===0 && (e.textContent||'').trim()==='Subdomain'){ label=e; break; }
  }
  if(!label) return {err:'no label'};
  label.scrollIntoView({block:'center'});
  const ly = label.getBoundingClientRect().y + 8;
  let best=null;
  for (const s of document.querySelectorAll('svg')) {
    const r=s.getBoundingClientRect();
    if (r.width>4 && r.height>4 && Math.abs((r.y+r.height/2)-ly) < 26) {
      if(!best || r.x>best.x) best={x:r.x+r.width/2, y:r.y+r.height/2};
    }
  }
  return best || {err:'no svg on row', ly};
}"""
with attach_chrome() as (browser, ctx):
    page = next((p for p in ctx.pages if "cloudflare" in p.url), None) or ctx.new_page()
    page.bring_to_front()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4500)
    res = page.evaluate(JS)
    print("svg 좌표:", res)
    if "x" in res:
        page.mouse.click(res["x"], res["y"]); page.wait_for_timeout(2800)
    snap(page, "cf_sub_edit6")
    body = page.inner_text("body")
    print("편집 UI:", [k for k in ("Subdomain name","available","Save","Cancel","Update","Register","Change") if k in body])
