# 연결 점검: 이 킷의 크롬에 붙어서 탭 목록 출력 (없으면 자동 실행)
from browser_core import attach_chrome

with attach_chrome() as (browser, ctx):
    for p in ctx.pages:
        try:
            print(f"  - {p.title()[:40] or '(제목 없음)'} | {p.url[:70]}")
        except Exception:
            pass
