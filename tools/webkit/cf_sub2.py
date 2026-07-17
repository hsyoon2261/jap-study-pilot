# -*- coding: utf-8 -*-
"""'Subdomain' 라벨과 같은 줄의 맨 오른쪽 버튼(연필) 좌표 계산 → 클릭."""
from browser_core import attach_chrome, snap

ACCT = "6ee81334fcdc1f3c171044e8ad914f28"
URL = f"https://dash.cloudflare.com/{ACCT}/workers-and-pages"

JS = r"""() => {
  let label = null;
  for (const e of document.querySelectorAll('*')) {
    if (e.children.length === 0 && (e.textContent||'').trim() === 'Subdomain') { label = e; break; }
  }
  if (!label) return {err: 'Subdomain 라벨 없음'};
  label.scrollIntoView({block: 'center'});
  const lr = label.getBoundingClientRect();
  const ly = lr.y + lr.height/2;
  let best = null;
  for (const b of document.querySelectorAll('button, [role=button], a')) {
    const r = b.getBoundingClientRect();
    if (r.width > 4 && r.height > 4 && Math.abs((r.y + r.height/2) - ly) < 26) {
      if (!best || r.x > best.r.x) best = {r};
    }
  }
  if (!best) return {err: '같은 줄 버튼 없음'};
  return {x: best.r.x + best.r.width/2, y: best.r.y + best.r.height/2, dpr: window.devicePixelRatio};
}"""

with attach_chrome() as (browser, ctx):
    page = next((p for p in ctx.pages if "cloudflare" in p.url), None) or ctx.new_page()
    page.bring_to_front()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4500)
    res = page.evaluate(JS)
    print("연필 좌표:", res)
    if "x" in res:
        page.mouse.click(res["x"], res["y"])
        page.wait_for_timeout(2800)
    snap(page, "cf_sub_edit5")
    body = page.inner_text("body")
    print("편집 UI 단서:", [k for k in ("Change subdomain", "Update", "Save", "Cancel", "available", "Register") if k in body])
