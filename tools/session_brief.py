# -*- coding: utf-8 -*-
"""세션 시작 브리핑 — SessionStart 훅이 실행해 튜터(Claude) 컨텍스트에 주입한다.

진도 / 오늘의 세트 상태 / 최근 드릴 통계 / 미해결 오답을 한 화면으로 요약.
표준 라이브러리만 사용, 실패해도 죽지 않는다 (훅이 세션을 막으면 안 됨).
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def section(title):
    print(f"\n[{title}]")


def safe(fn):
    try:
        fn()
    except Exception as e:  # 브리핑 일부 실패는 무시하고 계속
        print(f"  (읽기 실패: {e})")


def progress():
    section("진도 (progress.md 현재 상태)")
    with open(os.path.join(BASE, "progress.md"), encoding="utf-8") as f:
        lines = f.read().splitlines()
    inside = False
    for ln in lines:
        if ln.startswith("## 현재 상태"):
            inside = True
            continue
        if inside and (ln.startswith("## ") or ln.startswith("---")):
            break
        if inside and ln.strip():
            print(" " + ln)


def sets_status():
    section("오늘의 세트 (data/sets.json)")
    path = os.path.join(DATA, "sets.json")
    if not os.path.exists(path):
        print("  세트 없음 — 학습자가 범위를 알려주면 생성할 것")
        return
    sets = json.load(open(path, encoding="utf-8"))
    if not sets:
        print("  세트 없음 — 학습자가 범위를 알려주면 생성할 것")
        return
    for s in sets:
        mark = "완료 " + (s.get("doneAt") or "") if s.get("done") else "미완료"
        print(f"  - {s['title']} → {mark}")
    done_wait = [s for s in sets if s.get("done")]
    if done_wait:
        print("  ※ 완료된 세트는 피드백 후 sets-archive.json으로 이동할 것")


def drill_stats():
    section("최근 7일 드릴 (session-log.jsonl)")
    path = os.path.join(DATA, "session-log.jsonl")
    if not os.path.exists(path):
        print("  기록 없음")
        return
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    days = {}
    wrong = Counter()
    speed = []
    for ln in open(path, encoding="utf-8"):
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        d = e["ts"][:10]
        if d < cutoff:
            continue
        days.setdefault(d, [0, 0])
        days[d][0] += 1
        days[d][1] += 1 if e["correct"] else 0
        if not e["correct"]:
            wrong[e["item"]] += 1
        if isinstance(e.get("ms"), int) and e["ms"] < 30000:
            speed.append(e["ms"])
    if not days:
        print("  최근 7일 기록 없음")
        return
    for d in sorted(days, reverse=True):
        t, c = days[d]
        print(f"  {d}: {t}문제, 정답률 {round(c / t * 100)}%")
    if wrong:
        top = ", ".join(f"{k}×{v}" for k, v in wrong.most_common(8))
        print(f"  자주 틀림: {top}")
    if speed:
        avg = sum(speed) / len(speed) / 1000
        print(f"  평균 응답 속도: {avg:.1f}초 ({len(speed)}문제 기준)")


def mistakes():
    section("미해결 오답 (notes/mistakes.md)")
    path = os.path.join(BASE, "notes", "mistakes.md")
    count = 0
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if ln.startswith("|") and "~~" not in ln and "날짜" not in ln and "---" not in ln:
            print("  " + ln)
            count += 1
    if count == 0:
        print("  없음")


print("=== 세션 시작 브리핑 (자동 주입) ===")
safe(progress)
safe(sets_status)
safe(drill_stats)
safe(mistakes)
print("\n(학습자가 특별한 요청 없이 시작하면 위 상태 기준으로 바로 진행할 것. 완료된 세트가 있으면 피드백부터.)")
