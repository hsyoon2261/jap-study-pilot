<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { speak, stopSpeak } from '$lib/audio';

	type Note = { t?: string; n?: string; h?: string; d?: string; cont?: boolean };
	type Time = { start: number; end: number };
	type Song = { id: string; song: string; artist: string; videoId: string; lyric?: string; pastedLyric?: string; lineNotes?: Note[]; lineTimes?: Time[]; date?: string };

	let songs = $state<Song[]>([]);
	let cur = $state<Song | null>(null);
	let lines = $state<string[]>([]);
	let nowIdx = $state(-1);
	let detailIdx = $state<number | null>(null);
	let rowLoopOn = $state(false);
	let apiFailed = $state(false);

	let player: any = null;
	let ytReady = false;
	let tick: any = null;
	let lineEls: HTMLElement[] = [];

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

	onMount(async () => {
		songs = await fetch('/api/songs').then((r) => (r.ok ? r.json() : { songs: [] })).then((d) => d.songs || []);
		(window as any).onYouTubeIframeAPIReady = () => { ytReady = true; if (cur) mount(cur); };
		if (!(window as any).YT) {
			const s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api';
			s.onerror = () => { apiFailed = true; };
			document.head.appendChild(s);
			setTimeout(() => { if (!ytReady) apiFailed = true; }, 6000);
		} else { ytReady = true; }

		const wantId = page.url.searchParams.get('id');
		const first = (wantId && songs.find((s) => s.id === wantId)) || songs.find((s) => s.lyric) || songs[0];
		if (first) select(first);

		const onScroll = () => { lastUserScroll = Date.now(); };
		window.addEventListener('wheel', onScroll, { passive: true });
		window.addEventListener('touchmove', onScroll, { passive: true });

		tick = setInterval(() => {
			if (!player?.getCurrentTime) return;
			try {
				const t = player.getCurrentTime();
				const times = cur?.lineTimes;
				// 현재 줄 하이라이트 (보컬 리드 보정 + 방금 클릭한 행 우선)
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
				// 소절 반복
				if (rowLoopOn && t >= rowLoopEnd) { player.seekTo(Math.max(0, rowLoopStart - 0.2), true); return; }
				// 한 소절만 듣기: 끝나면 정지
				if (vocalStopAt !== null && t >= vocalStopAt) { player.pauseVideo(); vocalStopAt = null; }
			} catch { /* 준비 전 */ }
		}, 250);
	});
	onDestroy(() => { if (tick) clearInterval(tick); });

	function mount(s: Song) {
		if (!ytReady || !(window as any).YT?.Player) return;
		if (player) { player.cueVideoById({ videoId: s.videoId }); return; }
		player = new (window as any).YT.Player('yt', { videoId: s.videoId, playerVars: { rel: 0, playsinline: 1 } });
	}

	async function select(s: Song) {
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
		if (!cur?.lineTimes?.[i]) return;
		if (clickTimer) clearTimeout(clickTimer);
		clickTimer = setTimeout(() => { clickTimer = null; seekPlay(i); }, 260);
	}
	function onLineDbl(i: number) {
		if (!cur?.lineTimes?.[i]) return;
		if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; }
		openDetail(i);
	}

	function openDetail(i: number) {
		if (detailIdx === i) { closeDetail(); return; }
		detailIdx = i;
		rowLoopOn = false;
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

<div class="page" class:shift={detailIdx !== null}>
	<h1 class="page-title">노래로 공부 🎵</h1>
	<p class="page-sub">클릭 = 그 소절부터 이어 재생 · 더블클릭 = 상세 + 그 소절만 · 상세에서 🔁 반복.</p>

	<div class="songrow">
		{#each songs as s (s.id)}
			<button class="spick" class:on={cur?.id === s.id} onclick={() => select(s)}>
				<span class="st">{s.song}</span><span class="sa">{s.artist}</span>
			</button>
		{/each}
	</div>

	{#if cur}
		<div class="player"><div id="yt"></div></div>
		<div class="phint">
			<span>▶ 재생 후 <b>가사 줄 클릭</b> = 그 지점부터 · <b>더블클릭</b> = 그 소절만 듣고 정지</span>
			<a class="ytlink" href={watchUrl(cur)} target="_blank" rel="noopener">유튜브에서 열기 ↗</a>
		</div>
		{#if apiFailed}
			<div class="fallback">플레이어가 안 뜨면(광고 차단·네트워크) 위 <b>유튜브에서 열기</b>로. 가사 해설은 여기서 계속 볼 수 있어.</div>
		{/if}

		{#if lines.length}
			<div class="lyrics">
				{#each lines as l, i (i)}
					{@const n = (cur.lineNotes || [])[i]}
					{@const hasTime = !!cur.lineTimes?.[i]}
					<div class="line" class:now={nowIdx === i} class:seekable={hasTime} bind:this={lineEls[i]}>
						<button class="jp" ondblclick={() => onLineDbl(i)} onclick={() => onLineClick(i)}
							title={hasTime ? '클릭: 여기부터 · 더블클릭: 이 소절만' : ''}>
							{@html (n?.h) || l}{#if n?.cont}<span class="cont">→</span>{/if}
						</button>
						{#if n?.t}<div class="tr">{n.t}</div>{/if}
						{#if n?.n}<div class="nt">{n.n}</div>{/if}
						{#if !n}<div class="nt dim">⏳ 해설 대기</div>{/if}
					</div>
				{/each}
			</div>
		{:else}
			<p class="page-sub" style="margin-top:16px">이 곡은 아직 가사 해설이 없어. (곡 추가·가사 세팅은 데스크탑에서)</p>
		{/if}
	{/if}
</div>

{#if detailIdx !== null && cur}
	<aside class="dpanel">
		<button class="dclose" onclick={closeDetail}>✕ 닫기</button>
		<div class="dh">소절 상세 {#if cur.lineTimes?.[detailIdx]}<span class="dt">{fmt(cur.lineTimes[detailIdx].start)}~</span>{/if}</div>
		<div class="djp">{@html detailNote.h || lines[detailIdx]}</div>
		{#if detailNote.t}<div class="dtr">{detailNote.t}</div>{/if}
		<div class="dbtns">
			<button class="dbtn" class:on={rowLoopOn} onclick={toggleRowLoop} disabled={!cur.lineTimes?.[detailIdx]}>{rowLoopOn ? '⏹ 반복 끄기' : '🔁 이 소절 반복'}</button>
			<button class="dbtn" onclick={() => playVocal(detailIdx!)} disabled={!cur.lineTimes?.[detailIdx]}>▶ 한 번 듣기</button>
			<button class="dbtn" onclick={() => slowSpeak(detailIdx!)}>🗣 느리게 발음</button>
		</div>
		<div class="dbody">{@html detailNote.d || (detailNote.n ? `<div>${detailNote.n}</div>` : '더 깊은 해설은 데스크탑에서 추가.')}</div>
	</aside>
{/if}

<style>
	.songrow { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; margin: 14px 0; }
	.spick { flex-shrink: 0; min-width: 150px; text-align: left; padding: 11px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; color: var(--text); cursor: pointer; }
	.spick.on { border-color: var(--accent); background: var(--btn); }
	.spick .st { display: block; font-weight: 700; font-size: 15px; }
	.spick .sa { color: var(--sub); font-size: 12px; }
	.player { position: relative; width: 100%; max-width: 900px; aspect-ratio: 16/9; background: #000; border-radius: 10px; overflow: hidden; margin-bottom: 10px; }
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
	.dpanel { position: fixed; top: 0; right: 0; bottom: 0; width: 420px; max-width: 94vw; background: var(--card); border-left: 1px solid var(--border); padding: 20px; overflow-y: auto; z-index: 60; box-shadow: -14px 0 40px rgba(0,0,0,.5); }
	@media (min-width: 1300px) { .page.shift { padding-right: 440px; } }
	.dclose { position: absolute; top: 16px; right: 16px; background: var(--btn); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 6px 11px; cursor: pointer; }
	.dh { color: var(--sub); font-size: 13px; }
	.dh .dt { color: var(--accent); }
	.djp { font-family: var(--jp); font-size: 26px; line-height: 1.9; margin: 8px 0 4px; }
	.djp :global(rt) { font-size: 12px; color: var(--accent); }
	.dtr { font-size: 18px; margin-bottom: 12px; }
	.dbtns { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 14px; }
	.dbtn { padding: 11px 6px; border-radius: 9px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; font-size: 14px; font-weight: 600; }
	.dbtn:hover { border-color: var(--accent); }
	.dbtn.on { background: var(--ok); border-color: var(--ok); color: #14161b; }
	.dbtn:disabled { opacity: .45; cursor: default; }
	.dbody { font-size: 16px; line-height: 1.75; word-break: keep-all; }
	.dbody :global(table) { width: 100%; border-collapse: collapse; margin: 10px 0; }
	.dbody :global(th), .dbody :global(td) { padding: 7px 8px; border-bottom: 1px solid var(--border); text-align: left; font-size: 14.5px; }
	.dbody :global(.jp) { font-family: var(--jp); font-size: 18px; }
	.dbody :global(b) { color: var(--accent); }
	.dbody :global(.tr) { margin: 8px 0; }
</style>
