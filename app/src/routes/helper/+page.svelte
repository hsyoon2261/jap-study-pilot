<script lang="ts">
	import { onMount } from 'svelte';

	type Song = { id: string; song: string; artist: string; videoId?: string; lyric?: string; lineNotes?: any[]; lineTimes?: any[]; lyricUrl?: string };

	let songs = $state<Song[]>([]);
	let loaded = $state(false);

	onMount(async () => {
		try { songs = await fetch('/content/songs.json').then((r) => r.json()); } catch { songs = []; }
		loaded = true;
	});

	const statusOf = (s: Song) => {
		if (s.lineTimes && s.lineTimes.length) return { label: '싱크 완료', cls: 'ok' };
		if (s.lyric) return { label: '가사 등록 · 싱크 대기', cls: 'mid' };
		if (s.lyricUrl) return { label: '주소만 연결 · 세팅 대기', cls: 'mid' };
		return { label: '주소 없음', cls: 'off' };
	};
</script>

<svelte:head><title>가사 헬퍼</title></svelte:head>

<div class="page">
	<h1 class="page-title">가사 헬퍼 🔎</h1>
	<p class="page-sub">등록된 곡의 상태를 본다. 곡 <b>추가·가사 세팅</b>은 데스크탑에서 (자막·정렬 처리가 서버에서 돌아가야 해서).</p>

	<div class="note-box">
		가사 불러오기·⚡원클릭 세팅은 데스크탑 앱에서 한다 →
		<a class="ext" href="http://localhost:8765/helper" target="_blank" rel="noopener">데스크탑 헬퍼 열기 (localhost:8765)</a>
		<span class="dim">데스크탑에서 세팅하면 이 배포판 노래 탭에도 반영돼.</span>
	</div>

	{#if !loaded}
		<p class="page-sub" style="margin-top:20px">불러오는 중…</p>
	{:else if !songs.length}
		<p class="page-sub" style="margin-top:20px">등록된 곡이 없어.</p>
	{:else}
		<div class="list">
			{#each songs as s (s.id)}
				{@const st = statusOf(s)}
				<div class="srow">
					<div class="si">
						<div class="st">{s.song}</div>
						<div class="sa">{s.artist}</div>
					</div>
					<span class="badge {st.cls}">{st.label}</span>
					<a class="mini" href={`/songs?id=${s.id}`}>노래 탭</a>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.note-box { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; font-size: 14.5px; line-height: 1.7; margin-top: 18px; word-break: keep-all; }
	.ext { color: var(--accent); font-weight: 700; }
	.ext:hover { text-decoration: underline; }
	.dim { display: block; color: var(--sub); font-size: 13px; margin-top: 4px; }
	.list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
	.srow { display: flex; align-items: center; gap: 12px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
	.si { flex: 1; min-width: 0; }
	.st { font-weight: 700; font-size: 16px; word-break: keep-all; }
	.sa { color: var(--sub); font-size: 13px; }
	.badge { font-size: 12.5px; font-weight: 700; padding: 5px 10px; border-radius: 20px; white-space: nowrap; flex-shrink: 0; }
	.badge.ok { background: var(--ok-soft); color: var(--ok); }
	.badge.mid { background: var(--accent-soft); color: var(--accent); }
	.badge.off { background: var(--btn); color: var(--sub); }
	.mini { padding: 8px 13px; border-radius: 8px; border: 1px solid var(--border); background: var(--btn); color: var(--text); font-size: 14px; font-weight: 600; flex-shrink: 0; }
	.mini:hover { border-color: var(--accent); }
</style>
