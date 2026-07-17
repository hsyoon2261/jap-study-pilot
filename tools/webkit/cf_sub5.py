# -*- coding: utf-8 -*-
from browser_core import attach_chrome, snap
ACCT="6ee81334fcdc1f3c171044e8ad914f28"
URL=f"https://dash.cloudflare.com/{ACCT}/workers-and-pages"
JS=r"""() => {
  let val=null;
  for(const e of document.querySelectorAll('*')){
    if((e.textContent||'').trim()==='szpdkss3.workers.dev' && e.children.length<=1){ val=e; break; }
  }
  if(!val) return {err:'no val'};
  val.scrollIntoView({block:'center'});
  const vr=val.getBoundingClientRect(); const vy=vr.y+vr.height/2;
  let best=null;
  for(const s of document.querySelectorAll('svg')){
    const r=s.getBoundingClientRect();
    if(r.width>4 && r.width<30 && Math.abs((r.y+r.height/2)-vy)<15){
      if(best===null || r.x>best.x) best={x:r.x+r.width/2,y:r.y+r.height/2};
    }
  }
  return best||{err:'no pencil', vy};
}"""
with attach_chrome() as (browser, ctx):
    page=next((p for p in ctx.pages if "cloudflare" in p.url),None) or ctx.new_page()
    page.bring_to_front()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000); page.wait_for_timeout(4500)
    res=page.evaluate(JS); print("연필:",res)
    if "x" in res:
        page.mouse.click(res["x"],res["y"]); page.wait_for_timeout(3000)
    snap(page,"cf_sub_edit8")
    body=page.inner_text("body")
    print("편집UI:", [k for k in ("available","Save","Cancel","Update","Register","subdomain","This action","input") if k in body])
