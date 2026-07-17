// 공통 사이드바 — 모든 페이지에서 <script src="/nav.js"></script> 한 줄로 사용.
// 데스크톱: 왼쪽 고정 사이드바 / 좁은 화면: 하단 탭바 (폰에서 쓰기 좋게)
(function () {
  "use strict";
  // 학습지: 사이드바 → 목록(/sheets), 홈 바로가기 → 상세(/sheet?day=N)
  const ITEMS = [
    ["/", "🏠", "오늘"],
    ["/sheets", "📝", "학습지"],
    ["/chart", "📖", "학습표"],
    ["/browse", "📚", "덱 열람"],
    ["/songs", "🎵", "노래"],
    ["/helper", "🔎", "헬퍼"],
    ["/custom", "⭐", "요청"],
    ["/history", "📊", "기록"],
  ];
  const SUBPAGES = { "/sheets": ["/sheet"] }; // 상세 페이지도 해당 메뉴 활성 처리
  const style = document.createElement("style");
  style.textContent = `
    .sidenav {
      position: fixed; left: 0; top: 0; bottom: 0; width: 128px; z-index: 50;
      background: #181b21; border-right: 1px solid #33373f;
      display: flex; flex-direction: column; gap: 4px; padding-top: 18px;
    }
    .sidenav a {
      display: flex; flex-direction: column; align-items: center; gap: 4px;
      padding: 14px 4px; color: #a4a29a; text-decoration: none; font-size: 14px;
      border-left: 3px solid transparent;
    }
    .sidenav a .ic { font-size: 25px; }
    .sidenav a:hover { color: #eceae4; }
    .sidenav a.on { color: #eceae4; border-left-color: #e5735f; background: #1d2027; }
    body.has-nav { padding-left: 142px; }
    .sidenav .nav-set {
      margin-top: auto; margin-bottom: 10px; background: none; border: none; cursor: pointer;
      display: flex; flex-direction: column; align-items: center; gap: 4px;
      padding: 14px 4px; color: #a4a29a; font-size: 14px; font-family: inherit;
    }
    .sidenav .nav-set .ic { font-size: 25px; }
    .sidenav .nav-set:hover { color: #eceae4; }
    /* 설정 서랍 — 페이지 이동 없이 오른쪽에서 슬라이드 */
    .set-drawer {
      position: fixed; top: 0; right: 0; bottom: 0; width: min(400px, 94vw); z-index: 90;
      background: #181b21; border-left: 1px solid #33373f; padding: 20px 18px;
      transform: translateX(100%); transition: transform .25s ease; overflow-y: auto;
      color: #eceae4; font-family: "Segoe UI", "Malgun Gothic", sans-serif;
    }
    .set-drawer.open { transform: translateX(0); box-shadow: -12px 0 36px rgba(0,0,0,.5); }
    .sd-head { display: flex; align-items: center; justify-content: space-between; font-size: 19px; font-weight: 700; margin-bottom: 16px; }
    .sd-head button { background: #272b34; border: 1px solid #33373f; color: #eceae4; border-radius: 8px; padding: 6px 11px; cursor: pointer; font-size: 14px; }
    .sd-sec { color: #a4a29a; font-size: 14px; margin-bottom: 10px; line-height: 1.6; word-break: keep-all; }
    .sd-voice {
      display: flex; align-items: center; gap: 9px; padding: 10px 10px; margin-bottom: 6px;
      background: #1d2027; border: 1px solid #33373f; border-radius: 10px; cursor: pointer; font-size: 15px;
    }
    .sd-voice:hover { border-color: #e5735f; }
    .sd-voice.cur { border-color: #57c78a; }
    .sd-voice .sd-play {
      background: #272b34; border: 1px solid #33373f; color: #eceae4; border-radius: 8px;
      padding: 7px 10px; cursor: pointer; font-size: 13px; flex-shrink: 0;
    }
    .sd-voice .sd-play:hover { border-color: #e5735f; }
    .sd-voice .sd-name { flex: 1; line-height: 1.4; font-weight: 600; }
    .sd-voice .sd-desc { display: block; color: #a4a29a; font-size: 12.5px; font-weight: 400; margin-top: 2px; line-height: 1.45; word-break: keep-all; }
    .sd-voice .sd-cur { color: #57c78a; font-size: 12.5px; font-weight: 700; flex-shrink: 0; }
    .sd-note { color: #a4a29a; font-size: 13px; margin-top: 12px; line-height: 1.6; word-break: keep-all; }
    .sd-toast { color: #57c78a; font-size: 14px; margin: 10px 0; display: none; }
    @media (max-width: 700px) {
      .sidenav {
        top: auto; bottom: 0; right: 0; width: auto; height: 62px;
        flex-direction: row; justify-content: space-around; padding: 0;
        border-right: none; border-top: 1px solid #33373f;
      }
      /* 9개 항목이 375px 폰에서도 잘리지 않게 촘촘히 */
      .sidenav a { border-left: none; border-top: 3px solid transparent; padding: 7px 3px; font-size: 10.5px; min-width: 0; }
      .sidenav a .ic { font-size: 19px; }
      .sidenav a.on { border-top-color: #e5735f; background: none; }
      .sidenav .nav-set { margin: 0; padding: 7px 3px; font-size: 10.5px; }
      .sidenav .nav-set .ic { font-size: 19px; }
      body.has-nav { padding-left: 12px; padding-bottom: 78px; }
    }
  `;
  document.head.appendChild(style);
  const nav = document.createElement("nav");
  nav.className = "sidenav";
  const path = location.pathname.replace(/\.html$/, ""); // .html 직접 접근도 같은 메뉴로 인식
  nav.innerHTML = ITEMS.map(([href, ic, lb]) => {
    const on = href === "/"
      ? (path === "/" || path === "/index.html")
      : (path === href || (SUBPAGES[href] || []).includes(path));
    return `<a href="${href}" class="${on ? "on" : ""}"><span class="ic">${ic}</span><span class="lb">${lb}</span></a>`;
  }).join("");
  document.body.prepend(nav);
  document.body.classList.add("has-nav");

  // ── 설정 서랍 (⚙): 성우 일괄 변경 — 페이지 이동 없이 오른쪽 슬라이드 ──
  const setBtn = document.createElement("button");
  setBtn.className = "nav-set";
  setBtn.innerHTML = `<span class="ic">⚙</span><span class="lb">설정</span>`;
  nav.appendChild(setBtn);

  const drawer = document.createElement("div");
  drawer.className = "set-drawer";
  drawer.innerHTML = `
    <div class="sd-head">설정 <button id="sdClose">✕ 닫기</button></div>
    <div class="sd-sec"><b style="color:#eceae4">성우 고르기</b> — 한 글자·단어·문장 모든 발음에 한 번에 적용된다.
      ▶로 목소리를 들어보고, 줄을 누르면 선택.</div>
    <div class="sd-toast" id="sdToast"></div>
    <div id="sdVoices" class="sd-sec">불러오는 중...</div>
    <div class="sd-note">성우를 바꾼 직후 처음 듣는 단어는 준비에 2~4초 걸릴 수 있다 (한 번 들으면 그 뒤는 즉시).
      나중에 회화 롤플레이에서는 역할마다 다른 성우가 자동 배정된다.</div>`;
  document.body.appendChild(drawer);

  const SAMPLE = "こんにちは。今日も一緒にがんばりましょう。";
  let sdAudio = null;
  function sdPreview(id) {
    try { if (window.player && window.player.pauseVideo) window.player.pauseVideo(); } catch { /* 노래 탭 외 */ }
    if (sdAudio) { sdAudio.pause(); sdAudio = null; }
    fetch("/api/tts?text=" + encodeURIComponent(SAMPLE) + "&voice=" + encodeURIComponent(id) + "&_v=" + (localStorage.getItem("ttsVer") || "0"))
      .then(r => { if (!r.ok) throw new Error(); return r.blob(); })
      .then(b => { sdAudio = new Audio(URL.createObjectURL(b)); sdAudio.play(); })
      .catch(() => { const t = document.getElementById("sdToast"); t.style.display = "block"; t.textContent = "미리듣기 실패 — 엔진 준비 중일 수 있음"; });
  }
  function sdSelect(id, label) {
    fetch("/api/tts-voice", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ voice: id }) })
      .then(r => { if (!r.ok) throw new Error(); })
      .then(() => {
        (window.__ttsCaches || []).forEach(c => Object.keys(c).forEach(k => delete c[k])); // 이전 성우 소리 캐시 비우기
        localStorage.setItem("ttsVer", String(Date.now())); // 발음 URL 버전 갱신 → 브라우저 HTTP 캐시 무효화
        const t = document.getElementById("sdToast");
        t.style.display = "block"; t.textContent = "적용 완료 — 이제 모든 발음이 「" + label + "」 목소리다.";
        sdLoad();
      })
      .catch(() => alert("저장 실패 — 서버 상태 확인 필요."));
  }
  function sdLoad() {
    fetch("/api/tts-voices").then(r => r.json()).then(list => {
      const box = document.getElementById("sdVoices");
      box.className = "";
      box.innerHTML = "";
      list.forEach(v => {
        const row = document.createElement("div");
        row.className = "sd-voice" + (v.current ? " cur" : "");
        row.innerHTML = `<button class="sd-play" title="들어보기">▶</button>` +
          `<span class="sd-name">${v.label}${v.desc ? `<span class="sd-desc">${v.desc}</span>` : ""}</span>` +
          (v.current ? `<span class="sd-cur">사용 중</span>` : "");
        row.querySelector(".sd-play").onclick = e => { e.stopPropagation(); sdPreview(v.id); };
        row.onclick = () => { if (!v.current) sdSelect(v.id, v.label); };
        box.appendChild(row);
      });
    }).catch(() => { document.getElementById("sdVoices").textContent = "목록을 못 불러왔다 — 서버 확인 필요."; });
  }
  setBtn.onclick = () => {
    const opening = !drawer.classList.contains("open");
    drawer.classList.toggle("open", opening);
    if (opening) { document.getElementById("sdToast").style.display = "none"; sdLoad(); }
  };
  drawer.addEventListener("click", e => { if (e.target.id === "sdClose") drawer.classList.remove("open"); });
})();
