# -*- coding: utf-8 -*-
"""화면 자막 캡처 OCR — 범용 도구.

영상(유튜브 등)의 화면에서 지정한 영역의 글자가 바뀔 때마다 캡처해
일본어 OCR로 텍스트를 추출, 파일에 누적 저장한다.

실행(사용자가 직접):  python tools/ocr_capture.py
  1) 반투명 화면이 뜨면 자막이 표시되는 영역을 마우스로 드래그해 지정
  2) 영상을 재생하면 글자가 바뀔 때마다 자동으로 추출됨 (콘솔에 표시)
  3) 끝나면 콘솔 창에서 Ctrl+C → 결과는 ocr-result.txt (프로젝트 루트)
  4) 학습 앱 노래 탭의 [OCR 결과 불러오기] 버튼으로 바로 가져올 수 있다

엔진: RapidOCR (onnxruntime, 일본어 지원, 모델은 미리 받아둠 — 로딩 몇 초)
"""
import ctypes
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_FILE = Path(__file__).resolve().parent.parent / "ocr-result.txt"
POLL_SEC = 0.6          # 화면 확인 주기
DIFF_THRESHOLD = 6.0    # 이 이상 화면이 변하면 "자막이 바뀜"으로 판단 (0~255 평균차)
STABLE_TICKS = 1        # 변화 후 이만큼 안정되면 캡처 (전환 애니메이션 중 캡처 방지)


def select_region():
    """반투명 전체화면에서 드래그로 캡처 영역 선택."""
    import tkinter as tk

    sel = {}
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.30)
    root.attributes("-topmost", True)
    canvas = tk.Canvas(root, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.create_text(
        root.winfo_screenwidth() // 2, 60,
        text="자막(가사)이 나오는 영역을 드래그로 지정  (Esc = 취소)",
        fill="white", font=("Malgun Gothic", 18, "bold"))
    start = [0, 0]
    rect = [None]

    def press(e):
        start[0], start[1] = e.x, e.y
        rect[0] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=3)

    def drag(e):
        if rect[0]:
            canvas.coords(rect[0], start[0], start[1], e.x, e.y)

    def release(e):
        box = (min(start[0], e.x), min(start[1], e.y), max(start[0], e.x), max(start[1], e.y))
        if box[2] - box[0] > 30 and box[3] - box[1] > 15:
            sel["box"] = box
        root.destroy()

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", release)
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()
    return sel.get("box")


def frame_diff(a, b):
    from PIL import ImageChops
    import numpy as np
    diff = ImageChops.difference(a.convert("L"), b.convert("L"))
    return float(np.asarray(diff).mean())


def main():
    # DPI 스케일링 환경에서 좌표가 어긋나지 않게
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    from PIL import ImageGrab

    print("영역 선택 화면을 띄운다...")
    box = select_region()
    if not box:
        print("취소됨.")
        return
    print(f"영역 지정 완료: {box}")
    print("OCR 엔진 로딩 중...")
    import logging
    logging.getLogger("RapidOCR").setLevel(logging.WARNING)
    import numpy as np
    from rapidocr import RapidOCR
    engine = RapidOCR(params={"Rec.lang_type": "japan"})

    def do_ocr(img):
        res = engine(np.asarray(img))
        return "".join(res.txts or ()).strip()

    print("준비 완료! 이제 영상을 재생해줘. 글자가 바뀔 때마다 자동 추출된다. (종료: Ctrl+C)")
    print(f"결과 파일: {OUT_FILE}\n")

    prev = ImageGrab.grab(bbox=box)
    seen = set()
    pending = 0
    collected = 0

    try:
        while True:
            time.sleep(POLL_SEC)
            cur = ImageGrab.grab(bbox=box)
            d = frame_diff(prev, cur)
            prev = cur
            if d > DIFF_THRESHOLD:
                pending = STABLE_TICKS  # 변화 감지 → 안정될 때까지 대기
                continue
            if pending > 0:
                pending -= 1
                if pending == 0:
                    text = do_ocr(cur)
                    key = "".join(text.split())
                    if len(key) >= 2 and key not in seen:
                        seen.add(key)
                        collected += 1
                        with open(OUT_FILE, "a", encoding="utf-8") as f:
                            f.write(text + "\n")
                        print(f"[{collected:02d}] {text}")
    except KeyboardInterrupt:
        print(f"\n종료. 총 {collected}줄 → {OUT_FILE}")
        print("이 파일 내용을 복사해서 학습 앱 노래 탭의 [가사 등록] 칸에 붙여넣으면 된다.")


if __name__ == "__main__":
    main()
