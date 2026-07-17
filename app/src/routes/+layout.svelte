<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';

	let { children } = $props();

	const NAV = [
		{ href: '/', icon: '🏠', label: '오늘' },
		{ href: '/chart', icon: '📖', label: '학습표' },
		{ href: '/browse', icon: '📚', label: '덱' },
		{ href: '/songs', icon: '🎵', label: '노래' },
		{ href: '/history', icon: '📊', label: '기록' }
	];

	function isActive(href: string): boolean {
		const path = page.url.pathname;
		return href === '/' ? path === '/' : path.startsWith(href);
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>일본어 학습</title>
</svelte:head>

<nav class="sidenav">
	{#each NAV as item (item.href)}
		<a href={item.href} class:on={isActive(item.href)}>
			<span class="ic">{item.icon}</span>
			<span class="lb">{item.label}</span>
		</a>
	{/each}
</nav>

<main class="app-main">
	{@render children()}
</main>

<style>
	.sidenav {
		position: fixed;
		left: 0;
		top: 0;
		bottom: 0;
		width: 128px;
		z-index: 50;
		background: var(--surface);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding-top: 18px;
	}
	.sidenav a {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		padding: 14px 4px;
		color: var(--sub);
		font-size: 14px;
		border-left: 3px solid transparent;
	}
	.sidenav a .ic {
		font-size: 25px;
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
		padding-left: 128px;
	}

	@media (max-width: 700px) {
		.sidenav {
			top: auto;
			bottom: 0;
			right: 0;
			width: auto;
			height: 62px;
			flex-direction: row;
			justify-content: space-around;
			padding: 0;
			border-right: none;
			border-top: 1px solid var(--border);
			padding-bottom: env(safe-area-inset-bottom);
		}
		.sidenav a {
			border-left: none;
			border-top: 3px solid transparent;
			padding: 7px 8px;
			font-size: 11px;
			flex: 1;
			justify-content: center;
		}
		.sidenav a .ic {
			font-size: 21px;
		}
		.sidenav a.on {
			border-top-color: var(--accent);
			background: none;
		}
		.app-main {
			padding-left: 0;
			padding-bottom: 66px;
		}
	}
</style>
