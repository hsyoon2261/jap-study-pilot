<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { speak } from '$lib/audio';

	type WordItem = { word: string; romaji: string; mean: string };
	type KanaItem = { kana: string; sound: string; origin?: string; tip?: string };
	type Sec = { name: string; note?: string; type?: string; items: any[] };
	type Sheet = { day: number; date: string; title: string; intro?: string; sections: Sec[] };

	let sheets = $state<Sheet[]>([]);
	let idx = $state(0);
	let loaded = $state(false);

	onMount(async () => {
		try { sheets = await fetch('/content/sheets.json').then((r) => r.json()); } catch { sheets = []; }
		const want = page.url.searchParams.get('day');
		if (want !== null) {
			const found = sheets.findIndex((s) => String(s.day) === want);
			if (found >= 0) idx = found;
		}
		loaded = true;
	});

	const cur = $derived(sheets[idx] || null);
</script>

<svelte:head><title>{cur?.title || '오늘의 학습지'}</title></svelte:head>

<div class="page">
	{#if !loaded}
		<p class="page-sub" style="margin-top:24px">불러오는 중…</p>
	{:else if !cur}
		<p class="page-sub" style="margin-top:24px">학습지가 없어.</p>
	{:else}
		<a class="to-list" href="/sheets">📚 학습지 목록</a>
		<h1 class="page-title" style="margin-top:12px">{cur.title}</h1>
		{#if cur.intro}<p class="intro">{cur.intro}</p>{/if}

		{#each cur.sections as sec (sec.name)}
			<h2>{sec.name}</h2>
			{#if sec.note}<div class="note">{sec.note}</div>{/if}
			{#if sec.type === 'words'}
				<div class="word-grid">
					{#each sec.items as it (it.word)}
						<button class="wcard" onclick={() => speak((it as WordItem).word)}>
							<span class="jp">{(it as WordItem).word}</span>
							<span class="rom">{(it as WordItem).romaji}</span>
							<span class="mean">{(it as WordItem).mean}</span>
						</button>
					{/each}
				</div>
			{:else}
				<div class="kana-grid">
					{#each sec.items as it (it.kana)}
						<button class="kcard" onclick={() => speak((it as KanaItem).kana)}>
							<span class="big jp">{(it as KanaItem).kana}</span>
							<span class="info">
								<span class="sound">{(it as KanaItem).sound}</span>
								{#if (it as KanaItem).origin}<span class="origin">{(it as KanaItem).origin}</span>{/if}
								{#if (it as KanaItem).tip}<span class="tip">{(it as KanaItem).tip}</span>{/if}
							</span>
						</button>
					{/each}
				</div>
			{/if}
		{/each}
		<p class="tapnote">글자·단어를 누르면 발음이 재생돼.</p>
	{/if}
</div>

<style>
	.to-list { display: inline-block; padding: 8px 14px; border-radius: 18px; border: 1px solid var(--border); background: var(--btn); color: var(--sub); font-size: 14px; }
	.to-list:hover { border-color: var(--accent); color: var(--text); }
	.intro { color: var(--sub); font-size: 16px; line-height: 1.7; margin: 8px 0 8px; word-break: keep-all; }
	h2 { font-size: 20px; color: var(--accent); margin: 26px 0 6px; }
	.note { color: var(--sub); font-size: 15px; margin-bottom: 12px; line-height: 1.6; word-break: keep-all; }
	.kana-grid, .word-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
	@media (max-width: 620px) { .kana-grid, .word-grid { grid-template-columns: 1fr; } }
	.kcard, .wcard { display: flex; align-items: center; gap: 14px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 13px 15px; cursor: pointer; text-align: left; color: var(--text); width: 100%; }
	.kcard:hover, .wcard:hover { border-color: var(--accent); }
	.kcard .big { font-size: 50px; flex-shrink: 0; width: 60px; text-align: center; }
	.info { display: flex; flex-direction: column; }
	.info .sound { font-size: 18px; font-weight: 700; }
	.info .origin { font-size: 15px; color: var(--accent); font-family: var(--jp); margin-top: 2px; }
	.info .tip { font-size: 14px; color: var(--sub); margin-top: 3px; line-height: 1.5; word-break: keep-all; }
	.wcard .jp { font-size: 26px; }
	.wcard .rom { color: var(--sub); font-size: 14px; }
	.wcard .mean { margin-left: auto; font-size: 16px; text-align: right; }
	.tapnote { color: var(--sub); font-size: 13px; margin-top: 20px; }
</style>
