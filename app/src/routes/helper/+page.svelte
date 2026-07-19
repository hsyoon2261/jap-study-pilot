<script lang="ts">
	import { onMount } from 'svelte';

	type Song = { id: string; song: string; artist: string; videoId?: string; lyric?: string; lineNotes?: any[]; lineTimes?: any[]; lyricUrl?: string };

	let songs = $state<Song[]>([]);
	let loaded = $state(false);
	let isAdmin = $state(false);
	let pasted = $state<Record<string, string>>({}); // song_id → updatedAt

	// 붙여넣기 폼
	let selId = $state('');
	let lyricText = $state('');
	let saving = $state(false);
	let fetching = $state(false);
	let msg = $state('');

	onMount(async () => {
		try { songs = await fetch('/api/songs').then((r) => (r.ok ? r.json() : { songs: [] })).then((d) => d.songs || []); } catch { songs = []; }
		const me = await fetch('/api/me').then((r) => (r.ok ? r.json() : null)).catch(() => null);
		isAdmin = me?.username === 'admin';
		await loadPasted();
		if (songs.length) selId = (songs.find((s) => s.lyricUrl && !s.lyric)?.id) || songs[0].id;
		loaded = true;
	});

	async function loadPasted() {
		const d = await fetch('/api/songs/lyric').then((r) => (r.ok ? r.json() : { pasted: {} })).catch(() => ({ pasted: {} }));
		pasted = d.pasted || {};
	}

	const sel = $derived(songs.find((s) => s.id === selId) || null);

	function statusOf(s: Song) {
		if (s.lineTimes && s.lineTimes.length) return { label: '싱크 완료', cls: 'ok' };
		if (s.lyric) return { label: '해설 완료', cls: 'ok' };
		if (pasted[s.id]) return { label: '가사 붙여넣음 · 해설 대기', cls: 'mid' };
		if (s.lyricUrl) return { label: '가사 대기 (붙여넣기)', cls: 'mid' };
		return { label: '주소 없음', cls: 'off' };
	}

	async function fetchFromUtaten() {
		if (!selId) { msg = '곡부터 골라줘.'; return; }
		fetching = true; msg = '';
		try {
			const r = await fetch('/api/songs/fetch', {
				method: 'POST', headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ id: selId })
			});
			const d = await r.json();
			if (d.ok) {
				lyricText = d.lyric;
				msg = `✅ 우타텐에서 원문을 가져와 저장했어! 아래에 채워졌으니 확인하고, 고칠 게 있으면 고쳐서 "저장" 다시 눌러. 그다음 튜터한테 "가사 가져왔어" 하면 소절 나눠 해석 달아 노래 탭에 올려준다.`;
				await loadPasted();
			} else { msg = `❌ ${d.error || '가져오기 실패'}`; }
		} catch { msg = '❌ 연결 오류'; }
		fetching = false;
	}

	async function save() {
		if (!selId || !lyricText.trim()) { msg = '곡 고르고 가사를 붙여넣어줘.'; return; }
		saving = true; msg = '';
		try {
			const r = await fetch('/api/songs/lyric', {
				method: 'POST', headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ id: selId, lyric: lyricText })
			});
			const d = await r.json();
			if (d.ok) {
				msg = `✅ 저장됐어! "${sel?.song}" — 튜터한테 "가사 붙여넣었어"라고 하면 줄별 해석 달아서 노래 탭에 올려준다.`;
				lyricText = '';
				await loadPasted();
			} else { msg = `❌ ${d.error || '저장 실패'}`; }
		} catch { msg = '❌ 연결 오류'; }
		saving = false;
	}
</script>

<svelte:head><title>가사 헬퍼</title></svelte:head>

<div class="page">
	<h1 class="page-title">가사 헬퍼 🔎</h1>
	<p class="page-sub">곡에 가사를 붙여넣으면 튜터가 줄별 해석·문법을 달아 노래 탭에 올린다.</p>

	{#if loaded && isAdmin}
		<div class="paste">
			<div class="h">가사 붙여넣기 <span class="admin">admin</span></div>
			<label class="lbl">곡</label>
			<select class="inp" bind:value={selId}>
				{#each songs as s (s.id)}<option value={s.id}>{s.song} — {s.artist}</option>{/each}
			</select>

			{#if sel?.lyricUrl}
				<div class="fetchrow">
					<button class="btn2" onclick={fetchFromUtaten} disabled={fetching || saving}>{fetching ? '가져오는 중…' : '⚡ 우타텐에서 바로 가져오기'}</button>
					<a class="uta" href={sel.lyricUrl} target="_blank" rel="noopener">🔗 우타텐에서 보기 ↗</a>
				</div>
				<p class="tip">버튼 한 번이면 서버가 우타텐에서 원문을 긁어 아래에 채우고 저장까지 한다. (서버가 막히면 링크 열어 직접 복사→붙여넣기)</p>
			{:else if sel}
				<p class="tip">이 곡은 우타텐 주소가 없어. 아무 가사 원문이나 붙여넣어도 돼.</p>
			{/if}

			<label class="lbl">가사 원문</label>
			<textarea class="inp ta" bind:value={lyricText} rows="10" placeholder="여기에 가사 붙여넣기 (줄바꿈 유지)"></textarea>
			<button class="btn" onclick={save} disabled={saving}>{saving ? '저장 중…' : '저장'}</button>
			{#if msg}<p class="msg" class:ok={msg.startsWith('✅')}>{msg}</p>{/if}
		</div>
	{/if}

	{#if !loaded}
		<p class="page-sub" style="margin-top:20px">불러오는 중…</p>
	{:else}
		<div class="list">
			{#each songs as s (s.id)}
				{@const st = statusOf(s)}
				<div class="srow">
					<div class="si"><div class="st">{s.song}</div><div class="sa">{s.artist}</div></div>
					<span class="badge {st.cls}">{st.label}</span>
					<a class="mini" href={`/songs?id=${s.id}`}>노래 탭</a>
				</div>
			{/each}
		</div>
		<p class="foot">줄별 싱크(클릭하면 그 소절 재생)가 필요하면 데스크탑 앱에서 — <a href="http://localhost:8765/helper" target="_blank" rel="noopener">localhost:8765</a> (서버 켜져 있을 때만). 가사·해석만이면 여기 붙여넣기로 충분.</p>
	{/if}
</div>

<style>
	.paste { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; margin-top: 18px; }
	.h { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
	.admin { font-size: 11px; font-weight: 700; color: var(--accent); background: var(--accent-soft); padding: 2px 8px; border-radius: 10px; }
	.lbl { display: block; font-size: 12px; color: var(--sub); font-weight: 600; margin: 14px 0 5px; }
	.inp { width: 100%; padding: 11px 13px; border: 1px solid var(--border); border-radius: 9px; background: var(--btn); color: var(--text); font-size: 15px; }
	.ta { resize: vertical; font-family: var(--jp); line-height: 1.7; }
	.fetchrow { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-top: 12px; }
	.btn2 { padding: 11px 16px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); color: var(--accent); font-weight: 800; font-size: 14.5px; cursor: pointer; white-space: nowrap; }
	.btn2:hover { background: var(--accent); color: #fff; }
	.btn2:disabled { opacity: 0.6; cursor: default; }
	.uta { display: inline-block; color: var(--accent); font-weight: 700; font-size: 14px; }
	.uta:hover { text-decoration: underline; }
	.tip { color: var(--sub); font-size: 13px; margin: 6px 0 0; line-height: 1.5; word-break: keep-all; }
	.btn { margin-top: 14px; padding: 12px 20px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent); color: #fff; font-weight: 700; cursor: pointer; }
	.btn:disabled { opacity: 0.6; }
	.msg { margin-top: 12px; font-size: 14px; color: var(--accent); word-break: keep-all; line-height: 1.5; }
	.msg.ok { color: var(--ok); }
	.list { display: flex; flex-direction: column; gap: 8px; margin-top: 18px; }
	.srow { display: flex; align-items: center; gap: 12px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
	.si { flex: 1; min-width: 0; }
	.st { font-weight: 700; font-size: 16px; word-break: keep-all; }
	.sa { color: var(--sub); font-size: 13px; }
	.badge { font-size: 12px; font-weight: 700; padding: 5px 10px; border-radius: 20px; white-space: nowrap; flex-shrink: 0; }
	.badge.ok { background: var(--ok-soft); color: var(--ok); }
	.badge.mid { background: var(--accent-soft); color: var(--accent); }
	.badge.off { background: var(--btn); color: var(--sub); }
	.mini { padding: 8px 13px; border-radius: 8px; border: 1px solid var(--border); background: var(--btn); color: var(--text); font-size: 14px; font-weight: 600; flex-shrink: 0; }
	.mini:hover { border-color: var(--accent); }
	.foot { color: var(--sub); font-size: 13px; margin-top: 18px; line-height: 1.6; word-break: keep-all; }
	.foot a { color: var(--accent); }
</style>
