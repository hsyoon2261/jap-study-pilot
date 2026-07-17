<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { speak } from '$lib/audio';

	type Item = { id: string; front: string; back: string; ko?: string; origin?: string; tags: string[] };
	type Deck = { id: string; title: string; description: string; vocab?: boolean; items: Item[] };

	const DECKS = [
		{ id: 'kana', name: '가나' },
		{ id: 'hiragana-words', name: '히라가나 단어' },
		{ id: 'katakana-words', name: '가타카나 단어' }
	];
	let deckId = $state(page.url.searchParams.get('deck') || 'kana');
	let deck = $state<Deck | null>(null);
	let filter = $state('');

	async function load(id: string) {
		deckId = id;
		deck = await fetch(`/content/${id}.json`).then(r => r.json());
	}
	onMount(() => load(deckId));

	const items = $derived(
		!deck ? [] : (filter
			? deck.items.filter(it => (it.front+it.back+(it.ko||'')).toLowerCase().includes(filter.toLowerCase()))
			: deck.items)
	);
</script>

<div class="page">
	<h1 class="page-title">덱 열람 📚</h1>
	<p class="page-sub">단어를 눌러 발음을 듣는다.</p>
	<div class="picker">
		{#each DECKS as d (d.id)}
			<button class:on={deckId===d.id} onclick={() => load(d.id)}>{d.name}</button>
		{/each}
	</div>
	<input class="search" bind:value={filter} placeholder="검색 (글자·발음·뜻)" />

	{#if !deck}
		<p class="page-sub">불러오는 중…</p>
	{:else}
		<div class="cnt">{items.length}개</div>
		<div class="grid">
			{#each items as it (it.id)}
				<button class="w" onclick={() => speak(it.front)}>
					<span class="jp">{it.front}</span>
					<span class="rd">{it.back}</span>
					<span class="ko">{it.ko||''}</span>
					<span class="spk">🔊</span>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.picker { display: flex; gap: 8px; flex-wrap: wrap; margin: 14px 0 12px; }
	.picker button { padding: 9px 16px; border-radius: 20px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; font-size: 15px; }
	.picker button.on { background: var(--text); color: #14161b; font-weight: 700; }
	.search { width: 100%; padding: 12px 14px; border-radius: 10px; border: 1px solid var(--border); background: var(--btn); color: var(--text); font-size: 16px; margin-bottom: 14px; }
	.cnt { color: var(--accent); font-size: 13px; font-weight: 700; margin-bottom: 10px; }
	.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
	.w { display: flex; align-items: baseline; gap: 9px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 11px 13px; cursor: pointer; color: var(--text); text-align: left; }
	.w:hover { border-color: var(--accent); }
	.w .jp { font-family: var(--jp); font-size: 21px; }
	.w .rd { color: var(--accent); font-size: 13px; }
	.w .ko { color: var(--sub); font-size: 14px; margin-left: auto; }
	.w .spk { font-size: 12px; opacity: .5; }
</style>
