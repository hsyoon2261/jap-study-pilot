# -*- coding: utf-8 -*-
"""일본어 학습 훈련 서버 — 표준 라이브러리만 사용.

실행:  python tools/server.py   (브라우저 자동 오픈, 종료는 Ctrl+C)

역할:
  - tools/web/ 정적 파일 서빙 (훈련 엔진 UI)
  - data/decks/*.json 덱 목록·내용 제공
  - 답안 기록: data/review-state.json (SRS 상태) + data/session-log.jsonl (전체 이력)
데이터는 전부 파일이라 튜터(Claude)가 세션에서 읽고 수업에 반영한다.
"""
import asyncio
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

edge_tts = None  # 뉴럴 TTS. 임포트가 느려서 첫 요청 때 지연 로드 (시작 속도 우선)


def _load_edge_tts():
    global edge_tts
    if edge_tts is None:
        try:
            import edge_tts as mod
            edge_tts = mod
        except ImportError:
            edge_tts = False  # 미설치 → 브라우저 내장 TTS 폴백
    return edge_tts

TOOLS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(TOOLS)
WEB = os.path.join(TOOLS, "web")
DATA = os.path.join(BASE, "data")
DECKS = os.path.join(DATA, "decks")
STATE_FILE = os.path.join(DATA, "review-state.json")
LOG_FILE = os.path.join(DATA, "session-log.jsonl")
SETS_FILE = os.path.join(DATA, "sets.json")
SETS_ARCHIVE_FILE = os.path.join(DATA, "sets-archive.json")
SONGS_FILE = os.path.join(DATA, "songs.json")
VIDEO_TEXT_DIR = os.path.join(DATA, "video-text")
TTS_CACHE = os.path.join(DATA, "tts-cache")
AUDIO_KANA = os.path.join(DATA, "audio", "kana")
AUDIO_KANA_SLOW = os.path.join(DATA, "audio", "kana-slow")  # 1.5배 느린 버전 (학습자 요청 2026-07-18)
TTS_VOICE = "ja-JP-NanamiNeural"
TTS_RATE = "-35%"       # edge-tts 폴백 (아래 배속과 체감 통일)
TTS_RATE_SLOW = "-55%"  # "느리게 발음" 버튼용 폴백
# 성우 엔진 배속 — 학습자 기준 "전부 25% 느리게" (2026-07-18). 여기 숫자만 바꾸면 전체 반영
TTS_SPEED = 0.8         # 단어·문장 기본
TTS_SPEED_SLOW = 0.6    # "느리게 발음" 버튼
TTS_SPEED_MORA = 0.56   # 한 글자·요음 (기본 0.7에서 같은 비율로 감속)
# 로컬 성우 엔진 (같은 API, 앞선 것 우선): AivisSpeech = 자연스러움 최상급 / VOICEVOX = 캐릭터 다양 (폴백·롤플레이용)
LOCAL_TTS = [
    {"name": "aivis", "url": "http://127.0.0.1:10101", "speaker": 888753760,  # まお ノーマル
     "dir": os.path.join(BASE, "tools", "aivisspeech")},
    {"name": "voicevox", "url": "http://127.0.0.1:50021", "speaker": 8,  # 春日部つむぎ
     "dir": os.path.join(BASE, "tools", "voicevox")},
]
_tts_alive_cache = {}  # url -> (검사시각, 살아있나) — 요청마다 죽은 엔진 타임아웃 기다리지 않게
TTS_CONFIG = os.path.join(DATA, "tts-config.json")  # 학습자가 고른 성우 ("engine:styleId" 또는 default)
# 성우 메뉴 — 웹 레퍼런스로 엄선 (명료함·후기 기준, 2026-07-18). 원본 목록 54개 전부 노출 금지.
# ※ Anneli 계열은 실존 성우 무단 복제 판명으로 배포 중단 — 절대 추가 금지.
VOICE_MENU = [
    {"id": "default", "label": "기본 조합", "desc": "한 글자는 원어민 녹음 + 단어·문장은 마오"},
    {"id": "aivis:888753760", "label": "마오 (여) ⭐", "desc": "AivisSpeech — 자연스럽고 따뜻한 여성 음성, 로컬 TTS 중 자연스러움 최상위 평가 (기본값)"},
    {"id": "aivis:888753763", "label": "마오·차분 (여)", "desc": "마오의 차분·부드러운 톤 — 더 낮고 안정적"},
    {"id": "aivis:1878365376", "label": "코하쿠 (여)", "desc": "AivisSpeech — 밝고 부드러운 여성"},
    {"id": "edge:ja-JP-NanamiNeural", "label": "나나미 (여)", "desc": "Microsoft 뉴럴 — 아나운서처럼 정확·명료 (감정 적은 편)"},
    {"id": "voicevox:8", "label": "츠무기 (여)", "desc": "VOICEVOX — 차분한 누나 톤"},
    {"id": "edge:ja-JP-KeitaNeural", "label": "케이타 (남)", "desc": "Microsoft 뉴럴 남성 — 깨끗한 표준 발음"},
    {"id": "voicevox:13", "label": "류세이 (남)", "desc": "VOICEVOX — 낮고 안정감 있는 성인 남성"},
]

PORT = 8765

# 라이트너 박스별 다음 복습 간격(일). 틀리면 박스 0으로 리셋.
BOX_INTERVAL_DAYS = [0, 1, 3, 7, 14, 30]

_lock = threading.Lock()


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def record_answer(payload):
    """답안 하나를 SRS 상태와 로그에 반영한다."""
    deck = payload["deck"]
    item = payload["item"]
    correct = bool(payload["correct"])
    mode = payload.get("mode", "choice")
    now = datetime.now()
    key = f"{deck}:{item}"

    with _lock:
        state = _read_json(STATE_FILE, {})
        s = state.get(key, {"box": 0, "right": 0, "wrong": 0})
        if correct:
            s["box"] = min(s["box"] + 1, len(BOX_INTERVAL_DAYS) - 1)
            s["right"] += 1
        else:
            s["box"] = 0
            s["wrong"] += 1
        s["due"] = (now + timedelta(days=BOX_INTERVAL_DAYS[s["box"]])).strftime("%Y-%m-%dT%H:%M:%S")
        s["last"] = now.strftime("%Y-%m-%dT%H:%M:%S")
        state[key] = s
        _write_json(STATE_FILE, state)

        os.makedirs(DATA, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            entry = {
                "ts": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "deck": deck, "item": item, "mode": mode, "correct": correct,
            }
            if isinstance(payload.get("ms"), (int, float)):
                entry["ms"] = int(payload["ms"])  # 인식 속도 추적 (자동화 진행도 지표)
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return s


# ── 가사 페이지 불러오기 (헬퍼 — 실행은 학습자가 버튼으로 트리거) ──
def _parse_utaten(html):
    """우타텐 가사 페이지에서 가사 본문을 추출. 후리가나는 漢字（かな） 형태로."""
    from html.parser import HTMLParser

    def run(target_class):
        class P(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.in_rt = False
                self.buf = []

            def handle_starttag(self, tag, attrs):
                cls = dict(attrs).get("class", "") or ""
                if self.depth == 0 and tag == "div" and target_class in cls.split():
                    self.depth = 1
                    return
                if self.depth > 0:
                    if tag == "div":
                        self.depth += 1
                    elif tag == "br":
                        self.buf.append("\n")
                    elif tag == "span" and "rt" in cls.split():
                        self.in_rt = True
                        self.buf.append("（")

            def handle_endtag(self, tag):
                if self.depth > 0:
                    if tag == "div":
                        self.depth -= 1
                    elif tag == "span" and self.in_rt:
                        self.in_rt = False
                        self.buf.append("）")

            def handle_data(self, data):
                if self.depth > 0:
                    self.buf.append(data)

        p = P()
        p.feed(html)
        text = "".join(p.buf)
        lines = [ln.strip() for ln in text.splitlines()]
        out = []
        for ln in lines:
            if ln or (out and out[-1]):
                out.append(ln)
        return "\n".join(out).strip()

    for cls in ("hiragana", "romaji", "lyricBody", "medium"):
        text = run(cls)
        if len(text) > 30:
            return text
    return None


def fetch_lyrics_page(url):
    """가사 페이지 HTML을 받아 본문 텍스트를 추출해 반환."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept-Language": "ja,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")
    return _parse_utaten(html), html


# ── 공식 자막 큐 가져오기 + 가사↔큐 정렬 (원클릭 세팅용) ──
def fetch_subtitle_cues(video_id, langs=("ja", "ko", "en")):
    """공식 자막 트랙을 받아 (큐 리스트, 언어) 반환. 파일은 video-text에 보존."""
    import glob as globmod
    import shutil
    import tempfile
    from yt_dlp import YoutubeDL
    tmp = tempfile.mkdtemp(prefix="subs-")
    try:
        opts = {"skip_download": True, "writesubtitles": True,
                "subtitleslangs": list(langs), "subtitlesformat": "json3",
                "outtmpl": os.path.join(tmp, "s"), "quiet": True, "noprogress": True}
        with YoutubeDL(opts) as y:
            y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        for lang in langs:
            fs = globmod.glob(os.path.join(tmp, f"s.{lang}.json3"))
            if not fs:
                continue
            with open(fs[0], encoding="utf-8") as f:
                d = json.load(f)
            os.makedirs(VIDEO_TEXT_DIR, exist_ok=True)
            shutil.copy(fs[0], os.path.join(VIDEO_TEXT_DIR, f"subs-{video_id}.{lang}.json3"))
            cues = []
            for e in d.get("events", []):
                txt = "".join(sg.get("utf8", "") for sg in (e.get("segs") or [])).strip()
                if txt:
                    cues.append({"start": e["tStartMs"] / 1000,
                                 "end": (e["tStartMs"] + e.get("dDurationMs", 3000)) / 1000,
                                 "text": txt})
            if len(cues) >= 5:
                return cues, lang
        return None, None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _dp_align_lines(a_texts, b_texts):
    """a(가사 줄) ↔ b(자막 큐) 단조 정렬. a각 원소가 매칭된 b 인덱스 리스트 반환."""
    def bigrams(t):
        return {t[i:i + 2] for i in range(len(t) - 1)}

    def sim(x, y):
        A, B = bigrams(x), bigrams(y)
        return 2 * len(A & B) / (len(A) + len(B)) if A and B else 0.0

    L, C = len(a_texts), len(b_texts)
    M = [[-1e9] * (C + 1) for _ in range(L + 1)]
    BK = [[None] * (C + 1) for _ in range(L + 1)]
    M[0][0] = 0.0
    for j in range(1, C + 1):
        M[0][j] = M[0][j - 1] - 0.05
        BK[0][j] = ("skip_cue",)
    for i in range(1, L + 1):
        M[i][0] = M[i - 1][0] - 0.2
        BK[i][0] = ("skip_ln",)
        for j in range(1, C + 1):
            sc = sim(a_texts[i - 1], b_texts[j - 1])
            M[i][j], BK[i][j] = max([
                (M[i - 1][j - 1] + sc, ("match", j - 1)),
                (M[i - 1][j] + sc * 0.7, ("share", j - 1)),
                (M[i][j - 1] - 0.05, ("skip_cue",)),
                (M[i - 1][j] - 0.2, ("skip_ln",)),
            ])
    out = [None] * L
    i, j = L, C
    while i > 0 or j > 0:
        op = BK[i][j]
        if op[0] == "match":
            out[i - 1] = op[1]
            i -= 1
            j -= 1
        elif op[0] == "share":
            out[i - 1] = op[1]
            i -= 1
        elif op[0] == "skip_cue":
            j -= 1
        else:
            i -= 1
    for k in range(L):
        if out[k] is None:
            out[k] = out[k - 1] if k > 0 and out[k - 1] is not None else next(
                (x for x in out if x is not None), 0)
    return out


def setup_song_from_cues(song, lyric_text, cues, lang):
    """가사 텍스트를 큐 단위로 병합·정렬해 song에 lyric/lineTimes 기록."""
    import re as _re
    try:
        import pykakasi
        kks = pykakasi.kakasi()
    except ImportError:
        kks = None
    lines = [l.strip() for l in lyric_text.split("\n") if l.strip()]
    if kks and lang == "ja":
        def kana(t):
            t = "".join(i.get("hira") or "" for i in kks.convert(t))
            t = "".join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in t)
            return _re.sub(r"[^ぁ-ん0-9a-z]", "", t.lower())
        reading = lambda l: _re.sub(r"[一-龯々]+（([^）]+)）", r"\1", l)
        a = [kana(reading(l)) for l in lines]
        b = [kana(c["text"]) for c in cues]
    else:
        # 번역 자막뿐이면 텍스트 대조 불가 → 순서 기반 근사 (튜터 해석 후 /api/songs/align로 재정렬)
        a = [str(i) for i in range(len(lines))]
        b = [str(int(i * len(lines) / max(1, len(cues)))) for i in range(len(cues))]
    mapping = _dp_align_lines(a, b)
    groups, cur = [], [0]
    for k in range(1, len(lines)):
        if mapping[k] == mapping[cur[-1]]:
            cur.append(k)
        else:
            groups.append(cur)
            cur = [k]
    groups.append(cur)
    new_lines, new_times = [], []
    for grp in groups:
        c = cues[mapping[grp[0]]]
        new_lines.append("　".join(lines[k] for k in grp))
        new_times.append({"start": round(max(0, c["start"] - 0.1), 2),
                          "end": round(c["end"], 2), "sure": lang == "ja"})
    for k in range(1, len(new_times)):
        if new_times[k]["start"] < new_times[k - 1]["start"]:
            new_times[k]["start"] = round(new_times[k - 1]["start"] + 0.5, 2)
    # 문장 연속성 검수: 조사·연결형으로 끝나고 **보컬이 실제로 붙어 있는** 행만 병합.
    # 기준은 노래의 호흡이다 — 간주·쉼이 사이에 있으면 문법이 이어져도 절대 병합 금지 (학습자 지적 2026-07-18).
    # 이 판정은 행 끝을 늘리기 전(진짜 큐 끝 시각이 살아있을 때) 해야 한다.
    cont = set("はがをにでとのへてや")
    def _tail(line):
        t = _re.sub(r"（[^）]*）|[　\s「」『』…?？!！.,、。]", "", line)
        return t[-1] if t else ""
    i = 0
    while i < len(new_lines) - 1:
        dur = new_times[i + 1]["end"] - new_times[i]["start"]
        gap = new_times[i + 1]["start"] - new_times[i]["end"]  # 두 행 사이 보컬 공백
        if _tail(new_lines[i]) in cont and dur <= 20 and gap <= 2.0:
            new_lines[i] = new_lines[i] + "　" + new_lines[i + 1]
            new_times[i] = {"start": new_times[i]["start"], "end": new_times[i + 1]["end"],
                            "sure": bool(new_times[i].get("sure")) and bool(new_times[i + 1].get("sure"))}
            del new_lines[i + 1], new_times[i + 1]
        else:
            i += 1
    # 행 끝 확장: 다음 행 시작까지 잇되, 간주(3초 이상 공백)는 여운 2초만 남기고 끌고 가지 않는다
    for k in range(len(new_times) - 1):
        nxt = new_times[k + 1]["start"]
        if nxt - new_times[k]["end"] > 3.0:
            new_times[k]["end"] = round(new_times[k]["end"] + 2.0, 2)
        else:
            new_times[k]["end"] = round(max(new_times[k]["end"], nxt), 2)
    song["lyric"] = "\n".join(new_lines)
    song["lineNotes"] = None  # 해석은 튜터가 이어서 작성
    song["lineTimes"] = new_times
    return len(new_lines)


# ── 줄별 정밀 싱크 계산 (단어 타임스탬프 ↔ 등록 가사 문자 정렬) ──
def _kana_normalize(text, kks):
    """한자→가나 변환 + 가타카나→히라가나 + 기호 제거 (정렬 비교용)."""
    import re as _re
    t = "".join(item.get("hira") or "" for item in kks.convert(text))
    t = "".join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in t)
    return _re.sub(r"[^ぁ-ん0-9a-z]", "", t.lower())


def compute_line_times(song, video_data):
    """등록 가사의 각 줄이 실제로 불리는 시각을 문자 단위 전역 정렬로 계산.

    성공 시 song['lineTimes'] = [{start, end, sure?}] 갱신. 콘텐츠와 무관한 순수 계산.
    """
    import re as _re
    lyric = song.get("lyric")
    words = (video_data or {}).get("words") or []
    if not lyric or not words:
        return False
    try:
        import pykakasi
    except ImportError:
        return False
    kks = pykakasi.kakasi()
    lines = [l.strip() for l in lyric.split("\n") if l.strip()]
    reading = lambda l: _re.sub(r"[一-龯々]+（([^）]+)）", r"\1", l)  # 후리가나 우선

    lyr, line_ranges = [], []
    for l in lines:
        s0 = len(lyr)
        lyr.extend(_kana_normalize(reading(l), kks))
        line_ranges.append((s0, len(lyr)))
    stt, stt_t = [], []
    for w in words:
        for ch in _kana_normalize(w.get("text", ""), kks):
            stt.append(ch)
            stt_t.append(w["start"])
    n, m = len(lyr), len(stt)
    if n < 10 or m < 10:
        return False

    # 문자 단위 정렬 DP (match +2 / mismatch -1 / gap -1)
    MATCH, MIS, GAP = 2, -1, -1
    prev = [j * GAP for j in range(m + 1)]
    ops = [bytearray(m + 1) for _ in range(n + 1)]  # 0=대각 1=위(가사만) 2=왼쪽(음성만)
    for j in range(m + 1):
        ops[0][j] = 2
    for i in range(1, n + 1):
        cur = [prev[0] + GAP] + [0] * m
        ops[i][0] = 1
        ci = lyr[i - 1]
        row_prev, row_ops = prev, ops[i]
        for j in range(1, m + 1):
            d = row_prev[j - 1] + (MATCH if ci == stt[j - 1] else MIS)
            u = row_prev[j] + GAP
            l = cur[j - 1] + GAP
            if d >= u and d >= l:
                cur[j] = d
                row_ops[j] = 0
            elif u >= l:
                cur[j] = u
                row_ops[j] = 1
            else:
                cur[j] = l
                row_ops[j] = 2
        prev = cur

    align_time = [None] * n
    i, j = n, m
    while i > 0 or j > 0:
        op = ops[i][j] if i >= 0 else 2
        if i > 0 and j > 0 and op == 0:
            if lyr[i - 1] == stt[j - 1]:
                align_time[i - 1] = stt_t[j - 1]
            i -= 1
            j -= 1
        elif i > 0 and (op == 1 or j == 0):
            i -= 1
        else:
            j -= 1

    times = []
    for (s0, s1) in line_ranges:
        ts = sorted(t for t in (align_time[k] for k in range(s0, s1)) if t is not None)
        # 줄의 시작 = 매칭 문자들의 하위 25% 지점 (앞쪽 오매칭 이상치 완화)
        times.append({"start": round(ts[len(ts) // 4], 2), "sure": True} if len(ts) >= 3 else None)

    known = [k for k, t in enumerate(times) if t]
    if len(known) < max(3, len(lines) // 5):
        return False
    for k in range(len(times)):  # 미확정 줄은 이웃 사이 보간
        if times[k]:
            continue
        p = max((x for x in known if x < k), default=None)
        q = min((x for x in known if x > k), default=None)
        if p is None:
            times[k] = {"start": max(0.0, times[q]["start"] - 3.0 * (q - k))}
        elif q is None:
            times[k] = {"start": times[p]["start"] + 4.0 * (k - p)}
        else:
            frac = (k - p) / (q - p)
            times[k] = {"start": round(times[p]["start"] + (times[q]["start"] - times[p]["start"]) * frac, 2)}
    for k in range(1, len(times)):  # 단조 보정
        if times[k]["start"] < times[k - 1]["start"]:
            times[k]["start"] = round(times[k - 1]["start"] + 0.5, 2)
    for k in range(len(times)):  # 끝 = 다음 줄 시작
        nxt = times[k + 1]["start"] if k + 1 < len(times) else times[k]["start"] + 6
        times[k]["end"] = round(max(times[k]["start"] + 1.2, nxt), 2)
    song["lineTimes"] = times
    return True


# ── 영상 텍스트 추출 (앱 내장 기능 — 실행은 학습자가 앱 버튼으로 트리거) ──
_video_jobs = {}  # videoId -> "downloading" | "transcribing" | "done" | "error: ..."


def _extract_video_id(url):
    import re
    q = urllib.parse.urlparse(url)
    if q.hostname in ("youtu.be",):
        return q.path.lstrip("/")[:11]
    params = urllib.parse.parse_qs(q.query)
    if "v" in params:
        return params["v"][0][:11]
    m = re.search(r"[A-Za-z0-9_-]{11}", url)
    return m.group(0) if m else None


def get_text_from_video(url):
    """영상 음성에서 시간별 텍스트를 추출해 data/video-text/<id>.json에 저장한다.

    학습자가 앱에서 버튼으로 실행하는 내장 기능. 백그라운드 스레드에서 돈다.
    """
    vid = _extract_video_id(url)
    if not vid:
        return None
    out = os.path.join(VIDEO_TEXT_DIR, vid + ".json")
    if os.path.exists(out):
        _video_jobs[vid] = "done"
        return vid

    def job():
        import glob as globmod
        import shutil
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="vt-")
        try:
            _video_jobs[vid] = "downloading (영상 음성 받는 중)"
            from yt_dlp import YoutubeDL
            opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmpdir, "a.%(ext)s"),
                "quiet": True, "noprogress": True,
            }
            with YoutubeDL(opts) as y:
                y.extract_info(url, download=True)
            files = globmod.glob(os.path.join(tmpdir, "a.*"))
            if not files:
                raise RuntimeError("오디오 다운로드 실패")
            _video_jobs[vid] = "transcribing (음성 → 텍스트 변환 중, 몇 분 걸림)"
            from faster_whisper import WhisperModel
            model = WhisperModel("medium", device="cpu", compute_type="int8")
            # 노래용 설정: VAD 끔 + 단어 단위 타임스탬프 (정밀 싱크용)
            segments, _info = model.transcribe(
                files[0], language="ja",
                vad_filter=False, condition_on_previous_text=False,
                word_timestamps=True)
            segs, words_out = [], []
            for seg in segments:
                txt = seg.text.strip()
                if txt:
                    segs.append({"start": round(seg.start, 1), "end": round(seg.end, 1), "text": txt})
                for w in (seg.words or []):
                    wt = w.word.strip()
                    if wt:
                        words_out.append({"start": round(w.start, 2), "end": round(w.end, 2), "text": wt})
            os.makedirs(VIDEO_TEXT_DIR, exist_ok=True)
            _write_json(out, {"videoId": vid, "url": url, "segments": segs, "words": words_out})
            # 가사가 등록된 곡이면 줄별 정밀 싱크 자동 계산
            with _lock:
                songs_all = _read_json(SONGS_FILE, [])
                tgt = next((x for x in songs_all if x.get("videoId") == vid), None)
                if tgt and tgt.get("lyric") and compute_line_times(tgt, {"words": words_out}):
                    _write_json(SONGS_FILE, songs_all)
            _video_jobs[vid] = "done"
        except Exception as e:
            _video_jobs[vid] = f"error: {e}"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    if _video_jobs.get(vid, "").startswith(("downloading", "transcribing")):
        return vid  # 이미 진행 중
    _video_jobs[vid] = "downloading"
    threading.Thread(target=job, daemon=True).start()
    return vid


def get_valid_text_from_start_to_end(video_id, start, end):
    """추출된 시간별 텍스트에서 start~end 구간에 걸치는 항목만 반환."""
    data = _read_json(os.path.join(VIDEO_TEXT_DIR, video_id + ".json"), None)
    if not data:
        return None
    return [s for s in data.get("segments", [])
            if s["end"] > start and s["start"] < end]


def _slow_kana_clip(src, name):
    """원어민 가나 클립을 1.5배 느리게 (음높이 유지, atempo). 한 번 만들면 파일 캐시."""
    dst = os.path.join(AUDIO_KANA_SLOW, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    try:
        import imageio_ffmpeg
        os.makedirs(AUDIO_KANA_SLOW, exist_ok=True)
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", src,
             "-filter:a", "atempo=0.6667", "-vn", dst],
            capture_output=True, timeout=30)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return dst
    except Exception:
        pass
    return src  # 변환 실패 시 원본이라도 재생


def kana_audio_path(text):
    """단독 가나면 원어민 녹음 파일 경로를 반환 (가타카나는 히라가나 녹음 재사용).
    한 글자 발음은 짧고 빨라서 안 들린다는 피드백 → 1.5배 느린 버전을 기본으로 낸다."""
    if not text or len(text) > 2:
        return None
    hira = "".join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in text)
    p = os.path.join(AUDIO_KANA, hira + ".mp3")
    if not os.path.exists(p):
        return None
    return _slow_kana_clip(p, hira + ".mp3")


_engine_restart_at = {}  # url -> 마지막 자동 재기동 시각 (스팸 방지)


def _try_revive_engine(url):
    """죽은 로컬 엔진(설치된 것)을 조용히 재기동. 크래시로 목소리가 다른 걸로 새는 것 방지 (2026-07-18)."""
    eng = next((e for e in LOCAL_TTS if e["url"] == url), None)
    if not eng:
        return
    now = time.time()
    if now - _engine_restart_at.get(url, 0) < 60:  # 60초에 한 번만 시도
        return
    exe = os.path.join(eng["dir"], "run.exe")
    if not os.path.exists(exe):
        return
    _engine_restart_at[url] = now
    try:
        subprocess.Popen([exe, "--host", "127.0.0.1"], cwd=eng["dir"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x08000000)
    except Exception:
        pass


def _engine_alive(url, timeout=0.4):
    """엔진 생존 검사 — 15초 캐시로 죽은 엔진 타임아웃이 매 요청에 끼지 않게.
    죽어 있으면 자동 재기동 시도(부팅 중엔 이번 요청은 폴백, 다음 요청부터 정상)."""
    now = time.time()
    ts, ok = _tts_alive_cache.get(url, (0, False))
    if now - ts < 15:
        return ok
    try:
        urllib.request.urlopen(url + "/version", timeout=timeout)
        ok = True
    except Exception:
        ok = False
    _tts_alive_cache[url] = (now, ok)
    if not ok:
        _try_revive_engine(url)  # 죽었으면 되살리기 시도
    return ok


def start_local_tts_engines():
    """설치된 성우 엔진들을 조용히 백그라운드 기동 (서버 시작 시 1회). 없으면 패스."""
    for eng in LOCAL_TTS:
        exe = os.path.join(eng["dir"], "run.exe")
        if not os.path.exists(exe) or _engine_alive(eng["url"]):
            continue
        try:
            subprocess.Popen([exe, "--host", "127.0.0.1"], cwd=eng["dir"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=0x08000000)  # CREATE_NO_WINDOW
        except Exception:
            pass


def _get_voice():
    """학습자가 고른 성우 id ("engine:styleId"). 기본 조합이면 None."""
    try:
        with open(TTS_CONFIG, encoding="utf-8-sig") as f:  # BOM 있어도 읽힘
            v = json.load(f).get("voice")
        return v if v and v != "default" else None
    except Exception:
        return None


def _set_voice(vid):
    with _lock:
        with open(TTS_CONFIG, "w", encoding="utf-8") as f:
            json.dump({"voice": vid}, f, ensure_ascii=False)


def _is_single_mora(text):
    return len(text) == 1 or (len(text) == 2 and text[-1] in "ゃゅょぁぃぅぇぉャュョァィゥェォ")


def _engine_synth(eng, speaker, text, speed):
    """엔진 하나로 합성 (캐시 우선, 엔진 죽어 있어도 캐시는 서빙). 실패 시 None."""
    h = hashlib.md5(f"{eng['name']}:{speaker}:{speed}:{text}".encode("utf-8")).hexdigest()
    path = os.path.join(TTS_CACHE, h + ".wav")
    if os.path.exists(path):
        return path
    if not _engine_alive(eng["url"]):
        return None
    try:
        # 타임아웃을 넉넉히: 엔진이 바쁠 때 기다리지 않고 다른 성우로 넘어가면
        # 목소리가 뒤섞인 캐시가 영구히 남는다 (2026-07-18 사고 원인)
        req = urllib.request.Request(
            f"{eng['url']}/audio_query?speaker={speaker}&text=" + urllib.parse.quote(text),
            method="POST")
        query = json.loads(urllib.request.urlopen(req, timeout=90).read())
        query["speedScale"] = speed
        req2 = urllib.request.Request(
            f"{eng['url']}/synthesis?speaker={speaker}",
            data=json.dumps(query).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        wav = urllib.request.urlopen(req2, timeout=120).read()
        os.makedirs(TTS_CACHE, exist_ok=True)
        with open(path, "wb") as f:
            f.write(wav)
        return path
    except Exception:
        return None


def local_tts_path(text, slow=False, voice=None, speed=None):
    """로컬 성우 합성. voice="engine:styleId"면 그 성우로 전부(한 글자 포함),
    없으면 기본 체인(AivisSpeech まお → VOICEVOX). 롤플레이는 요청마다 voice를 넘겨 역할별 성우 사용.
    speed를 명시하면 그 배속을 그대로 쓴다(노래 가사 낭독은 1.0 — 학습자 요청 2026-07-18)."""
    def _spd(is_slow):
        return speed if speed is not None else (TTS_SPEED_SLOW if is_slow else TTS_SPEED)
    if voice:
        name, _, spk = voice.partition(":")
        eng = next((e for e in LOCAL_TTS if e["name"] == name), None)
        if not (eng and spk.lstrip("-").isdigit()):
            return None
        if _is_single_mora(text):
            mora_speed = speed if speed is not None else TTS_SPEED_MORA  # 한 글자는 또박또박
            return _engine_synth(eng, int(spk), text + "。", mora_speed)
        return _engine_synth(eng, int(spk), text, _spd(slow))
    # 기본 체인: "살아있는 첫 엔진 하나"만 쓴다. 실패했다고 다른 엔진(=다른 목소리)로
    # 넘어가면 단어마다 성우가 섞인다 — 절대 금지 (2026-07-18 사고)
    for eng in LOCAL_TTS:
        if _engine_alive(eng["url"]):
            return _engine_synth(eng, eng["speaker"], text, _spd(slow))
    return None


_kana_prewarm_gen = [0]


def prewarm_kana_for_voice(vid):
    """성우 전환 직후 한 글자 클립 전체를 새 성우로 미리 합성 (학습표 클릭 즉시 재생용).
    최신 전환만 유효(세대 토큰) + 합성 사이 간격을 둬서 학습자 클릭이 끼어들 자리를 남긴다."""
    _kana_prewarm_gen[0] += 1
    my_gen = _kana_prewarm_gen[0]
    try:
        kanas = [os.path.splitext(f)[0] for f in os.listdir(AUDIO_KANA) if f.endswith(".mp3")]
    except OSError:
        return
    for k in kanas:
        if _kana_prewarm_gen[0] != my_gen:
            return  # 그 사이 다른 성우로 또 바꿈 → 이 예열은 중단
        local_tts_path(k, voice=vid)
        time.sleep(0.25)  # 학습자 요청이 끼어들 틈


def list_tts_voices():
    """설정 서랍용 성우 목록 — 웹 레퍼런스로 엄선한 VOICE_MENU만 노출 (한국어 라벨·설명)."""
    cur = _get_voice() or "default"
    edge_ok = _load_edge_tts()
    out = []
    for v in VOICE_MENU:
        if v["id"] != "default":
            name, _, _spk = v["id"].partition(":")
            if name == "edge":
                if not edge_ok:
                    continue  # 인터넷/미설치로 edge 불가면 숨김
            else:
                eng = next((e for e in LOCAL_TTS if e["name"] == name), None)
                if not eng or not _engine_alive(eng["url"]):
                    continue  # 엔진이 죽어 있으면 그 성우는 숨김 (골랐다 소리 안 나는 사고 방지)
        out.append({**v, "current": cur == v["id"]})
    return out


def _speed_to_edge_rate(speed):
    """배속(1.0=보통)을 edge-tts rate 문자열로. 0.8→-20%, 0.6→-40%."""
    return f"{round((speed - 1.0) * 100):+d}%"


def edge_tts_path(text, voice_name=None, slow=False, speed=None):
    """Microsoft 뉴럴 음성(edge-tts)으로 합성해 mp3 반환. voice_name 지정(나나미/케이타 등). 캐시 우선."""
    if not _load_edge_tts():
        return None
    voice_name = voice_name or TTS_VOICE
    # 단독 가나는 감탄사("え？")처럼 읽혀 억양이 이상 → 마침표로 평서문 억양 강제
    say = text + "。" if len(text) <= 2 else text
    if speed is not None:
        spd = speed
    elif _is_single_mora(text):
        spd = TTS_SPEED_MORA
    else:
        spd = TTS_SPEED_SLOW if slow else TTS_SPEED
    rate = _speed_to_edge_rate(spd)
    h = hashlib.md5(f"{voice_name}:{rate}:{say}".encode("utf-8")).hexdigest()
    path = os.path.join(TTS_CACHE, h + ".mp3")
    if not os.path.exists(path):
        os.makedirs(TTS_CACHE, exist_ok=True)
        async def _gen():
            await edge_tts.Communicate(say, voice_name, rate=rate).save(path)
        try:
            asyncio.run(_gen())
        except Exception:
            if os.path.exists(path):
                os.remove(path)
            return None
    return path


def tts_mp3_path(text, slow=False, speed=None):
    """기본 폴백: 나나미 edge 음성."""
    return edge_tts_path(text, TTS_VOICE, slow, speed)


def compute_stats():
    """세션 로그를 집계해 대시보드용 통계를 만든다."""
    days = {}  # 날짜 -> [전체, 정답, ms합, ms개수]
    with _lock:
        try:
            with open(LOG_FILE, encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    d = e["ts"][:10]
                    days.setdefault(d, [0, 0, 0, 0])
                    days[d][0] += 1
                    days[d][1] += 1 if e["correct"] else 0
                    ms = e.get("ms")
                    if isinstance(ms, int) and 0 < ms < 30000:
                        days[d][2] += ms
                        days[d][3] += 1
        except FileNotFoundError:
            pass
        state = _read_json(STATE_FILE, {})

    today = datetime.now().strftime("%Y-%m-%d")
    streak = 0
    cur = datetime.now()
    while cur.strftime("%Y-%m-%d") in days:
        streak += 1
        cur -= timedelta(days=1)

    weak = sorted(
        ({"key": k, **v} for k, v in state.items() if v.get("wrong", 0) > 0),
        key=lambda s: (s["wrong"] - s["right"], s["wrong"]), reverse=True,
    )[:10]

    t = days.get(today, [0, 0, 0, 0])
    day_list = [
        {"date": d, "count": v[0], "correct": v[1],
         "avgMs": round(v[2] / v[3]) if v[3] else None}
        for d, v in sorted(days.items(), reverse=True)
    ]
    return {
        "today": {"count": t[0], "correct": t[1]},
        "totalAnswers": sum(v[0] for v in days.values()),
        "activeDays": len(days),
        "streak": streak,
        "weak": weak,
        "days": day_list,
    }


# 깔끔한 URL 라우팅: /sheet?day=2 처럼 .html 없이 접근 (기존 .html 경로도 계속 동작)
CLEAN_ROUTES = {
    "/sheet": "/sheet.html",
    "/sheets": "/sheets.html",
    "/chart": "/chart.html",
    "/browse": "/browse.html",
    "/custom": "/custom.html",
    "/songs": "/songs.html",
    "/helper": "/helper.html",
    "/history": "/history.html",
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def log_message(self, fmt, *args):  # 콘솔 소음 줄이기
        pass

    def end_headers(self):
        # 정적 파일은 항상 최신으로 (브라우저 캐시 때문에 UI 갱신이 안 보이는 문제 방지)
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urllib.parse.urlparse(self.path).path
        if route in CLEAN_ROUTES:
            query = urllib.parse.urlparse(self.path).query
            self.path = CLEAN_ROUTES[route] + (("?" + query) if query else "")
        if self.path == "/api/decks":
            decks = []
            if os.path.isdir(DECKS):
                for name in sorted(os.listdir(DECKS)):
                    if not name.endswith(".json"):
                        continue
                    d = _read_json(os.path.join(DECKS, name), None)
                    if d:
                        decks.append({"id": d["id"], "title": d.get("title", d["id"]),
                                      "description": d.get("description", ""),
                                      "count": len(d.get("items", []))})
            return self._send_json(decks)
        if self.path.startswith("/api/deck/"):
            deck_id = os.path.basename(self.path[len("/api/deck/"):])
            d = _read_json(os.path.join(DECKS, deck_id + ".json"), None)
            return self._send_json(d if d else {"error": "not found"}, 200 if d else 404)
        if self.path == "/api/state":
            return self._send_json(_read_json(STATE_FILE, {}))
        if self.path == "/api/sets":
            return self._send_json(_read_json(SETS_FILE, []))
        if self.path == "/api/sets/archive":
            return self._send_json(_read_json(SETS_ARCHIVE_FILE, []))
        if self.path == "/api/songs":
            return self._send_json(_read_json(SONGS_FILE, []))
        if self.path.startswith("/api/lyrics-fetch"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            url = (q.get("url") or [""])[0].strip()
            if not url.startswith("https://utaten.com/"):
                return self._send_json({"error": "우타텐(https://utaten.com/) 주소만 지원 (필요하면 확장)"}, 400)
            try:
                text, html = fetch_lyrics_page(url)
            except Exception as e:
                return self._send_json({"error": f"페이지 가져오기 실패: {e}"}, 502)
            if not text:
                if "debug" in q:
                    import re as _re
                    classes = sorted(set(_re.findall(r'<div[^>]+class="([^"]*)"', html)))[:40]
                    return self._send_json({"error": "가사 영역을 못 찾음", "divClasses": classes}, 404)
                return self._send_json({"error": "가사 영역을 못 찾음 — 튜터에게 알려주면 파서를 고친다"}, 404)
            return self._send_json({"url": url, "text": text})
        if self.path.startswith("/api/video-text/status"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            vid = (q.get("videoId") or [""])[0]
            done_file = os.path.exists(os.path.join(VIDEO_TEXT_DIR, vid + ".json"))
            status = "done" if done_file else _video_jobs.get(vid, "none")
            return self._send_json({"videoId": vid, "status": status})
        if self.path.startswith("/api/video-text"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            vid = (q.get("videoId") or [""])[0]
            try:
                start = float((q.get("start") or ["0"])[0])
                end = float((q.get("end") or ["999999"])[0])
            except ValueError:
                return self._send_json({"error": "start/end는 숫자"}, 400)
            segs = get_valid_text_from_start_to_end(vid, start, end)
            if segs is None:
                return self._send_json({"error": "아직 추출 안 됨"}, 404)
            return self._send_json({"videoId": vid, "segments": segs})
        if self.path == "/api/ocr-result":
            # 학습자가 OCR 도구로 추출해둔 텍스트 파일을 앱 화면으로 불러온다
            ocr_path = os.path.join(BASE, "ocr-result.txt")
            if not os.path.exists(ocr_path):
                return self._send_json({"error": "ocr-result.txt 없음 — 먼저 python tools/ocr_capture.py 실행"}, 404)
            with open(ocr_path, encoding="utf-8") as f:
                return self._send_json({"text": f.read()})
        if self.path == "/api/stats":
            return self._send_json(compute_stats())
        if self.path == "/api/tts-voices":
            return self._send_json(list_tts_voices())
        if self.path.startswith("/api/tts"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            text = (q.get("text") or [""])[0].strip()
            slow = (q.get("slow") or ["0"])[0] == "1"
            if not text or len(text) > 200:
                return self._send_json({"error": "text 필요 (200자 이내)"}, 400)
            # 배속 명시(노래 가사 낭독=1.0 등). 없으면 slow/기본 규칙대로
            try:
                speed = float((q.get("speed") or ["0"])[0])
                speed = min(2.0, max(0.5, speed)) if speed > 0 else None
            except ValueError:
                speed = None
            # 성우: 요청 지정(voice=, 미리듣기·롤플레이) > 학습자 설정 > 기본 조합
            voice = (q.get("voice") or [None])[0] or _get_voice()
            if voice == "default":
                voice = None
            # 한 글자·요음은 어떤 성우든 실제 원어민 녹음이 가장 깨끗 → 항상 우선 (합성 단일모음 억양 문제 회피)
            native = kana_audio_path(text)
            if native:
                path = native
            elif voice and voice.startswith("edge:"):  # Microsoft 뉴럴 (나나미/케이타)
                path = edge_tts_path(text, voice.split(":", 1)[1], slow, speed) or tts_mp3_path(text, slow, speed)
            elif voice:  # 로컬 엔진 성우(보이스복스/아비스). 엔진 죽어도 다른 캐릭터로 바꿔치기 금지
                path = local_tts_path(text, slow, voice, speed) or tts_mp3_path(text, slow, speed)
            else:  # 기본 조합: 나나미(edge) → 로컬 엔진 폴백
                path = edge_tts_path(text, TTS_VOICE, slow, speed) or local_tts_path(text, slow, None, speed)
            if not path:
                return self._send_json({"error": "TTS 사용 불가 (edge-tts 미설치 또는 네트워크 오류)"}, 503)
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav" if path.endswith(".wav") else "audio/mpeg")
            self.send_header("Content-Length", str(len(body)))
            # no-store 필수: 주소에 성우가 안 들어가므로 브라우저가 캐시하면
            # 성우를 바꿔도 옛 목소리가 박제된다 (2026-07-18 사고 — max-age 금지)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/answer":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                return self._send_json(record_answer(payload))
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        if self.path == "/api/tts-voice":
            # 설정 서랍에서 성우 선택 → 저장 (모든 발음에 일괄 적용)
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                vid = (payload.get("voice") or "default").strip()
                _set_voice(vid)
                # 한 글자·요음은 성우와 무관하게 항상 원어민 녹음을 쓰므로 예열 불필요
                return self._send_json({"ok": True, "voice": vid})
            except (ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        if self.path == "/api/songs":
            # 학습자가 노래 탭에서 가사 한 줄을 직접 등록 (붙여넣기)
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                line = (payload.get("line") or "").strip()
                if not line or len(line) > 200:
                    return self._send_json({"error": "가사 한 줄이 필요 (200자 이내)"}, 400)
                with _lock:
                    songs = _read_json(SONGS_FILE, [])
                    entry = {
                        "id": f"s{len(songs) + 1:03d}",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "artist": (payload.get("artist") or "").strip(),
                        "song": (payload.get("song") or "").strip(),
                        "line": line,
                        "analysis": None,  # 튜터가 나중에 채움
                    }
                    songs.insert(0, entry)
                    _write_json(SONGS_FILE, songs)
                return self._send_json(entry)
            except (ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        if self.path == "/api/video-text/extract":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                url = (payload.get("url") or "").strip()
                if not url:
                    return self._send_json({"error": "url 필요"}, 400)
                vid = get_text_from_video(url)
                if not vid:
                    return self._send_json({"error": "유효한 유튜브 URL이 아님"}, 400)
                return self._send_json({"videoId": vid, "status": _video_jobs.get(vid, "started")})
            except (ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        if self.path == "/api/songs/lyric":
            # 학습자가 앱에서 가사(자기가 가져온 텍스트)를 등록
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                lyric = (payload.get("lyric") or "").strip()
                if not lyric or len(lyric) > 1500:
                    return self._send_json({"error": "가사 텍스트 필요 (1500자 이내)"}, 400)
                with _lock:
                    songs = _read_json(SONGS_FILE, [])
                    target = next((s for s in songs if s["id"] == payload.get("id")), None)
                    if not target:
                        return self._send_json({"error": "song not found"}, 404)
                    target["lyric"] = lyric
                    target["lineNotes"] = None  # 가사가 바뀌면 줄별 해설은 다시
                    _write_json(SONGS_FILE, songs)
                return self._send_json({"ok": True})
            except (ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        if self.path == "/api/songs/setup":
            # 원클릭 세팅: 가사 로드 → 등록 → 공식 자막 큐 → 정렬 (학습자 버튼으로 트리거)
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                with _lock:
                    songs = _read_json(SONGS_FILE, [])
                    target = next((x for x in songs if x["id"] == payload.get("id")), None)
                if not target:
                    return self._send_json({"error": "song not found"}, 404)
                if not target.get("lyricUrl") or not target.get("videoId"):
                    return self._send_json({"error": "우타텐 주소/영상이 먼저 등록돼야 함 — 튜터에게 요청"}, 400)
                text, _html = fetch_lyrics_page(target["lyricUrl"])
                if not text:
                    return self._send_json({"error": "가사 페이지 파싱 실패 — 튜터에게 알려줘"}, 502)
                cues, lang = fetch_subtitle_cues(target["videoId"])
                if cues:
                    rows = setup_song_from_cues(target, text, cues, lang)
                    aligned = lang == "ja"
                else:
                    target["lyric"] = text
                    target["lineNotes"] = None
                    rows = len([l for l in text.split("\n") if l.strip()])
                    aligned = False
                with _lock:
                    songs2 = _read_json(SONGS_FILE, [])
                    for i, x in enumerate(songs2):
                        if x["id"] == target["id"]:
                            songs2[i] = target
                    _write_json(SONGS_FILE, songs2)
                return self._send_json({"ok": True, "rows": rows, "subLang": lang,
                                        "aligned": aligned,
                                        "next": "완료" if aligned else "튜터가 해석 작성 후 정렬 예정"})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)
        if self.path == "/api/songs/align":
            # 등록 가사 + 추출 데이터로 줄별 싱크 재계산
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                with _lock:
                    songs = _read_json(SONGS_FILE, [])
                    target = next((x for x in songs if x["id"] == payload.get("id")), None)
                    if not target:
                        return self._send_json({"error": "song not found"}, 404)
                    vdata = _read_json(os.path.join(VIDEO_TEXT_DIR, (target.get("videoId") or "") + ".json"), None)
                    ok = compute_line_times(target, vdata)
                    if ok:
                        _write_json(SONGS_FILE, songs)
                sure = sum(1 for t in (target.get("lineTimes") or []) if t.get("sure"))
                return self._send_json({"ok": ok, "lines": len(target.get("lineTimes") or []), "sure": sure})
            except (ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        if self.path == "/api/songs/update":
            # 노래 반복 구간 저장 (loopStart/loopEnd)
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                with _lock:
                    songs = _read_json(SONGS_FILE, [])
                    target = next((s for s in songs if s["id"] == payload.get("id")), None)
                    if not target:
                        return self._send_json({"error": "song not found"}, 404)
                    si = payload.get("sectionIndex")
                    secs = target.get("sections") or []
                    if isinstance(si, int) and 0 <= si < len(secs):
                        # 선택된 학습 구간의 시간 미세조정 저장
                        if isinstance(payload.get("loopStart"), (int, float)):
                            secs[si]["start"] = payload["loopStart"]
                        if isinstance(payload.get("loopEnd"), (int, float)):
                            secs[si]["end"] = payload["loopEnd"]
                    else:
                        for k in ("loopStart", "loopEnd"):
                            if isinstance(payload.get(k), (int, float)):
                                target[k] = payload[k]
                    _write_json(SONGS_FILE, songs)
                return self._send_json(target)
            except (ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        if self.path == "/api/sets/done":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                with _lock:
                    sets = _read_json(SETS_FILE, [])
                    target = next((s for s in sets if s["id"] == payload["id"]), None)
                    if not target:
                        return self._send_json({"error": "set not found"}, 404)
                    target["done"] = True
                    target["doneAt"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    _write_json(SETS_FILE, sets)
                return self._send_json(target)
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                return self._send_json({"error": str(e)}, 400)
        return self._send_json({"error": "unknown endpoint"}, 404)


def main():
    # 0.0.0.0 바인딩: 같은 네트워크의 폰에서도 접속 가능 (모바일 학습용)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"학습 서버 시작: {url}  (같은 와이파이 기기에서도 접속 가능, 종료: Ctrl+C)", flush=True)
    threading.Thread(target=start_local_tts_engines, daemon=True).start()  # 성우 엔진들 백그라운드 기동
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료.")


if __name__ == "__main__":
    main()
