<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { page } from '$app/state';
	import { speak, stopSpeak } from '$lib/audio';

	type Note = { t?: string; n?: string; h?: string; r?: string; d?: string; cont?: boolean };
	type Time = { start: number; end: number };
	type Song = { id: string; song: string; artist: string; videoId: string; lyric?: string; pastedLyric?: string; lineNotes?: Note[]; lineTimes?: Time[]; date?: string };

	let songs = $state<Song[]>([]);
	let cur = $state<Song | null>(null);
	let lines = $state<string[]>([]);
	let nowIdx = $state(-1);
	let detailIdx = $state<number | null>(null);
	let rowLoopOn = $state(false);
	let apiFailed = $state(false);

	// 탭 싱크 (admin 전용)
	let isAdmin = $state(false);
	let syncMode = $state(false);
	let syncTimes = $state<number[]>([]);
	let syncPos = $state(0);
	let syncMsg = $state('');
	let syncSaving = $state(false);

	let player: any = null;
	let ytReady = false;
	let timer: any = null;
	let lineEls: HTMLElement[] = [];

	// 레거시 이식: 상세 패널을 더블클릭한 행 옆에 붙이기 위한 참조/오프셋
	let layoutEl = $state<HTMLElement | undefined>();
	let panelEl = $state<HTMLElement | undefined>();
	let panelTop = $state(0);
	let panelRight = $state(0);

	// 재생 제어 내부 상태 (템플릿에서 안 읽으므로 일반 변수)
	let rowLoopStart = 0, rowLoopEnd = 0;
	let vocalStopAt: number | null = null;
	let manualHiIdx = -1, manualHiUntil = 0;
	let lastUserScroll = 0;
	let clickTimer: any = null;

	const HIGHLIGHT_LAG = 0.6;
	const readingOf = (s: string) => (s || '')
		.replace(/[一-龥々〆ヶ]+（([^（）]+)）/g, '$1').replace(/（[^）]*）/g, '');
	const watchUrl = (s: Song | null) => s ? `https://www.youtube.com/watch?v=${s.videoId}` : '#';
	const fmt = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;

	// 상세 패널: 더블클릭한 행 옆 높이에 fixed로 고정. 절대조건 = 패널 전체가 화면 안에 보일 것.
	// (본문이 좁아지며 리플로우가 커도 fixed는 뷰포트 기준이라 흔들리지 않는다)
	function positionPanel() {
		if (detailIdx === null || !layoutEl || !panelEl) return;
		if (window.innerWidth <= 1200) { panelTop = 0; panelRight = 0; return; } // 좁으면 CSS가 오른쪽 전체 오버레이
		const layoutRect = layoutEl.getBoundingClientRect();
		panelRight = Math.max(8, Math.round(window.innerWidth - layoutRect.right)); // 레이아웃 오른쪽 끝에 도킹
		const rowEl = lineEls[detailIdx];
		const panelH = panelEl.offsetHeight;
		let top = 14;
		if (rowEl) {
			top = rowEl.getBoundingClientRect().top - 6;             // 행 높이
			top = Math.min(top, window.innerHeight - panelH - 14);   // 아래로 잘리면 위로 당김
			top = Math.max(top, 14);                                 // 위로도 안 잘리게
		}
		panelTop = Math.round(top);
	}
	const onResize = () => positionPanel();

	onMount(async () => {
		songs = await fetch('/api/songs').then((r) => (r.ok ? r.json() : { songs: [] })).then((d) => d.songs || []);
		fetch('/api/me').then((r) => (r.ok ? r.json() : null)).then((d) => { isAdmin = d?.username === 'admin'; }).catch(() => {});
		window.addEventListener('keydown', onKey);
		(window as any).onYouTubeIframeAPIReady = () => { ytReady = true; if (cur) mount(cur); };
		if (!(window as any).YT) {
			const s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api';
			s.onerror = () => { apiFailed = true; };
			document.head.appendChild(s);
			setTimeout(() => { if (!ytReady) apiFailed = true; }, 6000);
		} else { ytReady = true; }

		const wantId = page.url.searchParams.get('id');
		const first = (wantId && songs.find((s) => s.id === wantId)) || songs.find((s) => s.lyric || s.pastedLyric) || songs[0];
		if (first) select(first);

		const onScroll = () => { lastUserScroll = Date.now(); };
		window.addEventListener('wheel', onScroll, { passive: true });
		window.addEventListener('touchmove', onScroll, { passive: true });
		window.addEventListener('resize', onResize);

		timer = setInterval(() => {
			if (!player?.getCurrentTime) return;
			try {
				const t = player.getCurrentTime();
				const times = cur?.lineTimes;
				if (times && times.length) {
					let idx = -1;
					const tt = t - HIGHLIGHT_LAG;
					for (let k = 0; k < times.length; k++) {
						const tm = times[k];
						if (tm && tt >= tm.start - 0.2 && tt < tm.end + 0.3) { idx = k; break; }
					}
					if (Date.now() < manualHiUntil && manualHiIdx >= 0) idx = manualHiIdx;
					if (idx !== nowIdx) {
						nowIdx = idx;
						if (idx >= 0 && lineEls[idx] && Date.now() - lastUserScroll > 4000) {
							lineEls[idx].scrollIntoView({ block: 'center', behavior: 'smooth' });
						}
					}
				}
				if (rowLoopOn && t >= rowLoopEnd) { player.seekTo(Math.max(0, rowLoopStart - 0.2), true); return; }
				if (vocalStopAt !== null && t >= vocalStopAt) { player.pauseVideo(); vocalStopAt = null; }
			} catch { /* 준비 전 */ }
		}, 250);
	});
	onDestroy(() => { if (timer) clearInterval(timer); window.removeEventListener('resize', onResize); window.removeEventListener('keydown', onKey); });

	// ── 탭 싱크: 재생하며 각 소절 첫 소리에 탭(Space/클릭) → lineTimes 생성 (admin) ──
	function onKey(e: KeyboardEvent) {
		if (syncMode && (e.code === 'Space' || e.key === ' ')) { e.preventDefault(); tapSync(); }
	}
	function startSync() {
		if (!cur || !lines.length) return;
		detailIdx = null; rowLoopOn = false; vocalStopAt = null;
		syncMode = true; syncTimes = []; syncPos = 0; syncMsg = '';
		player?.seekTo?.(0, true);
		player?.playVideo?.();
	}
	function tapSync() {
		if (!syncMode || syncPos >= lines.length) return;
		const t = player?.getCurrentTime?.();
		if (typeof t !== 'number') return;
		syncTimes = [...syncTimes.slice(0, syncPos), t];
		syncPos += 1;
		lineEls[Math.min(syncPos, lines.length - 1)]?.scrollIntoView({ block: 'center' });
		if (syncPos >= lines.length) player?.pauseVideo?.();
	}
	function undoSync() {
		if (syncPos <= 0) return;
		syncPos -= 1;
		syncTimes = syncTimes.slice(0, syncPos);
		lineEls[syncPos]?.scrollIntoView({ block: 'center' });
	}
	function cancelSync() { syncMode = false; syncTimes = []; syncPos = 0; syncMsg = ''; player?.pauseVideo?.(); }
	async function saveSync() {
		if (!cur || syncPos < 1) { syncMsg = '소절을 먼저 탭해줘.'; return; }
		syncSaving = true; syncMsg = '';
		const times = [];
		for (let i = 0; i < syncPos; i++) {                 // 탭한 데까지만(0..syncPos-1) — 줄 인덱스와 정렬 유지
			const start = syncTimes[i];
			let end = syncTimes[i + 1];
			if (typeof end !== 'number' || end <= start) end = start + 5;
			times.push({ start: Math.max(0, start), end });
		}
		try {
			const r = await fetch('/api/songs/times', {
				method: 'POST', headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ id: cur.id, times })
			});
			const d = await r.json();
			if (d.ok) {
				const id = cur.id;
				songs = await fetch('/api/songs').then((x) => (x.ok ? x.json() : { songs: [] })).then((x) => x.songs || []);
				syncMode = false;
				const again = songs.find((x) => x.id === id);
				if (again) select(again);
				syncMsg = `✅ ${d.count}개 소절 싱크 저장! 이제 줄 클릭하면 그 소절부터 재생된다.`;
			} else { syncMsg = `❌ ${d.error || '저장 실패'}`; }
		} catch { syncMsg = '❌ 연결 오류'; }
		syncSaving = false;
	}

	function mount(s: Song) {
		if (!ytReady || !(window as any).YT?.Player) return;
		if (player) { player.cueVideoById({ videoId: s.videoId }); return; }
		player = new (window as any).YT.Player('yt', { videoId: s.videoId, playerVars: { rel: 0, playsinline: 1 } });
	}

	function select(s: Song) {
		cur = s; detailIdx = null; nowIdx = -1; rowLoopOn = false; vocalStopAt = null;
		manualHiIdx = -1; lineEls = [];
		// 해설 가사(lyric)가 있으면 그걸, 없으면 admin이 붙여넣은/불러온 원문(pastedLyric)을 표시
		const text = s.lyric || s.pastedLyric || '';
		lines = text.split(/\n+/).map((x) => x.trim()).filter(Boolean);
		mount(s);
	}

	function markManual(i: number) {
		manualHiIdx = i; manualHiUntil = Date.now() + 1800; nowIdx = i;
	}

	// 클릭: 그 소절부터 이어재생 (이후 개입 없음)
	function seekPlay(i: number) {
		const t = cur?.lineTimes?.[i];
		if (!t || !player?.seekTo) return;
		stopSpeak(); vocalStopAt = null;
		if (rowLoopOn) { rowLoopOn = false; }
		markManual(i);
		player.seekTo(Math.max(0, t.start - 0.2), true);
		player.playVideo?.();
	}

	// 더블클릭/한번듣기: 딱 이 소절만 재생하고 정지
	function playVocal(i: number) {
		const t = cur?.lineTimes?.[i];
		if (!t || !player?.seekTo) return;
		stopSpeak();
		rowLoopOn = false;
		vocalStopAt = t.end + 0.3;
		markManual(i);
		player.seekTo(Math.max(0, t.start - 0.2), true);
		player.playVideo?.();
	}

	function onLineClick(i: number) {
		if (syncMode) { tapSync(); return; }               // 싱크 중엔 클릭=탭
		if (!cur?.lineTimes?.[i]) return;
		if (clickTimer) clearTimeout(clickTimer);
		clickTimer = setTimeout(() => { clickTimer = null; seekPlay(i); }, 260);
	}
	function onLineDbl(i: number) {
		if (syncMode) return;
		if (!cur?.lineTimes?.[i]) return;
		if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; }
		openDetail(i);
	}

	async function openDetail(i: number) {
		if (detailIdx === i) { closeDetail(); return; }
		detailIdx = i;
		rowLoopOn = false;
		await tick();                                       // .panel-open 반영(본문 리플로우) 후
		lineEls[i]?.scrollIntoView({ block: 'center' });    // 그 행을 화면 안으로
		positionPanel();                                    // 패널을 그 행 높이에 고정
		const t = cur?.lineTimes?.[i];
		if (t) { rowLoopStart = t.start; rowLoopEnd = t.end; playVocal(i); }
	}
	function closeDetail() { detailIdx = null; rowLoopOn = false; }

	function toggleRowLoop() {
		rowLoopOn = !rowLoopOn;
		if (rowLoopOn) {
			stopSpeak(); vocalStopAt = null;
			if (detailIdx != null) { manualHiIdx = detailIdx; manualHiUntil = Date.now() + 3000; }
			player?.seekTo?.(Math.max(0, rowLoopStart - 0.2), true);
			player?.playVideo?.();
		} else {
			player?.pauseVideo?.();
		}
	}

	// 느리게 발음: 영상 멈추고 발음 → 끝나면 원래 재생 중이었으면 이어재생
	function slowSpeak(i: number) {
		const line = lines[i]; if (!line) return;
		const wasPlaying = player?.getPlayerState?.() === 1;
		if (wasPlaying) player.pauseVideo();
		speak(readingOf(line), { slow: true, onEnd: () => { if (wasPlaying) player?.playVideo?.(); } });
	}

	const detailNote = $derived(detailIdx != null ? (cur?.lineNotes || [])[detailIdx] || {} : {});
</script>

<svelte:head><title>노래로 공부</title></svelte:head>

<div class="songpage">
	<h1 class="page-title">노래로 공부 🎵</h1>
	<p class="page-sub">클릭 = 그 소절부터 이어 재생 · 더블클릭 = 오른쪽에 상세 해설(반복 포함).</p>

	<div class="layout" class:panel-open={detailIdx !== null} bind:this={layoutEl}>
		<!-- 왼쪽: 곡 목록 (스크롤 내려도 붙어 있음) -->
		<div class="songs-col">
			<div class="col-label">곡 목록</div>
			<div class="list">
				{#each songs as s (s.id)}
					<button class="song-pick" class:on={cur?.id === s.id} onclick={() => select(s)}>
						<span class="sp-t">{s.song}</span><span class="sp-a">{s.artist}</span>
					</button>
				{/each}
			</div>
		</div>

		<!-- 가운데: 플레이어 + 가사 -->
		<div class="main-col">
			{#if cur}
				<div class="player"><div id="yt"></div></div>
				<div class="phint">
					<span>▶ 재생 후 <b>가사 줄 클릭</b> = 그 지점부터 · <b>더블클릭</b> = 오른쪽 상세 + 그 소절</span>
					<a class="ytlink" href={watchUrl(cur)} target="_blank" rel="noopener">유튜브에서 열기 ↗</a>
				</div>
				{#if apiFailed}
					<div class="fallback">플레이어가 안 뜨면(광고 차단·네트워크) 위 <b>유튜브에서 열기</b>로. 가사 해설은 여기서 계속 볼 수 있어.</div>
				{/if}

				{#if isAdmin && lines.length}
					{#if syncMode}
						<div class="syncbar">
							<div class="sync-h">🎯 탭 싱크 <span class="sync-prog">{syncPos} / {lines.length}</span></div>
							<div class="sync-now">지금 소절: <b>{syncPos < lines.length ? lines[syncPos] : '끝까지 완료!'}</b></div>
							<div class="sync-btns">
								<button class="sbtn accent" onclick={tapSync} disabled={syncPos >= lines.length}>👆 탭 (Space)</button>
								<button class="sbtn" onclick={undoSync} disabled={syncPos <= 0}>↩ 되돌리기</button>
								<button class="sbtn ok" onclick={saveSync} disabled={syncPos < 1 || syncSaving}>{syncSaving ? '저장 중…' : '💾 저장'}</button>
								<button class="sbtn" onclick={cancelSync}>✕ 취소</button>
							</div>
							<div class="sync-tip">영상 재생 중, 각 소절 <b>첫 소리</b>에 탭/Space (가사 줄을 눌러도 됨). 틀리면 되돌리기.</div>
							{#if syncMsg}<div class="sync-msg">{syncMsg}</div>{/if}
						</div>
					{:else}
						<div class="syncrow">
							<button class="syncstart" onclick={startSync}>🎯 탭으로 싱크 만들기{cur.lineTimes?.length ? ' (다시)' : ''}</button>
							{#if syncMsg}<span class="sync-msg ok">{syncMsg}</span>{/if}
						</div>
					{/if}
				{/if}

				{#if lines.length}
					<div class="lyrics">
						{#each lines as l, i (i)}
							{@const n = (cur.lineNotes || [])[i]}
							{@const hasTime = !!cur.lineTimes?.[i]}
							<div class="line" class:now={nowIdx === i} class:seekable={hasTime || syncMode} class:tapnow={syncMode && syncPos === i} bind:this={lineEls[i]}>
								<button class="jp" ondblclick={() => onLineDbl(i)} onclick={() => onLineClick(i)}
									title={syncMode ? '탭: 이 소절 타이밍 기록' : (hasTime ? '클릭: 여기부터 · 더블클릭: 이 소절만' : '')}>
									{@html (n?.h) || l}{#if n?.cont}<span class="cont">→</span>{/if}
								</button>
								{#if n?.t}<div class="tr">{n.t}</div>{/if}
								{#if n?.n}<div class="nt">{n.n}</div>{/if}
								{#if !n}<div class="nt dim">⏳ 해설 대기</div>{/if}
							</div>
						{/each}
					</div>
				{:else}
					<p class="page-sub" style="margin-top:16px">이 곡은 아직 가사가 없어. (헬퍼에서 우타텐 불러오기 / 붙여넣기)</p>
				{/if}
			{:else}
				<p class="page-sub">왼쪽에서 곡을 골라줘.</p>
			{/if}
		</div>

		<!-- 오른쪽: 더블클릭한 행 옆에 붙는 상세 패널 -->
		{#if detailIdx !== null && cur}
			<aside class="dpanel" bind:this={panelEl} style="top:{panelTop}px; right:{panelRight}px">
				<button class="dclose" onclick={closeDetail}>✕ 닫기</button>
				<div class="col-label">소절 상세 {#if cur.lineTimes?.[detailIdx]}<span class="dt">{fmt(cur.lineTimes[detailIdx].start)}~</span>{/if}</div>
				<div class="djp">{@html detailNote.h || lines[detailIdx]}</div>
				{#if !detailNote.h && detailNote.r}<div class="drom">{detailNote.r}</div>{/if}
				{#if detailNote.t}<div class="dtr">{detailNote.t}</div>{/if}
				<div class="dbtns">
					<button class="dbtn" class:on={rowLoopOn} onclick={toggleRowLoop} disabled={!cur.lineTimes?.[detailIdx]}>{rowLoopOn ? '⏹ 반복 끄기' : '🔁 이 소절 반복'}</button>
					<button class="dbtn" onclick={() => playVocal(detailIdx!)} disabled={!cur.lineTimes?.[detailIdx]}>▶ 한 번 듣기</button>
					<button class="dbtn" onclick={() => slowSpeak(detailIdx!)}>🗣 느리게 발음</button>
				</div>
				<div class="dbody">{@html detailNote.d || (detailNote.n ? `<div>${detailNote.n}</div>` : '더 깊은 해설은 데스크탑에서 추가.')}</div>
			</aside>
		{/if}
	</div>
</div>

<style>
	.songpage { max-width: 1520px; margin: 0 auto; padding: 28px 18px 90px; }

	/* 본문 그리드: 곡 목록 | 본문 | (상세 열리면) 상세 패널 */
	.layout { position: relative; display: grid; grid-template-columns: 200px minmax(0, 900px); gap: 14px; align-items: start; margin-top: 16px; }
	.layout.panel-open { grid-template-columns: 200px minmax(0, 1fr) 420px; }

	.songs-col { position: sticky; top: 12px; }
	.col-label { color: var(--sub); font-size: 13px; font-weight: 700; margin-bottom: 8px; }
	.list { display: flex; flex-direction: column; gap: 8px; }
	.song-pick { display: block; width: 100%; text-align: left; padding: 12px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; color: var(--text); cursor: pointer; }
	.song-pick:hover { border-color: var(--accent); }
	.song-pick.on { border-color: var(--accent); background: var(--btn); }
	.song-pick .sp-t { display: block; font-weight: 700; font-size: 16px; word-break: keep-all; }
	.song-pick .sp-a { color: var(--sub); font-size: 12.5px; }

	.main-col { min-width: 0; }
	.player { position: relative; width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 10px; overflow: hidden; margin-bottom: 10px; }
	.player :global(iframe) { position: absolute; inset: 0; width: 100%; height: 100%; }
	.phint { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin: -2px 0 14px; color: var(--sub); font-size: 13.5px; }
	.phint b { color: var(--text); }
	.ytlink { flex-shrink: 0; padding: 8px 13px; border: 1px solid var(--border); border-radius: 8px; background: var(--btn); color: var(--accent); font-weight: 600; font-size: 13px; }
	.ytlink:hover { border-color: var(--accent); }
	.fallback { background: var(--accent-soft); border: 1px solid var(--accent); border-radius: 10px; padding: 11px 14px; font-size: 14px; margin-bottom: 14px; }
	.fallback b { color: var(--accent); }
	.lyrics { border-top: 1px solid var(--border); padding-top: 12px; }
	.line { margin-bottom: 10px; padding: 7px 10px; border-radius: 10px; border-left: 3px solid transparent; }
	.line.now { background: var(--btn); border-left-color: var(--accent); }
	.line:hover { background: rgba(255,255,255,.045); }
	.jp { display: block; width: 100%; text-align: left; background: none; border: none; color: var(--text); font-family: var(--jp); font-size: 29px; line-height: 1.9; user-select: none; }
	.line.seekable .jp { cursor: pointer; }
	.jp :global(ruby) { white-space: nowrap; }
	.jp :global(rt) { font-size: 13px; color: var(--accent); font-family: "Segoe UI", sans-serif; }
	.cont { color: var(--sub); opacity: .5; font-size: 60%; }
	.tr { font-size: 17px; margin-top: 4px; opacity: .9; }
	.nt { color: var(--sub); font-size: 15px; margin-top: 3px; word-break: keep-all; }
	.nt.dim { opacity: .6; }

	/* 탭 싱크 (admin 전용) */
	.syncrow { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 4px 0 12px; }
	.syncstart { padding: 9px 15px; border: 1px solid var(--accent); border-radius: 9px; background: var(--accent-soft); color: var(--accent); font-weight: 700; font-size: 14px; cursor: pointer; }
	.syncstart:hover { background: var(--accent); color: #fff; }
	.syncbar { background: var(--card); border: 1px solid var(--accent); border-radius: 12px; padding: 14px 16px; margin: 4px 0 14px; position: sticky; top: 8px; z-index: 30; }
	.sync-h { font-size: 15px; font-weight: 800; }
	.sync-prog { color: var(--accent); margin-left: 6px; }
	.sync-now { margin: 6px 0 10px; font-family: var(--jp); font-size: 20px; word-break: keep-all; }
	.sync-now b { color: var(--accent); }
	.sync-btns { display: flex; gap: 8px; flex-wrap: wrap; }
	.sbtn { padding: 10px 14px; border: 1px solid var(--border); border-radius: 9px; background: var(--btn); color: var(--text); font-weight: 700; font-size: 14px; cursor: pointer; }
	.sbtn:hover { border-color: var(--accent); }
	.sbtn.accent { background: var(--accent); border-color: var(--accent); color: #fff; }
	.sbtn.ok { background: var(--ok); border-color: var(--ok); color: #14161b; }
	.sbtn:disabled { opacity: .45; cursor: default; }
	.sync-tip { color: var(--sub); font-size: 12.5px; margin-top: 9px; line-height: 1.5; word-break: keep-all; }
	.sync-msg { font-size: 13.5px; color: var(--accent); word-break: keep-all; }
	.syncbar .sync-msg { margin-top: 8px; }
	.sync-msg.ok { color: var(--ok); }
	.line.tapnow { background: var(--accent-soft); border-left-color: var(--accent); outline: 2px solid var(--accent); }

	/* 상세 패널: 더블클릭한 행 옆(오른쪽)에 fixed로 붙는다. top·right는 JS가 행 높이·레이아웃 끝에 맞춰 계산 */
	.dpanel { position: fixed; top: 0; right: 0; width: 420px; max-height: 84vh; overflow-y: auto; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; transition: top .18s ease; z-index: 55; box-shadow: 0 10px 34px rgba(0,0,0,.42); }
	.dclose { position: absolute; top: 14px; right: 14px; background: var(--btn); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 6px 11px; cursor: pointer; font-size: 14px; }
	.dt { color: var(--accent); }
	.djp { font-family: var(--jp); font-size: 26px; line-height: 1.9; margin: 8px 24px 4px 0; }
	.djp :global(rt) { font-size: 12px; color: var(--accent); }
	.drom { color: var(--accent); font-size: 15px; margin-bottom: 4px; }
	.dtr { font-size: 18px; margin-bottom: 12px; }
	.dbtns { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 14px; }
	.dbtn { padding: 11px 6px; border-radius: 9px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; font-size: 14px; font-weight: 600; }
	.dbtn:hover { border-color: var(--accent); }
	.dbtn.on { background: var(--ok); border-color: var(--ok); color: #14161b; }
	.dbtn:disabled { opacity: .45; cursor: default; }
	.dbody { font-size: 16px; line-height: 1.75; word-break: keep-all; }
	.dbody :global(table) { width: 100%; border-collapse: collapse; margin: 10px 0; }
	.dbody :global(th), .dbody :global(td) { padding: 7px 8px; border-bottom: 1px solid var(--border); text-align: left; font-size: 14.5px; }
	.dbody :global(th) { color: var(--sub); font-size: 13px; }
	.dbody :global(.jp) { font-family: var(--jp); font-size: 18px; }
	.dbody :global(b) { color: var(--accent); }
	.dbody :global(.tr) { margin: 8px 0; }

	/* ≤1200px: 상세 패널을 오른쪽 고정 오버레이로 (행 옆 배치가 좁아서 안 예쁨) */
	@media (max-width: 1200px) {
		.layout.panel-open { grid-template-columns: 200px minmax(0, 1fr); }
		.dpanel { position: fixed !important; top: 0 !important; right: 0; bottom: 0; width: min(430px, 92vw); max-height: none; border-radius: 0; z-index: 70; box-shadow: -10px 0 32px rgba(0,0,0,.55); }
	}
	/* ≤700px: 곡 목록을 상단 가로 스크롤로, 본문 1열 */
	@media (max-width: 700px) {
		.layout, .layout.panel-open { grid-template-columns: minmax(0, 1fr); }
		.songs-col { position: static; }
		.list { flex-direction: row; overflow-x: auto; padding-bottom: 6px; }
		.song-pick { width: auto; min-width: 150px; flex-shrink: 0; }
		.jp { font-size: 25px; }
		.tr { font-size: 16px; }
		.dpanel { width: 100vw; }
	}
</style>
