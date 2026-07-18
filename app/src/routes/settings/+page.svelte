<script lang="ts">
	import { onMount } from 'svelte';
	import { speak, VOICE_LIST, getSelectedVoice, setSelectedVoice } from '$lib/audio';

	let username = $state('');
	let loaded = $state(false);
	let busy = $state(false);
	let sel = $state('');

	const SAMPLE = 'こんにちは。今日も一緒にがんばりましょう。';
	const isAdmin = $derived(username === 'admin');

	onMount(async () => {
		sel = getSelectedVoice();
		try {
			const r = await fetch('/api/me');
			if (r.ok) { const d = await r.json(); username = d.username || ''; }
		} catch { /* */ }
		loaded = true;
	});

	function pick(id: string) { setSelectedVoice(id); sel = id; speak(SAMPLE); }
	function preview(id: string) {
		const prev = getSelectedVoice();
		setSelectedVoice(id);
		speak(SAMPLE);          // speakBrowser는 음성을 동기 캡처
		setSelectedVoice(prev); // 미리듣기는 현재 선택을 안 바꿈
	}

	async function logout() {
		busy = true;
		await fetch('/api/me', { method: 'POST' }).catch(() => {});
		location.href = '/login';
	}
</script>

<svelte:head><title>설정</title></svelte:head>

<div class="page">
	<h1 class="page-title">설정 ⚙</h1>
	<p class="page-sub">발음·계정.</p>

	<div class="card">
		<div class="row"><span class="k">로그인 계정</span><span class="v">{loaded ? (username || '—') : '…'}</span></div>
		<div class="row"><span class="k">기록 저장</span><span class="v">계정(D1)에 자동 저장</span></div>
		<div class="row"><span class="k">발음</span><span class="v">미리 녹음한 기본 음성 (어디서나 같은 소리)</span></div>
		<button class="logout" disabled={busy} onclick={logout}>{busy ? '…' : '로그아웃'}</button>
	</div>

	{#if loaded && isAdmin}
		<div class="card">
			<div class="h">발음 음성 고르기 <span class="admin">admin 전용</span></div>
			<p class="desc">빌드에 내장한 음성이라 어느 기기에서나 같은 소리. ▶로 들어보고 줄을 눌러 선택.</p>
			<div class="voices">
				{#each VOICE_LIST as v (v.id)}
					<div class="voice" class:cur={sel === v.id}>
						<button class="vplay" onclick={(e) => { e.stopPropagation(); preview(v.id); }} title="들어보기">▶</button>
						<button class="vname" onclick={() => pick(v.id)}>
							<span class="vl">{v.label}</span>
							<span class="vd">{v.desc}</span>
						</button>
						{#if sel === v.id}<span class="vcur">사용 중</span>{/if}
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<div class="card sec">
		<div class="h">곡 세팅</div>
		<p class="desc">노래 추가·가사 싱크는 데스크탑 앱(<a href="http://localhost:8765/helper" target="_blank" rel="noopener">localhost:8765</a>)에서. 자막 정렬이 서버에서 돌아가기 때문.</p>
	</div>
</div>

<style>
	.card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; margin-top: 18px; }
	.h { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
	.admin { font-size: 11px; font-weight: 700; color: var(--accent); background: var(--accent-soft); padding: 2px 8px; border-radius: 10px; }
	.desc { color: var(--sub); font-size: 14px; line-height: 1.7; margin-top: 6px; word-break: keep-all; }
	.desc a { color: var(--accent); font-weight: 600; }
	.voices { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
	.voice { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--btn); border: 1px solid var(--border); border-radius: 10px; }
	.voice.cur { border-color: var(--ok); }
	.vplay { flex-shrink: 0; background: var(--card); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 8px 12px; cursor: pointer; font-size: 13px; }
	.vplay:hover { border-color: var(--accent); }
	.vname { flex: 1; min-width: 0; text-align: left; background: none; border: none; color: var(--text); cursor: pointer; display: flex; flex-direction: column; gap: 2px; }
	.vname .vl { font-size: 15px; font-weight: 700; }
	.vname .vd { font-size: 12.5px; color: var(--sub); font-weight: 400; line-height: 1.4; word-break: keep-all; }
	.vcur { color: var(--ok); font-size: 12.5px; font-weight: 700; flex-shrink: 0; align-self: center; }
	.row { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 15px; }
	.row:first-child { padding-top: 0; }
	.row:last-of-type { border-bottom: none; }
	.row .k { color: var(--sub); flex-shrink: 0; }
	.row .v { font-weight: 600; text-align: right; word-break: keep-all; }
	.logout { margin-top: 16px; width: 100%; padding: 13px; font-size: 16px; font-weight: 700; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); color: var(--accent); cursor: pointer; }
	.logout:disabled { opacity: 0.6; }
	.sec .desc { margin-top: 6px; }
</style>
