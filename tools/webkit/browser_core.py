# 범용 브라우저 자동화 코어 — 전용 디버그 크롬에 붙어 제어
# 이 킷은 복사해서 주제별로 쓰는 템플릿: 포트는 폴더 경로에서 자동 계산되므로
# 복사본마다 저절로 달라져 여러 킷을 동시에 띄워도 충돌하지 않는다.
# (수동 지정이 필요하면 이 폴더에 port.txt 파일을 만들고 숫자만 적기)
#
# 사용 예:
#   from browser_core import attach_chrome, page_for, snap, dump_structure
#   with attach_chrome() as (browser, ctx):
#       page = page_for(ctx, "naver.com", create_url="https://www.naver.com")
#       snap(page, "확인")            # 스크린샷 → snaps\
#       dump_structure(page, "구조")   # 입력칸/버튼 목록 → snaps\
# 연결이 끊겨도(스크립트 종료) 크롬 창과 탭은 그대로 유지된다.
import sys, pathlib, contextlib, zlib
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
DEBUG_PROFILE = HERE / "chrome-profile"    # 이 킷 전용 프로필 (로그인 유지)

_port_file = HERE / "port.txt"
if _port_file.exists():
    DEBUG_PORT = int(_port_file.read_text(encoding="utf-8").strip())
else:  # 폴더 경로 → 9300~9999 사이 고정 포트 (복사본마다 다름)
    DEBUG_PORT = 9300 + zlib.crc32(str(HERE.resolve()).lower().encode("utf-8")) % 700


def find_chrome():
    import os
    for c in (os.path.expandvars(p) for p in (
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe")):
        if pathlib.Path(c).exists():
            return c
    raise RuntimeError("크롬(chrome.exe)을 못 찾음 — 크롬 설치가 필요합니다")


def ensure_debug_chrome(debug_port=None, launch_if_needed=True, start_url=None):
    """이 킷의 디버그 크롬이 떠 있게 보장. 없으면 실행해서 뜰 때까지 대기."""
    import urllib.request, subprocess, time
    debug_port = debug_port or DEBUG_PORT
    endpoint = f"http://localhost:{debug_port}/json/version"

    def alive():
        try:
            urllib.request.urlopen(endpoint, timeout=2); return True
        except Exception:
            return False

    if not alive() and launch_if_needed:
        args = [find_chrome(), f"--remote-debugging-port={debug_port}",
                f"--user-data-dir={DEBUG_PROFILE}",
                "--no-first-run", "--no-default-browser-check"]
        if start_url:
            args.append(start_url)
        subprocess.Popen(args)
        for _ in range(20):
            if alive():
                break
            time.sleep(1)
    if not alive():
        raise RuntimeError(f"디버그 크롬(포트 {debug_port}) 없음. 크롬실행.bat을 먼저 실행하세요.")
    return debug_port


@contextlib.contextmanager
def attach_chrome(debug_port=None, launch_if_needed=True, start_url=None):
    """이 킷의 디버그 크롬에 붙는다. (browser, context) 반환.
    browser.close()는 연결만 끊고 실제 크롬 창은 닫지 않는다."""
    debug_port = ensure_debug_chrome(debug_port, launch_if_needed, start_url)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        print(f"[코어] 디버그 크롬에 붙음 (포트 {debug_port}, 탭 {len(ctx.pages)}개)")
        try:
            yield browser, ctx
        finally:
            browser.close()


def page_for(ctx, url_part, create_url=None, wait_ms=4000):
    """url_part가 들어간 탭을 찾고, 없으면 create_url로 새 탭을 연다."""
    page = next((p for p in ctx.pages if url_part in p.url), None)
    if page is None and create_url:
        page = ctx.new_page()
        page.goto(create_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(wait_ms)
    return page


def snap(page, name, full=False):
    r"""스크린샷 → snaps\ 폴더."""
    (HERE / "snaps").mkdir(exist_ok=True)
    path = HERE / "snaps" / f"{name}.png"
    page.screenshot(path=str(path), full_page=full)
    print("[스냅]", path)
    return path


def dump_structure(page, name):
    r"""입력칸/버튼/링크 구조를 파일로 기록 (새 사이트 파악용) → snaps\."""
    (HERE / "snaps").mkdir(exist_ok=True)
    path = HERE / "snaps" / f"{name}.txt"
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(f"URL: {page.url}\n제목: {page.title()}\n\n")
        for f in page.frames:
            try:
                els = f.locator("input, select, textarea, button, a, [onclick]").all()
            except Exception:
                continue
            if not els:
                continue
            fp.write(f"\n=== frame: {f.url[:80]} — {len(els)}개 ===\n")
            for el in els[:600]:
                try:
                    tag = el.evaluate("e => e.tagName")
                    txt = (el.inner_text() or "").strip().replace("\n", " ")[:40] \
                        if tag in ("BUTTON", "A", "LI", "DIV", "SPAN") else ""
                    fp.write(f"{tag} | type={el.get_attribute('type')} | id={el.get_attribute('id')}"
                             f" | name={el.get_attribute('name')} | text={txt}\n")
                except Exception:
                    pass
    print("[구조]", path)
    return path


if __name__ == "__main__":
    print(f"이 킷의 포트: {DEBUG_PORT} (폴더: {HERE})")
