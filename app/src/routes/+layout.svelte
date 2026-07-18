<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { enforceVoiceAccess } from '$lib/audio';

	let { children } = $props();
	let ready = $state(false);
	let authed = $state(false);

	onMount(async () => {
		if (page.url.pathname === '/login') { ready = true; return; }
		try {
			const r = await fetch('/api/me');
			authed = r.ok;
			if (r.ok) { const d = await r.json(); enforceVoiceAccess(d.username === 'admin'); }
		} catch { authed = false; }
		if (!authed) { location.href = '/login'; return; }
		ready = true;
	});

	// 데스크톱 사이드바: 기존 9개 그대로 (데스크톱은 손대지 않음)
	const NAV = [
		{ href: '/', icon: '🏠', label: '오늘', match: ['/', '/drill'] },
		{ href: '/sheets', icon: '📝', label: '학습지', match: ['/sheet'] },
		{ href: '/chart', icon: '📖', label: '학습표', match: ['/chart'] },
		{ href: '/browse', icon: '📚', label: '덱', match: ['/browse'] },
		{ href: '/songs', icon: '🎵', label: '노래', match: ['/songs'] },
		{ href: '/helper', icon: '🔎', label: '헬퍼', match: ['/helper'] },
		{ href: '/custom', icon: '⭐', label: '요청', match: ['/custom'] },
		{ href: '/history', icon: '📊', label: '기록', match: ['/history'] },
		{ href: '/settings', icon: '⚙', label: '설정', match: ['/settings'] }
	];

	// 모바일 하단 탭: 축소 (학습표=학습지 병합, 헬퍼 제거, 기록·설정은 상단으로)
	const NAV_MOBILE = [
		{ href: '/', icon: '🏠', label: '오늘', match: ['/', '/drill'] },
		{ href: '/sheets', icon: '📖', label: '학습표', match: ['/sheets', '/sheet', '/chart'] },
		{ href: '/browse', icon: '📚', label: '덱', match: ['/browse'] },
		{ href: '/songs', icon: '🎵', label: '노래', match: ['/songs'] },
		{ href: '/custom', icon: '⭐', label: '요청', match: ['/custom'] }
	];

	function isActive(item: { href: string; match: string[] }): boolean {
		const path = page.url.pathname;
		if (item.href === '/') return path === '/' || path.startsWith('/drill');
		return item.match.some((m) => path === m || path.startsWith(m));
	}
	const histActive = $derived(page.url.pathname.startsWith('/history'));
	const setActive = $derived(page.url.pathname.startsWith('/settings'));
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>일본어 학습</title>
</svelte:head>

{#if page.url.pathname === '/login'}
	{@render children()}
{:else if ready}
	<!-- 데스크톱: 좌측 사이드바 (그대로) -->
	<nav class="sidenav">
		{#each NAV as item (item.href)}
			<a href={item.href} class:on={isActive(item)}>
				<span class="ic">{item.icon}</span>
				<span class="lb">{item.label}</span>
			</a>
		{/each}
	</nav>

	<!-- 모바일: 우측 최상단 기록·설정 -->
	<div class="mobtop">
		<a href="/history" class:on={histActive} aria-label="기록" title="기록">
			<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l3 2"/></svg>
		</a>
		<a href="/settings" class:on={setActive} aria-label="설정" title="설정">
			<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
		</a>
	</div>

	<!-- 모바일: 하단 탭 -->
	<nav class="mobbar">
		{#each NAV_MOBILE as item (item.href)}
			<a href={item.href} class:on={isActive(item)}>
				<span class="ic">{item.icon}</span>
				<span class="lb">{item.label}</span>
			</a>
		{/each}
	</nav>

	<main class="app-main">
		{@render children()}
	</main>
{/if}

<style>
	.sidenav {
		position: fixed;
		left: 0; top: 0; bottom: 0;
		width: 118px; z-index: 50;
		background: var(--surface);
		border-right: 1px solid var(--border);
		display: flex; flex-direction: column;
		gap: 2px; padding-top: 12px; overflow-y: auto;
	}
	.sidenav a {
		display: flex; flex-direction: column; align-items: center; gap: 4px;
		padding: 11px 4px; color: var(--sub); font-size: 13.5px;
		border-left: 3px solid transparent; flex-shrink: 0;
	}
	.sidenav a .ic { font-size: 23px; }
	.sidenav a:hover { color: var(--text); }
	.sidenav a.on { color: var(--text); border-left-color: var(--accent); background: var(--card); }
	.app-main { padding-left: 118px; }

	/* 모바일 전용 요소는 기본 숨김 */
	.mobtop, .mobbar { display: none; }

	@media (max-width: 700px) {
		.sidenav { display: none; }

		/* 우측 최상단: 기록·설정 아이콘 (다른 UI와 안 겹치게 고정) */
		.mobtop {
			display: flex; gap: 8px;
			position: fixed; top: 8px; right: 10px; z-index: 60;
			padding-top: env(safe-area-inset-top);
		}
		.mobtop a {
			display: flex; align-items: center; justify-content: center;
			width: 40px; height: 40px; border-radius: 50%;
			background: var(--card); border: 1px solid var(--border); color: var(--sub);
		}
		.mobtop a.on { color: var(--accent); border-color: var(--accent); }

		/* 하단 탭바: 5개 */
		.mobbar {
			display: flex; flex-direction: row; justify-content: space-around;
			position: fixed; left: 0; right: 0; bottom: 0; height: 60px; z-index: 50;
			background: var(--surface); border-top: 1px solid var(--border);
			padding-bottom: env(safe-area-inset-bottom);
		}
		.mobbar a {
			display: flex; flex-direction: column; align-items: center; justify-content: center;
			gap: 2px; flex: 1; min-width: 0;
			color: var(--sub); font-size: 11.5px; border-top: 3px solid transparent;
		}
		.mobbar a .ic { font-size: 21px; }
		.mobbar a.on { color: var(--text); border-top-color: var(--accent); }

		.app-main { padding-left: 0; padding-bottom: 68px; padding-top: 44px; }
		/* 제목이 우측 상단 버튼과 안 겹치게 */
		:global(.page-title) { padding-right: 92px; }
	}
</style>
