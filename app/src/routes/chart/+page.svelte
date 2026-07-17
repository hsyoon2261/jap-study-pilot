<script lang="ts">
	import { onMount } from 'svelte';
	import { speak } from '$lib/audio';

	type Item = { id: string; front: string; back: string; ko?: string; origin?: string; tags: string[] };
	type Deck = { items: Item[] };

	const BASIC = ['あ행','か행','さ행','た행','な행','は행','ま행','や행','ら행','わ행·ん','が행','ざ행','だ행','ば행','ぱ행'];
	const YOON = ['요음','요음(탁)'];

	let deck = $state<Deck | null>(null);
	let words: Item[] = [];
	let tab = $state<'hira'|'kata'|'yoon'|'rules'>('hira');
	let sel = $state<Item | null>(null);
	let examples = $state<Item[]>([]);

	onMount(async () => {
		deck = await fetch('/content/kana.json').then(r => r.json());
		const [h, k] = await Promise.all([
			fetch('/content/hiragana-words.json').then(r => r.json()).catch(() => ({items:[]})),
			fetch('/content/katakana-words.json').then(r => r.json()).catch(() => ({items:[]}))
		]);
		words = [...(h.items||[]), ...(k.items||[])];
	});

	function rowsFor(script: string, rows: string[]) {
		if (!deck) return [];
		return rows.map(row => ({
			row,
			items: deck!.items.filter(it => it.tags.includes(row) && it.tags.includes(script))
		})).filter(g => g.items.length);
	}

	function open(it: Item) {
		sel = it;
		examples = words.filter(w => (w.front||'').includes(it.front)).slice(0, 8);
		speak(it.front);
	}

	function originText(it: Item): string {
		const kata = it.tags.includes('가타카나');
		if (it.origin) return kata
			? `가타카나 <b>${it.front}</b> — 한자 <b>${it.origin}</b>의 일부를 딴 글자.`
			: `히라가나 <b>${it.front}</b> — 한자 <b>${it.origin}</b>의 흘림체에서 왔다.`;
		if (it.tags.some(t => t.includes('요음'))) return `<b>${it.front}</b> — い단 글자 + 작은 ゃ/ゅ/ょ를 <b>한 박자</b>로.`;
		return `<b>${it.front}</b> — 소리 내어 여러 번 따라 읽자.`;
	}
</script>

<div class="page" class:shift={sel}>
	<h1 class="page-title">가나 학습표 📖</h1>
	<p class="page-sub">글자를 누르면 발음 재생 + 옆에 유래·예시 단어.</p>
	<div class="tabs">
		<button class:on={tab==='hira'} onclick={() => tab='hira'}>히라가나</button>
		<button class:on={tab==='kata'} onclick={() => tab='kata'}>가타카나</button>
		<button class:on={tab==='yoon'} onclick={() => tab='yoon'}>요음</button>
		<button class:on={tab==='rules'} onclick={() => tab='rules'}>촉음·장음·ん</button>
	</div>

	{#if !deck}
		<p class="page-sub">불러오는 중…</p>
	{:else if tab==='rules'}
		<div class="info">
			<h3>촉음 っ — 받침 같은 멈춤</h3>작은 っ는 한 박자 숨을 막는 소리(받침 ㅅ/ㄱ). 있고 없고로 뜻이 갈린다.
			<div class="pair">{#each [['きって','킷테·우표'],['きて','키테·와줘'],['ちょっと','춋토·잠깐'],['やった','얏타·앗싸']] as [w,m]}<button onclick={() => speak(w)}>{w} ({m}) 🔊</button>{/each}</div>
			<h3>장음 — 길게 늘이면 뜻이 바뀐다</h3>같은 모음이 이어지면 두 박자로 길게. 아주머니를 할머니로 만들지 말 것.
			<div class="pair">{#each [['おばさん','아주머니'],['おばあさん','할머니'],['おじさん','아저씨'],['おじいさん','할아버지']] as [w,m]}<button onclick={() => speak(w)}>{w} ({m}) 🔊</button>{/each}</div>
			<div class="lead">가타카나에서는 「ー」로 표기:</div>
			<div class="pair">{#each [['コーヒー','커피'],['ケーキ','케이크']] as [w,m]}<button onclick={() => speak(w)}>{w} ({m}) 🔊</button>{/each}</div>
			<h3>ん — 위치 따라 변하는 콧소리</h3>뒤 글자에 끌려 ㄴ/ㅁ/ㅇ 사이를 오간다.
			<div class="pair">{#each [['せんぱい','셈파이·선배'],['まんが','망가·만화'],['みんな','민나·모두']] as [w,m]}<button onclick={() => speak(w)}>{w} ({m}) 🔊</button>{/each}</div>
			<h3>요음 — 작은 ゃ ゅ ょ 조합</h3>い단 글자 + 작은 ゃ/ゅ/ょ를 한 박자로. 크기 차이로 뜻이 갈린다.
			<div class="pair">{#each [['びょういん','뵤-인·병원'],['びよういん','비요-인·미용실'],['きょう','쿄-·오늘'],['しゃしん','샤신·사진']] as [w,m]}<button onclick={() => speak(w)}>{w} ({m}) 🔊</button>{/each}</div>
		</div>
	{:else}
		{#each (tab==='yoon' ? [...rowsFor('히라가나',YOON), ...rowsFor('가타카나',YOON)] : rowsFor(tab==='hira'?'히라가나':'가타카나', BASIC)) as g (g.row)}
			<div class="rowblock">
				<div class="rowname">{g.row}</div>
				<div class="cells">
					{#each g.items as it (it.id)}
						<button class="cell" class:on={sel?.id===it.id} onclick={() => open(it)}>
							<span class="kana">{it.front}</span>
							<span class="sub2">{it.back} · {it.ko}</span>
							{#if it.origin}<span class="sub3">{it.origin}</span>{/if}
						</button>
					{/each}
				</div>
			</div>
		{/each}
	{/if}
</div>

{#if sel}
	<aside class="kpanel">
		<button class="kclose" onclick={() => sel=null}>✕ 닫기</button>
		<div class="kglyph">{sel.front}</div>
		<div class="kread">{sel.back}</div>
		<div class="kko">{sel.ko}</div>
		<button class="kplay" onclick={() => speak(sel!.front)}>🔊 소리 듣기</button>
		<div class="ksec"><div class="kh">유래·힌트</div><div class="korigin">{@html originText(sel)}</div></div>
		<div class="ksec"><div class="kh">이 글자가 든 단어</div>
			{#if examples.length}
				<div class="kwords">{#each examples as w (w.id)}<button class="kword" onclick={() => speak(w.front)}><span class="w">{w.front}</span><span class="r">{w.back}</span><span class="m">{w.ko||''}</span></button>{/each}</div>
			{:else}<div class="dim">등록 단어 없음.</div>{/if}
		</div>
	</aside>
{/if}

<style>
	.tabs { display: flex; gap: 8px; flex-wrap: wrap; margin: 14px 0 18px; }
	.tabs button { padding: 9px 16px; border-radius: 20px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; font-size: 15px; }
	.tabs button.on { background: var(--text); color: #14161b; font-weight: 700; }
	.rowblock { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; }
	.rowname { font-size: 14px; font-weight: 700; color: var(--sub); margin-bottom: 10px; }
	.cells { display: grid; grid-template-columns: repeat(5, 1fr); gap: 9px; }
	@media (max-width: 560px) { .cells { grid-template-columns: repeat(3, 1fr); } }
	.cell { text-align: center; padding: 12px 4px; background: var(--btn); border: 1px solid var(--border); border-radius: 10px; cursor: pointer; color: var(--text); }
	.cell.on { border-color: var(--accent); }
	.cell .kana { display: block; font-size: 40px; font-family: var(--jp); line-height: 1.1; }
	.cell .sub2 { display: block; font-size: 14px; color: var(--sub); margin-top: 4px; }
	.cell .sub3 { display: block; font-size: 12px; color: var(--accent); margin-top: 2px; font-family: var(--jp); }
	.info { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; font-size: 16px; line-height: 1.8; }
	.info h3 { color: var(--accent); font-size: 17px; margin: 14px 0 4px; }
	.info .lead { margin: 8px 0 2px; }
	.pair { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 8px; }
	.pair button { font-family: var(--jp); font-size: 17px; background: var(--btn); border: 1px solid var(--border); border-radius: 8px; padding: 5px 11px; cursor: pointer; color: var(--text); }
	.kpanel { position: fixed; top: 0; right: 0; bottom: 0; width: 380px; max-width: 92vw; background: var(--card); border-left: 1px solid var(--border); padding: 22px; overflow-y: auto; z-index: 60; box-shadow: -14px 0 40px rgba(0,0,0,.5); }
	@media (min-width: 1240px) { .page.shift { padding-right: 410px; } }
	.kclose { position: absolute; top: 16px; right: 16px; background: var(--btn); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 6px 12px; cursor: pointer; }
	.kglyph { font-size: 120px; text-align: center; font-family: var(--jp); line-height: 1.05; margin-top: 12px; }
	.kread { text-align: center; color: var(--accent); font-size: 30px; font-weight: 700; }
	.kko { text-align: center; color: var(--sub); font-size: 18px; }
	.kplay { display: block; margin: 16px auto 6px; padding: 12px 24px; font-size: 17px; border-radius: 40px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; }
	.ksec { margin-top: 20px; }
	.kh { color: var(--accent); font-size: 14px; font-weight: 700; margin-bottom: 7px; }
	.korigin { font-size: 16px; line-height: 1.7; }
	.korigin :global(b) { color: var(--text); }
	.kwords { display: flex; flex-direction: column; gap: 7px; }
	.kword { display: flex; align-items: baseline; gap: 10px; background: var(--btn); border: 1px solid var(--border); border-radius: 9px; padding: 9px 12px; cursor: pointer; color: var(--text); text-align: left; }
	.kword .w { font-family: var(--jp); font-size: 20px; }
	.kword .r { color: var(--accent); font-size: 13px; }
	.kword .m { color: var(--sub); font-size: 14px; margin-left: auto; }
	.dim { color: var(--sub); font-size: 14px; }
</style>
