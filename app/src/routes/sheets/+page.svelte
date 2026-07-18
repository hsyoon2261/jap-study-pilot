<script lang="ts">
	import { onMount } from 'svelte';

	type Sec = { name: string; note?: string; type?: string; items: any[] };
	type Sheet = { day: number; date: string; title: string; intro?: string; sections: Sec[] };

	let sheets = $state<Sheet[]>([]);
	let loaded = $state(false);

	onMount(async () => {
		try { sheets = await fetch('/content/sheets.json').then((r) => r.json()); } catch { sheets = []; }
		loaded = true;
	});

	const counts = (s: Sheet) => {
		const kana = s.sections.filter((x) => x.type === 'kana').reduce((n, x) => n + x.items.length, 0);
		const words = s.sections.filter((x) => x.type === 'words').reduce((n, x) => n + x.items.length, 0);
		return { kana, words };
	};
</script>

<svelte:head><title>학습지 목록</title></svelte:head>

<div class="page">
	<h1 class="page-title">학습지 목록 📚</h1>
	<p class="page-sub">매일 하나씩 쌓인다. 클릭하면 그날 학습지로.</p>

	{#if !loaded}
		<p class="page-sub" style="margin-top:24px">불러오는 중…</p>
	{:else if !sheets.length}
		<p class="page-sub" style="margin-top:24px">아직 학습지가 없어.</p>
	{:else}
		<div class="list">
			<a class="card day0" href="/chart">
				<div class="day">Day 0 · 기초</div>
				<div class="t">가나 학습표 📖</div>
				<div class="meta">히라가나·가타카나·요음·촉음/장음/ん — 글자를 눌러 발음 듣기</div>
			</a>
			{#each sheets as s (s.day)}
				{@const c = counts(s)}
				<a class="card" href={`/sheet?day=${s.day}`}>
					<div class="day">Day {s.day} · {s.date}</div>
					<div class="t">{s.title}</div>
					<div class="meta">글자 {c.kana}개 · 단어 {c.words}개</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.list { display: flex; flex-direction: column; gap: 10px; margin-top: 20px; }
	.card { display: block; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; }
	.card:hover { border-color: var(--accent); }
	.card.day0 { background: linear-gradient(180deg, var(--card), var(--btn)); border-color: var(--accent); }
	.day { font-size: 13.5px; color: var(--accent); font-weight: 700; }
	.t { font-size: 18px; font-weight: 700; margin: 3px 0; word-break: keep-all; }
	.meta { font-size: 14px; color: var(--sub); }
</style>
