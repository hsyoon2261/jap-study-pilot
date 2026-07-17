<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { speak } from '$lib/audio';

	type Req = { id: string; day: number; date: string; title: string; html?: string };

	let reqs = $state<Req[]>([]);
	let loaded = $state(false);
	let wantId = $state<string | null>(null);
	let detailEl = $state<HTMLElement | null>(null);

	onMount(async () => {
		try { reqs = await fetch('/content/custom.json').then((r) => r.json()); } catch { reqs = []; }
		wantId = page.url.searchParams.get('id');
		loaded = true;
	});

	// URL 쿼리 변화 반영 (클라이언트 네비게이션)
	$effect(() => { wantId = page.url.searchParams.get('id'); });

	const cur = $derived(wantId ? reqs.find((r) => r.id === wantId) || null : null);

	// 상세 HTML 안의 data-say 요소에 발음 재생 연결
	$effect(() => {
		if (!cur || !detailEl) return;
		const els = detailEl.querySelectorAll<HTMLElement>('[data-say]');
		const handlers: Array<() => void> = [];
		els.forEach((el) => {
			const h = () => speak(el.dataset.say || '');
			el.addEventListener('click', h);
			el.style.cursor = 'pointer';
			handlers.push(() => el.removeEventListener('click', h));
		});
		return () => handlers.forEach((off) => off());
	});

	// Day 내림차순 그룹
	const byDay = $derived.by(() => {
		const m = new Map<number, Req[]>();
		for (const r of reqs) { if (!m.has(r.day)) m.set(r.day, []); m.get(r.day)!.push(r); }
		return [...m.entries()].sort((a, b) => b[0] - a[0]);
	});
</script>

<svelte:head><title>{cur?.title || '요청 자료'}</title></svelte:head>

<div class="page custom">
	{#if !loaded}
		<p class="page-sub" style="margin-top:24px">불러오는 중…</p>
	{:else if cur}
		<a class="to-list" href="/custom">← 요청 목록</a>
		<div class="group" bind:this={detailEl}>
			<h2>{cur.title}</h2>
			{@html cur.html || ''}
			<div class="date">Day {cur.day} · {cur.date || ''}</div>
		</div>
	{:else}
		<h1 class="page-title">요청 자료 ⭐</h1>
		<p class="page-sub">공부하다 궁금해서 요청한 것들이 여기 쌓인다. 버튼 = 발음 재생.</p>
		{#if !reqs.length}
			<p class="page-sub" style="margin-top:24px">아직 요청이 없어. 공부하다 궁금한 걸 튜터에게 물어보면 여기 쌓인다.</p>
		{:else}
			{#each byDay as [day, list] (day)}
				<div class="day-head">Day {day} <span class="dsub">· {list[0].date} · {list.length}건</span></div>
				{#each list as r (r.id)}
					<a class="req-link" href={`/custom?id=${r.id}`}>{r.title}</a>
				{/each}
			{/each}
		{/if}
	{/if}
</div>

<style>
	.to-list { display: inline-block; margin-bottom: 14px; padding: 8px 14px; border-radius: 18px; border: 1px solid var(--border); background: var(--btn); color: var(--sub); font-size: 14px; }
	.to-list:hover { border-color: var(--accent); color: var(--text); }
	.day-head { font-size: 20px; color: var(--accent); font-weight: 700; margin: 22px 0 10px; }
	.day-head .dsub { font-size: 14px; color: var(--sub); font-weight: 400; }
	.req-link { display: block; background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; margin-bottom: 8px; color: var(--text); font-size: 16px; font-weight: 600; }
	.req-link:hover { border-color: var(--accent); }
	.group { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
	.group :global(h2) { font-size: 20px; color: var(--accent); margin-bottom: 8px; }
	.date { font-size: 12px; color: var(--sub); margin-top: 10px; }
	/* 자유 HTML 블록 공용 스타일 (원본 custom.html과 동일 규칙) */
	.custom :global(table) { width: 100%; border-collapse: collapse; margin: 10px 0; }
	.custom :global(th), .custom :global(td) { padding: 8px; border-bottom: 1px solid var(--border); font-size: 15px; text-align: left; }
	.custom :global(th) { color: var(--sub); font-size: 13px; }
	.custom :global(ul) { margin: 8px 0 8px 20px; line-height: 1.8; font-size: 15px; }
	.custom :global(p) { line-height: 1.8; font-size: 16px; margin: 8px 0; word-break: keep-all; }
	.custom :global(.jp-inline) { font-family: var(--jp); font-size: 18px; }
	.custom :global(.btns) { display: flex; flex-wrap: wrap; gap: 10px; }
	.custom :global(.say) { flex: 1; min-width: 150px; text-align: center; background: var(--btn); border: 1px solid var(--border); border-radius: 12px; padding: 16px 12px; cursor: pointer; color: var(--text); }
	.custom :global(.say:hover) { border-color: var(--accent); }
	.custom :global(.say .jp) { font-size: 32px; font-family: var(--jp); display: block; }
	.custom :global(.say .lb) { font-size: 15px; font-weight: 700; display: block; margin-top: 6px; }
	.custom :global(.say .sub2) { font-size: 13px; color: var(--sub); display: block; margin-top: 3px; word-break: keep-all; }
</style>
