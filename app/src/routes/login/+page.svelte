<script lang="ts">
	let mode = $state<'login' | 'signup'>('login');
	let username = $state('');
	let password = $state('');
	let err = $state('');
	let busy = $state(false);

	async function submit(e: Event) {
		e.preventDefault();
		if (busy) return;
		busy = true; err = '';
		try {
			const url = mode === 'signup' ? '/api/signup' : '/api/login';
			const r = await fetch(url, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username: username.trim(), password })
			});
			const d = await r.json();
			if (d.ok) { location.href = '/'; return; }
			err = d.error || (mode === 'signup' ? '가입 실패' : '로그인 실패');
		} catch {
			err = '연결 오류';
		}
		busy = false;
	}

	function toggle() {
		mode = mode === 'login' ? 'signup' : 'login';
		err = '';
	}
</script>

<div class="wrap">
	<form class="box" onsubmit={submit}>
		<h1>일본어 학습 🎌</h1>
		<p class="sub">{mode === 'signup' ? '계정을 만들면 기록이 그 계정에 쌓여.' : '로그인하면 기록이 계정에 쌓인다.'}</p>
		<input bind:value={username} placeholder="아이디" autocomplete="username" />
		<input bind:value={password} type="password" placeholder="비밀번호" autocomplete={mode === 'signup' ? 'new-password' : 'current-password'} />
		{#if err}<div class="err">{err}</div>{/if}
		<button disabled={busy}>{busy ? '…' : mode === 'signup' ? '회원가입' : '로그인'}</button>
		<button type="button" class="switch" onclick={toggle}>
			{mode === 'signup' ? '이미 계정이 있어? 로그인' : '계정이 없어? 회원가입'}
		</button>
		{#if mode === 'signup'}<p class="note">아이디 2~20자 · 비밀번호 4자 이상. 개인정보는 안 받아.</p>{/if}
	</form>
</div>

<style>
	.wrap { min-height: 100dvh; display: flex; align-items: center; justify-content: center; padding: 20px; }
	.box { width: 100%; max-width: 340px; background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 28px 24px; display: flex; flex-direction: column; gap: 12px; }
	h1 { font-size: 24px; font-weight: 800; }
	.sub { color: var(--sub); font-size: 14px; margin-bottom: 8px; word-break: keep-all; }
	input { padding: 13px 14px; font-size: 16px; border-radius: 10px; border: 1px solid var(--border); background: var(--btn); color: var(--text); }
	button { margin-top: 6px; padding: 13px; font-size: 16px; font-weight: 700; border: none; border-radius: 10px; background: var(--accent); color: #fff; cursor: pointer; }
	button:disabled { opacity: .6; }
	.switch { margin-top: 2px; padding: 8px; background: none; color: var(--accent); font-weight: 600; font-size: 14px; border: none; cursor: pointer; }
	.note { color: var(--sub); font-size: 12.5px; text-align: center; margin-top: 2px; word-break: keep-all; }
	.err { color: var(--accent); font-size: 14px; }
</style>
