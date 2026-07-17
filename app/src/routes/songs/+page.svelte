<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { speak } from '$lib/audio';

	type Note = { t?: string; n?: string; h?: string; d?: string; cont?: boolean };
	type Time = { start: number; end: number };
	type Song = { id: string; song: string; artist: string; videoId: string; lyric?: string; lineNotes?: Note[]; lineTimes?: Time[]; date?: string };

	let songs = $state<Song[]>([]);
	let cur = $state<Song | null>(null);
	let lines = $state<string[]>([]);
	let nowIdx = $state(-1);
	let detail = $state<number | null>(null);
	let player: any = null;
	let ytReady = false;
	let apiFailed = $state(false);
	let tick: any = null;

	const readingOf = (s: string) => (s||'')
		.replace(/[一-龥々〆ヶ]+（([^（）]+)）/g, '$1').replace(/（[^）]*）/g, '');
	const watchUrl = (s: Song | null) => s ? `https://www.youtube.com/watch?v=${s.videoId}` : '#';

	onMount(async () => {
		songs = await fetch('/content/songs.json').then(r => r.json());
		// YouTube IFrame API
		(window as any).onYouTubeIframeAPIReady = () => { ytReady = true; if (cur) mount(cur); };
		if (!(window as any).YT) {
			const s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api';
			s.onerror = () => { apiFailed = true; };
			document.head.appendChild(s);
			// 6초 안에 API가 안 뜨면(광고차단·네트워크) 폴백 안내
			setTimeout(() => { if (!ytReady) apiFailed = true; }, 6000);
		} else { ytReady = true; }
		const first = songs.find(s => s.lyric) || songs[0];
		if (first) select(first);
		tick = setInterval(() => {
			if (!player?.getCurrentTime || !cur?.lineTimes) return;
			try {
				const t = player.getCurrentTime() - 0.6;
				let idx = -1;
				for (let k=0;k<cur.lineTimes.length;k++){ const tm=cur.lineTimes[k]; if (tm && t>=tm.start-0.2 && t<tm.end+0.3){ idx=k; break; } }
				if (idx !== nowIdx) nowIdx = idx;
			} catch { /* */ }
		}, 250);
	});
	onDestroy(() => { if (tick) clearInterval(tick); });

	function mount(s: Song) {
		if (!ytReady || !(window as any).YT?.Player) return;
		if (player) { player.cueVideoById({ videoId: s.videoId }); return; }
		player = new (window as any).YT.Player('yt', { videoId: s.videoId, playerVars: { rel: 0 } });
	}

	function select(s: Song) {
		cur = s; detail = null; nowIdx = -1;
		lines = (s.lyric || '').split(/\n+/).map(x => x.trim()).filter(Boolean);
		mount(s);
	}

	function seek(i: number) {
		const t = cur?.lineTimes?.[i]; if (!t || !player?.seekTo) return;
		player.seekTo(Math.max(0, t.start - 0.2), true); player.playVideo?.();
		nowIdx = i;
	}
	function openDetail(i: number) { detail = detail === i ? null : i; }
</script>

<svelte:head><title>노래로 공부</title></svelte:head>

<div class="page" class:shift={detail!==null}>
	<h1 class="page-title">노래로 공부 🎵</h1>
	<p class="page-sub">소절을 누르면 그 지점부터 재생 · 더블클릭하면 상세 해설.</p>

	<div class="songrow">
		{#each songs as s (s.id)}
			<button class="spick" class:on={cur?.id===s.id} onclick={() => select(s)}>
				<span class="st">{s.song}</span><span class="sa">{s.artist}</span>
			</button>
		{/each}
	</div>

	{#if cur}
		<div class="player"><div id="yt"></div></div>
		<div class="phint">
			<span>▶ 재생 버튼을 누르거나 <b>가사 줄을 클릭</b>하면 그 지점부터 소리와 함께 재생돼.</span>
			<a class="ytlink" href={watchUrl(cur)} target="_blank" rel="noopener">유튜브에서 열기 ↗</a>
		</div>
		{#if apiFailed}
			<div class="fallback">플레이어가 안 뜨면(광고 차단·네트워크) 위 <b>유튜브에서 열기</b>로 들어. 가사 해설은 여기서 계속 볼 수 있어.</div>
		{/if}
		{#if lines.length}
			<div class="lyrics">
				{#each lines as l, i (i)}
					{@const n = (cur.lineNotes||[])[i]}
					<div class="line" class:now={nowIdx===i}>
						<button class="jp" ondblclick={() => openDetail(i)} onclick={() => seek(i)}>{@html (n?.h) || l}{#if n?.cont}<span class="cont">→</span>{/if}</button>
						{#if n?.t}<div class="tr">{n.t}</div>{/if}
						{#if n?.n}<div class="nt">{n.n}</div>{/if}
					</div>
				{/each}
			</div>
		{:else}
			<p class="page-sub" style="margin-top:16px">이 곡은 아직 가사 해설이 없어. (곡 추가는 데스크탑에서)</p>
		{/if}
	{/if}
</div>

{#if detail!==null && cur}
	{@const n = (cur.lineNotes||[])[detail]}
	<aside class="dpanel">
		<button class="dclose" onclick={() => detail=null}>✕ 닫기</button>
		<div class="dh">소절 상세</div>
		<div class="djp">{@html n?.h || lines[detail]}</div>
		{#if n?.t}<div class="dtr">{n.t}</div>{/if}
		<div class="dbtns">
			<button onclick={() => seek(detail!)}>▶ 이 소절부터</button>
			<button onclick={() => speak(readingOf(lines[detail!]))}>🗣 느리게 발음</button>
		</div>
		<div class="dbody">{@html n?.d || (n?.n ? `<div>${n.n}</div>` : '더 깊은 해설은 데스크탑에서 추가.')}</div>
	</aside>
{/if}

<style>
	.songrow { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; margin: 14px 0; }
	.spick { flex-shrink: 0; min-width: 150px; text-align: left; padding: 11px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; color: var(--text); cursor: pointer; }
	.spick.on { border-color: var(--accent); background: var(--btn); }
	.spick .st { display: block; font-weight: 700; font-size: 15px; }
	.spick .sa { color: var(--sub); font-size: 12px; }
	.player { position: relative; width: 100%; max-width: 900px; aspect-ratio: 16/9; background: #000; border-radius: 10px; overflow: hidden; margin-bottom: 14px; }
	.player :global(iframe) { position: absolute; inset: 0; width: 100%; height: 100%; }
	.phint { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin: -4px 0 14px; color: var(--sub); font-size: 13.5px; }
	.phint b { color: var(--text); }
	.ytlink { flex-shrink: 0; padding: 8px 13px; border: 1px solid var(--border); border-radius: 8px; background: var(--btn); color: var(--accent); font-weight: 600; font-size: 13px; }
	.ytlink:hover { border-color: var(--accent); }
	.fallback { background: var(--accent-soft); border: 1px solid var(--accent); border-radius: 10px; padding: 11px 14px; font-size: 14px; margin-bottom: 14px; }
	.fallback b { color: var(--accent); }
	.lyrics { border-top: 1px solid var(--border); padding-top: 12px; }
	.line { margin-bottom: 10px; padding: 7px 10px; border-radius: 10px; border-left: 3px solid transparent; }
	.line.now { background: var(--btn); border-left-color: var(--accent); }
	.jp { display: block; width: 100%; text-align: left; background: none; border: none; color: var(--text); font-family: var(--jp); font-size: 29px; line-height: 1.9; cursor: pointer; user-select: none; }
	.jp :global(ruby) { white-space: nowrap; }
	.jp :global(rt) { font-size: 13px; color: var(--accent); font-family: "Segoe UI", sans-serif; }
	.cont { color: var(--sub); opacity: .5; font-size: 60%; }
	.tr { font-size: 17px; margin-top: 4px; opacity: .9; }
	.nt { color: var(--sub); font-size: 15px; margin-top: 3px; word-break: keep-all; }
	.dpanel { position: fixed; top: 0; right: 0; bottom: 0; width: 420px; max-width: 94vw; background: var(--card); border-left: 1px solid var(--border); padding: 20px; overflow-y: auto; z-index: 60; box-shadow: -14px 0 40px rgba(0,0,0,.5); }
	@media (min-width: 1300px) { .page.shift { padding-right: 440px; } }
	.dclose { position: absolute; top: 16px; right: 16px; background: var(--btn); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 6px 11px; cursor: pointer; }
	.dh { color: var(--sub); font-size: 13px; }
	.djp { font-family: var(--jp); font-size: 26px; line-height: 1.9; margin: 8px 0 4px; }
	.djp :global(rt) { font-size: 12px; color: var(--accent); }
	.dtr { font-size: 18px; margin-bottom: 12px; }
	.dbtns { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
	.dbtns button { padding: 10px 14px; border-radius: 9px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; font-size: 14.5px; font-weight: 600; }
	.dbody { font-size: 16px; line-height: 1.75; word-break: keep-all; }
	.dbody :global(table) { width: 100%; border-collapse: collapse; margin: 10px 0; }
	.dbody :global(th), .dbody :global(td) { padding: 7px 8px; border-bottom: 1px solid var(--border); text-align: left; font-size: 14.5px; }
	.dbody :global(.jp) { font-family: var(--jp); font-size: 18px; }
	.dbody :global(b) { color: var(--accent); }
	.dbody :global(.tr) { margin: 8px 0; }
</style>
