<script lang="ts">
	import { onMount } from 'svelte';

	let username = $state('');
	let loaded = $state(false);
	let busy = $state(false);

	onMount(async () => {
		try {
			const r = await fetch('/api/me');
			if (r.ok) { const d = await r.json(); username = d.username || ''; }
		} catch { /* */ }
		loaded = true;
	});

	async function logout() {
		busy = true;
		await fetch('/api/me', { method: 'POST' }).catch(() => {});
		location.href = '/login';
	}
</script>

<svelte:head><title>설정</title></svelte:head>

<div class="page">
	<h1 class="page-title">설정 ⚙</h1>
	<p class="page-sub">계정과 앱 정보.</p>

	<div class="card">
		<div class="row"><span class="k">로그인 계정</span><span class="v">{loaded ? (username || '—') : '…'}</span></div>
		<div class="row"><span class="k">기록 저장</span><span class="v">계정(D1)에 자동 저장</span></div>
		<button class="logout" disabled={busy} onclick={logout}>{busy ? '…' : '로그아웃'}</button>
	</div>

	<div class="card sec">
		<div class="h">발음 재생</div>
		<p class="desc">글자·단어·소절을 누르면 발음이 나온다. 미리 구운 음성이 없으면 브라우저 내장 음성으로 재생돼.</p>
		<div class="h">곡 세팅</div>
		<p class="desc">노래 추가·가사 싱크는 데스크탑 앱(<a href="http://localhost:8765/helper" target="_blank" rel="noopener">localhost:8765</a>)에서. 성우 엔진·자막 정렬이 서버에서 돌아가기 때문.</p>
	</div>
</div>

<style>
	.card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; margin-top: 20px; }
	.row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 15px; }
	.row:first-child { padding-top: 0; }
	.row .k { color: var(--sub); }
	.row .v { font-weight: 600; }
	.logout { margin-top: 16px; width: 100%; padding: 13px; font-size: 16px; font-weight: 700; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); color: var(--accent); cursor: pointer; }
	.logout:disabled { opacity: 0.6; }
	.sec .h { font-size: 15px; font-weight: 700; margin-top: 6px; }
	.sec .h + .desc { margin-bottom: 14px; }
	.desc { color: var(--sub); font-size: 14px; line-height: 1.7; margin-top: 6px; word-break: keep-all; }
	.desc a { color: var(--accent); font-weight: 600; }
</style>
