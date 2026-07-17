<script lang="ts">
	import { onMount } from 'svelte';

	type SetCfg = { id: string; title: string; deck: string; mode: string; count: number };
	type DeckMeta = { id: string; title: string; description: string; count: number };
	type Srs = { box: number; right: number; wrong: number; due: string };

	const DECK_IDS = ['kana', 'hiragana-words', 'katakana-words'];
	const KST = 32400000;
	const nowKst = () => new Date(Date.now() + KST).toISOString().slice(0, 19);
	const todayKst = () => new Date(Date.now() + KST).toISOString().slice(0, 10);

	let sets = $state<SetCfg[]>([]);
	let doneMap = $state<Record<string, { done: boolean; doneAt: string | null }>>({});
	let decks = $state<DeckMeta[]>([]);
	let srs = $state<Record<string, Srs>>({});
	let byDay = $state<{ d: string; n: number; ok: number }[]>([]);
	let total = $state(0);
	let loaded = $state(false);
	let busy = $state<string | null>(null);

	async function load() {
		const [setsRes, doneRes, stateRes, ...deckRes] = await Promise.all([
			fetch('/content/sets.json').then((r) => r.json()).catch(() => []),
			fetch('/api/sets').then((r) => r.json()).catch(() => ({ sets: {} })),
			fetch('/api/state').then((r) => r.json()).catch(() => ({})),
			...DECK_IDS.map((id) =>
				fetch(`/content/${id}.json`).then((r) => r.json()).then((d) => ({ id, title: d.title, description: d.description, count: (d.items || []).length })).catch(() => null)
			)
		]);
		sets = setsRes;
		doneMap = doneRes.sets || {};
		srs = stateRes.srs || {};
		byDay = stateRes.byDay || [];
		total = stateRes.total || 0;
		decks = deckRes.filter((m): m is DeckMeta => m !== null);
		loaded = true;
	}

	onMount(load);

	async function toggleDone(id: string, next: boolean) {
		busy = id;
		await fetch('/api/sets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, done: next }) }).catch(() => {});
		doneMap = { ...doneMap, [id]: { done: next, doneAt: next ? nowKst() : null } };
		busy = null;
	}

	const isDone = (id: string) => !!doneMap[id]?.done;
	const pending = $derived(sets.filter((s) => !isDone(s.id)));
	const doneSets = $derived(sets.filter((s) => isDone(s.id)));

	// 현황 통계
	const todayCount = $derived(byDay.find((b) => b.d === todayKst())?.n ?? 0);
	const streak = $derived.by(() => {
		if (!byDay.length) return 0;
		const days = new Set(byDay.map((b) => b.d));
		let n = 0;
		const cur = new Date(Date.now() + KST);
		// 오늘 기록이 없으면 어제부터 세되, 오늘까지 안 끊긴 연속만 인정
		for (let i = 0; i < 400; i++) {
			const key = cur.toISOString().slice(0, 10);
			if (days.has(key)) n++;
			else if (i === 0) { /* 오늘은 아직 안 풀었을 수 있음 — 넘어가서 어제부터 */ }
			else break;
			cur.setUTCDate(cur.getUTCDate() - 1);
		}
		return n;
	});
	// 복습 대기 (due <= now), 덱별
	const dueByDeck = $derived.by(() => {
		const now = nowKst();
		const m: Record<string, number> = {};
		for (const [key, s] of Object.entries(srs)) {
			if (!s.due || s.due > now) continue;
			const deck = key.slice(0, key.indexOf(':'));
			m[deck] = (m[deck] || 0) + 1;
		}
		return m;
	});
	const dueEntries = $derived(Object.entries(dueByDeck));
	const deckTitle = (id: string) => decks.find((d) => d.id === id)?.title || id;
	// 약한 항목 top
	const weak = $derived.by(() =>
		Object.entries(srs)
			.filter(([, s]) => s.wrong > 0)
			.sort((a, b) => b[1].wrong - a[1].wrong)
			.slice(0, 8)
			.map(([key, s]) => ({ label: key.split(':').pop()!.replace(/^[hk]-/, ''), wrong: s.wrong }))
	);
</script>

<div class="page">
	<h1 class="page-title">일본어 학습 🎌</h1>
	<p class="page-sub">기록은 계정에 쌓이고, 매일 조금씩. 오늘 할 것부터.</p>

	{#if !loaded}
		<p class="page-sub" style="margin-top:30px">불러오는 중…</p>
	{:else}
		<!-- 오늘의 세트 -->
		{#if sets.length}
			<section class="block">
				<div class="block-h">오늘의 세트 {#if pending.length}· {pending.length}개 남음{:else}· 모두 완료 🎉{/if}</div>
				<div class="setlist">
					{#each pending as s (s.id)}
						<div class="set-row">
							<div class="set-t">{s.title}</div>
							<div class="set-meta">{s.count}문제 · {s.mode}</div>
							<div class="set-btns">
								<a class="mini accent" href={`/drill?set=${s.id}`}>시작</a>
								<button class="mini" disabled={busy === s.id} onclick={() => toggleDone(s.id, true)}>완료</button>
							</div>
						</div>
					{/each}
					{#each doneSets as s (s.id)}
						<div class="set-row done">
							<div class="set-t">✅ {s.title}</div>
							<div class="set-btns">
								<a class="mini" href={`/drill?set=${s.id}`}>다시</a>
								<button class="mini ghost" disabled={busy === s.id} onclick={() => toggleDone(s.id, false)}>완료취소</button>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- 복습 대기 -->
		{#if dueEntries.length}
			<section class="block">
				<div class="block-h">복습 대기 — 복습 시점이 된 항목</div>
				<div class="setlist">
					{#each dueEntries as [deck, n] (deck)}
						<div class="set-row">
							<div class="set-t">{deckTitle(deck)} — {n}개 대기</div>
							<div class="set-btns"><a class="mini accent" href={`/drill?deck=${deck}`}>복습 시작</a></div>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- 현황 -->
		<section class="block">
			<div class="block-h">현황 &nbsp;<a class="more" href="/history">기록 전체 보기 →</a></div>
			<div class="stat-row">
				<div class="stat"><b>{streak}</b><span>연속 학습일</span></div>
				<div class="stat"><b>{todayCount}</b><span>오늘 푼 문제</span></div>
				<div class="stat"><b>{total}</b><span>누적 문제</span></div>
			</div>
			<div class="weakline">
				{#if weak.length}
					<b>약한 항목:</b>
					{#each weak as w (w.label)}<span class="wk"><span class="jp">{w.label}</span>({w.wrong})</span> {/each}
				{:else}
					아직 약점 기록 없음 — 훈련을 시작해보자.
				{/if}
			</div>
		</section>

		<!-- 자유 연습 덱 -->
		<section class="block">
			<div class="block-h">훈련 덱 (자유 연습)</div>
			<div class="grid">
				{#each decks as d (d.id)}
					<a class="card" href={`/browse?deck=${d.id}`}>
						<div class="set-t">{d.title}</div>
						<div class="set-meta">{d.description}</div>
						<div class="count">{d.count}개</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	.block { margin-top: 26px; }
	.block-h { font-size: 14px; font-weight: 700; color: var(--sub); letter-spacing: 0.02em; margin-bottom: 12px; display: flex; align-items: baseline; }
	.more { font-size: 12.5px; color: var(--accent); font-weight: 600; }

	.setlist { display: flex; flex-direction: column; gap: 8px; }
	.set-row { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 6px 12px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; }
	.set-row.done { opacity: 0.6; }
	.set-t { font-size: 16px; font-weight: 600; line-height: 1.4; word-break: keep-all; grid-column: 1; }
	.set-meta { grid-column: 1; grid-row: 2; color: var(--sub); font-size: 13px; }
	.set-btns { grid-column: 2; grid-row: 1 / span 2; display: flex; gap: 8px; flex-shrink: 0; }
	.mini { display: inline-flex; align-items: center; padding: 9px 16px; border-radius: 9px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; font-size: 15px; font-weight: 600; }
	.mini:hover { border-color: var(--text); }
	.mini.accent { background: var(--accent); border-color: var(--accent); color: #fff; }
	.mini.ghost { color: var(--sub); }
	.mini:disabled { opacity: 0.5; cursor: default; }

	.stat-row { display: flex; gap: 10px; margin-bottom: 12px; }
	.stat { flex: 1; text-align: center; padding: 14px 4px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; }
	.stat b { display: block; font-size: 28px; font-weight: 800; font-variant-numeric: tabular-nums; }
	.stat span { font-size: 12.5px; color: var(--sub); }
	.weakline { font-size: 15px; line-height: 1.9; color: var(--text); }
	.weakline .wk { white-space: nowrap; margin-right: 4px; }
	.weakline .jp { font-family: var(--jp); font-size: 19px; }

	.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
	.card { display: block; background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; }
	.card:hover { border-color: var(--accent); }
	.card .set-meta { margin-top: 6px; }
	.count { color: var(--accent); font-size: 13px; font-weight: 700; margin-top: 10px; font-variant-numeric: tabular-nums; }

	@media (max-width: 480px) {
		.stat b { font-size: 24px; }
	}
</style>
