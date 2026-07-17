<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	let { children } = $props();
	let ready = $state(false);
	let authed = $state(false);

	onMount(async () => {
		if (page.url.pathname === '/login') { ready = true; return; }
		try {
			const r = await fetch('/api/me');
			authed = r.ok;
		} catch { authed = false; }
		if (!authed) { location.href = '/login'; return; }
		ready = true;
	});

	// 레거시(8765)와 동일한 메뉴 구성 + 순서. 설정은 기록 바로 밑.
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

	function isActive(item: { href: string; match: string[] }): boolean {
		const path = page.url.pathname;
		if (item.href === '/') return path === '/' || path.startsWith('/drill');
		return item.match.some((m) => path === m || path.startsWith(m));
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>일본어 학습</title>
</svelte:head>

{#if page.url.pathname === '/login'}
	{@render children()}
{:else if ready}
	<nav class="sidenav">
		{#each NAV as item (item.href)}
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
		left: 0;
		top: 0;
		bottom: 0;
		width: 118px;
		z-index: 50;
		background: var(--surface);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding-top: 12px;
		overflow-y: auto;
	}
	.sidenav a {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		padding: 11px 4px;
		color: var(--sub);
		font-size: 13.5px;
		border-left: 3px solid transparent;
		flex-shrink: 0;
	}
	.sidenav a .ic {
		font-size: 23px;
	}
	.sidenav a:hover {
		color: var(--text);
	}
	.sidenav a.on {
		color: var(--text);
		border-left-color: var(--accent);
		background: var(--card);
	}
	.app-main {
		padding-left: 118px;
	}

	@media (max-width: 700px) {
		.sidenav {
			top: auto;
			bottom: 0;
			right: 0;
			width: auto;
			height: 60px;
			flex-direction: row;
			justify-content: space-around;
			padding: 0;
			gap: 0;
			border-right: none;
			border-top: 1px solid var(--border);
			padding-bottom: env(safe-area-inset-bottom);
			overflow: visible;
		}
		/* 9개 항목이 375px 폰에서도 안 잘리게 촘촘히 (레거시와 동일 규칙) */
		.sidenav a {
			border-left: none;
			border-top: 3px solid transparent;
			padding: 7px 2px;
			font-size: 10px;
			gap: 2px;
			flex: 1;
			min-width: 0;
			justify-content: center;
		}
		.sidenav a .ic {
			font-size: 18px;
		}
		.sidenav a.on {
			border-top-color: var(--accent);
			background: none;
		}
		.app-main {
			padding-left: 0;
			padding-bottom: 68px;
		}
	}
</style>
