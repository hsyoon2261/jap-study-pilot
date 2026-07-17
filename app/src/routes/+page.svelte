<script lang="ts">
	import { onMount } from 'svelte';

	type StudySet = { id: string; title: string; mode: string; count: number; done: boolean };
	type DeckMeta = { id: string; title: string; description: string; count: number };

	let sets = $state<StudySet[]>([]);
	let decks = $state<DeckMeta[]>([]);
	let loaded = $state(false);

	const DECK_IDS = ['kana', 'hiragana-words', 'katakana-words'];

	onMount(async () => {
		try {
			sets = await fetch('/content/sets.json').then((r) => r.json());
		} catch {
			sets = [];
		}
		const metas = await Promise.all(
			DECK_IDS.map(async (id) => {
				try {
					const d = await fetch(`/content/${id}.json`).then((r) => r.json());
					return { id, title: d.title, description: d.description, count: (d.items || []).length };
				} catch {
					return null;
				}
			})
		);
		decks = metas.filter((m): m is DeckMeta => m !== null);
		loaded = true;
	});

	const pending = $derived(sets.filter((s) => !s.done));
</script>

<div class="page">
	<h1 class="page-title">일본어 학습 🎌</h1>
	<p class="page-sub">기록은 계정에 쌓이고, 매일 조금씩. 오늘 할 것부터.</p>

	{#if loaded}
		{#if pending.length}
			<section class="block">
				<div class="block-h">오늘의 세트 · {pending.length}개 남음</div>
				<div class="grid">
					{#each pending as s (s.id)}
						<a class="card" href={`/drill?set=${s.id}`}>
							<div class="set-t">{s.title}</div>
							<div class="set-m">{s.count}문제 · {s.mode}</div>
							<div class="go">시작 →</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<section class="block">
			<div class="block-h">덱</div>
			<div class="grid">
				{#each decks as d (d.id)}
					<a class="card" href={`/browse?deck=${d.id}`}>
						<div class="set-t">{d.title}</div>
						<div class="set-m">{d.description}</div>
						<div class="count">{d.count}개</div>
					</a>
				{/each}
			</div>
		</section>
	{:else}
		<p class="page-sub" style="margin-top:30px">불러오는 중…</p>
	{/if}
</div>

<style>
	.block {
		margin-top: 30px;
	}
	.block-h {
		font-size: 14px;
		font-weight: 700;
		color: var(--sub);
		letter-spacing: 0.04em;
		margin-bottom: 12px;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 12px;
	}
	.card {
		display: block;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 14px;
		padding: 16px 18px;
	}
	.card:hover {
		border-color: var(--accent);
	}
	.set-t {
		font-size: 16.5px;
		font-weight: 700;
		line-height: 1.4;
		word-break: keep-all;
	}
	.set-m {
		color: var(--sub);
		font-size: 13.5px;
		margin-top: 6px;
		word-break: keep-all;
	}
	.go {
		color: var(--accent);
		font-weight: 700;
		font-size: 14px;
		margin-top: 12px;
	}
	.count {
		color: var(--accent);
		font-size: 13px;
		font-weight: 700;
		margin-top: 10px;
		font-variant-numeric: tabular-nums;
	}
</style>
