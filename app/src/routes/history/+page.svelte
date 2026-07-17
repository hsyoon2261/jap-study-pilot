<script lang="ts">
	import { onMount } from 'svelte';
	import { getSrs } from '$lib/progress';

	type Log = { ts: string; correct: boolean };
	type Item = { id: string; front: string; back: string; ko?: string };

	const KST = 32400000;

	let itemMap: Record<string, Item> = {};
	let loaded = $state(false);
	let srs = $state<Record<string, { box:number; right:number; wrong:number }>>({});
	let total = $state(0);
	let correctN = $state(0);
	let byDay = $state<{ d:string; n:number; ok:number; pct:number }[]>([]);

	onMount(async () => {
		let ok = false;
		try {
			const st = await fetch('/api/state').then(r => r.ok ? r.json() : null);
			if (st?.ok) {
				total = st.total; correctN = st.correct; srs = st.srs || {};
				byDay = (st.byDay || []).map((r: any) => ({ d: r.d, n: r.n, ok: r.ok, pct: r.n ? Math.round(r.ok*100/r.n) : 0 }));
				ok = true;
			}
		} catch { /* 폴백 */ }
		if (!ok) {
			// 오프라인·비로그인 폴백: 로컬 기록
			let logs: Log[] = [];
			try { logs = JSON.parse(localStorage.getItem('jsp_logs_v1') || '[]'); } catch { logs = []; }
			total = logs.length; correctN = logs.filter(l => l.correct).length; srs = getSrs();
			const m: Record<string, {n:number; ok:number}> = {};
			for (const l of logs) { const d = (l.ts||'').slice(0,10); if (!d) continue; (m[d] ||= {n:0,ok:0}); m[d].n++; if (l.correct) m[d].ok++; }
			byDay = Object.entries(m).sort().map(([d,v]) => ({ d, n:v.n, ok:v.ok, pct: Math.round(v.ok*100/v.n) }));
		}
		const decks = await Promise.all(['kana','hiragana-words','katakana-words'].map(id =>
			fetch(`/content/${id}.json`).then(r => r.json()).catch(() => ({items:[]}))));
		for (const d of decks) for (const it of (d.items||[])) itemMap[(d.id||'')+':'+it.id] = it;
		loaded = true;
	});

	const pct = $derived(total ? Math.round(correctN/total*100) : 0);
	const days = $derived(byDay.length);
	const streak = $derived.by(() => {
		const set = new Set(byDay.map(x => x.d));
		let s = 0; const dt = new Date(Date.now() + KST);
		const today = new Date(Date.now() + KST).toISOString().slice(0,10);
		for (;;) { const key = dt.toISOString().slice(0,10); if (set.has(key)) { s++; dt.setUTCDate(dt.getUTCDate()-1); } else if (s===0 && key===today) { dt.setUTCDate(dt.getUTCDate()-1); } else break; }
		return s;
	});
	const weak = $derived.by(() =>
		Object.entries(srs).filter(([,v]) => v.wrong>0).sort((a,b) => b[1].wrong-a[1].wrong).slice(0,15)
			.map(([k,v]) => ({ it: itemMap[k], wrong: v.wrong, box: v.box }))
	);
</script>

<div class="page">
	<h1 class="page-title">기록 📊</h1>
	<p class="page-sub">계정에 쌓인 학습 기록. 매일 조금씩 늘려가자.</p>

	{#if !loaded}
		<p class="page-sub">불러오는 중…</p>
	{:else if !total}
		<p class="page-sub" style="margin-top:24px">아직 기록이 없어. 홈에서 세트 하나 풀면 여기 쌓인다.</p>
	{:else}
		<div class="cards">
			<div class="c"><div class="n">{total}</div><div class="k">총 답안</div></div>
			<div class="c"><div class="n ok">{pct}%</div><div class="k">정답률</div></div>
			<div class="c"><div class="n">{days}</div><div class="k">학습한 날</div></div>
			<div class="c"><div class="n ac">{streak}</div><div class="k">연속 학습</div></div>
		</div>

		<div class="h2">날짜별 정답률</div>
		<div class="tbl">
			{#each byDay as r (r.d)}<div class="tr"><span>{r.d}</span><span>{r.n}문제</span><span class="ac">{r.ok} ({r.pct}%)</span></div>{/each}
		</div>

		{#if weak.length}
			<div class="h2">자주 틀린 것</div>
			<div class="tbl">
				{#each weak as w (w.it?.id || Math.random())}
					<div class="tr"><span class="jp">{w.it?.front || '?'}</span><span>{w.it ? `${w.it.back}${w.it.ko?` (${w.it.ko})`:''}` : ''}</span><span class="no">오답 {w.wrong}</span></div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.cards { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin: 20px 0 8px; }
	@media (max-width: 560px) { .cards { grid-template-columns: 1fr 1fr; } }
	.c { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
	.c .n { font-size: 28px; font-weight: 800; font-variant-numeric: tabular-nums; }
	.c .n.ok { color: var(--ok); } .c .n.ac { color: var(--accent); }
	.c .k { color: var(--sub); font-size: 13px; margin-top: 2px; }
	.h2 { font-size: 15px; color: var(--accent); font-weight: 700; margin: 26px 0 10px; }
	.tbl { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
	.tr { display: flex; justify-content: space-between; gap: 10px; padding: 11px 15px; border-top: 1px solid var(--border); font-size: 14.5px; }
	.tr:first-child { border-top: none; }
	.tr .jp { font-family: var(--jp); font-size: 19px; }
	.tr .ac { color: var(--ok); font-variant-numeric: tabular-nums; }
	.tr .no { color: var(--accent); }
</style>
