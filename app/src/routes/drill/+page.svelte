<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { speak } from '$lib/audio';
	import { getSrs, srsKey, nowIso, recordAnswer } from '$lib/progress';

	type Item = { id: string; front: string; back: string; ko?: string; origin?: string; tags: string[] };
	type Deck = { id: string; title: string; vocab?: boolean; tagGroups: { name: string; tags: string[] }[]; items: Item[] };
	type StudySet = { id: string; title: string; deck: string; mode: string; count: number; tags?: Record<string, string[]>; itemIds?: string[] };

	const ROMAJI_ALT: Record<string, string[]> = {
		shi: ['si'], chi: ['ti'], tsu: ['tu'], fu: ['hu'], ji: ['zi', 'di'], zu: ['du'],
		sha: ['sya'], shu: ['syu'], sho: ['syo'], cha: ['tya'], chu: ['tyu'], cho: ['tyo'],
		ja: ['zya', 'jya'], ju: ['zyu', 'jyu'], jo: ['zyo', 'jyo']
	};
	const shuffle = <T,>(a: T[]) => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

	let phase = $state<'loading' | 'quiz' | 'result'>('loading');
	let errorMsg = $state('');
	let deck: Deck | null = null;
	let cfg: { mode: string; count: number; tags?: Record<string, string[]>; itemIds?: string[]; title: string } | null = null;
	let queue: { item: Item; mode: string }[] = [];
	let idx = $state(0);
	let correct = $state(0);
	let wrong: Item[] = [];
	let answered = $state(false);

	// 현재 문제 뷰모델
	let promptText = $state('');
	let promptClass = $state('');
	let subHtml = $state('');
	let choices = $state<{ item: Item; label: string; correct: boolean; cls: string }[]>([]);
	let mode = $state('');
	let showTyping = $state(false);
	let showPlay = $state(false);
	let typingValue = $state('');
	let feedbackHtml = $state('');
	let hintText = $state('');
	let qStart = 0;
	let typingEl = $state<HTMLInputElement | null>(null);
	// 서버(D1) SRS — 로그인 사용자의 실제 복습 상태. buildQueue의 due·약점 가중에 사용.
	let srsData: Record<string, { box: number; right: number; wrong: number; due: string }> = {};

	function filteredItems(): Item[] {
		if (!deck) return [];
		const tags = cfg?.tags;
		return deck.items.filter((it) => {
			if (!tags) return true;
			for (const g of deck!.tagGroups || []) {
				const sel = tags[g.name];
				if (!sel) continue;
				const groupTags = it.tags.filter((t) => g.tags.includes(t));
				if (groupTags.length && !groupTags.some((t) => sel.includes(t))) return false;
			}
			return true;
		});
	}

	function buildQueue(): { item: Item; mode: string }[] | null {
		if (!deck || !cfg) return null;
		if (filteredItems().length < 4) return null;
		let pool = filteredItems();
		if (cfg.itemIds && cfg.itemIds.length) {
			const set = new Set(cfg.itemIds);
			pool = pool.filter((it) => set.has(it.id));
		}
		if (!pool.length) return null;
		const srs = Object.keys(srsData).length ? srsData : getSrs();
		const now = nowIso();
		const due: Item[] = [], fresh: Item[] = [], rest: Item[] = [];
		for (const it of pool) {
			const s = srs[srsKey(deck.id, it.id)];
			if (!s) fresh.push(it);
			else if (s.due <= now) due.push(it);
			else rest.push(it);
		}
		shuffle(due); shuffle(fresh);
		const weighted: Item[] = [];
		for (const it of rest) { const s = srs[srsKey(deck.id, it.id)]; const w = 1 + Math.min(5, s ? s.wrong : 0); for (let i = 0; i < w; i++) weighted.push(it); }
		shuffle(weighted);
		const picked: Item[] = [], seen = new Set<string>();
		for (const src of [due, fresh, weighted]) for (const it of src) { if (picked.length >= cfg.count) break; if (seen.has(it.id)) continue; seen.add(it.id); picked.push(it); }
		while (picked.length < cfg.count && pool.length) picked.push(pool[Math.floor(Math.random() * pool.length)]);
		const pickMix = () => ['f2b', 'b2f', 'typing', 'listen'][Math.floor(Math.random() * 4)];
		return picked.map((it) => ({ item: it, mode: cfg!.mode === 'mix' ? pickMix() : cfg!.mode }));
	}

	function makeChoices(target: Item, label: (c: Item) => string, isCorrect: (c: Item) => boolean) {
		const seenB = new Set([target.back]);
		const distractors: Item[] = [];
		for (const it of shuffle([...filteredItems()])) { if (distractors.length >= 3) break; if (seenB.has(it.back)) continue; seenB.add(it.back); distractors.push(it); }
		return shuffle([target, ...distractors]).map((c) => ({ item: c, label: label(c), correct: isCorrect(c), cls: '' }));
	}

	function render() {
		const q = queue[idx];
		if (!q) return;
		answered = false;
		qStart = Date.now();
		mode = q.mode;
		const item = q.item;
		promptText = ''; promptClass = ''; subHtml = ''; choices = []; showTyping = false; showPlay = false;
		feedbackHtml = ''; hintText = ''; typingValue = '';
		const vocab = !!deck?.vocab;
		const jp = (c: Item) => `${c.front}<small>${c.back}</small>`;
		const same = (c: Item) => c.id === item.id;

		if (q.mode === 'f2b') {
			if (vocab) { promptText = item.front; promptClass = 'word'; subHtml = `<span class="reading">${item.back}</span> · 뜻은?`; choices = makeChoices(item, (c) => c.ko || c.back, same); }
			else { promptText = item.front; subHtml = '발음/뜻은?'; choices = makeChoices(item, (c) => `${c.back}${c.ko ? `<small>${c.ko}</small>` : ''}`, (c) => c.back === item.back); }
		} else if (q.mode === 'b2f') {
			if (vocab) { promptText = item.ko || item.back; promptClass = 'roman'; subHtml = '맞는 일본어는?'; choices = makeChoices(item, jp, same); }
			else { promptText = item.back + (item.ko ? ` (${item.ko})` : ''); promptClass = 'roman'; subHtml = '맞는 글자는?'; choices = makeChoices(item, (c) => c.front, (c) => c.back === item.back); }
		} else if (q.mode === 'typing') {
			promptText = item.front; if (vocab) promptClass = 'word'; subHtml = '로마자로 입력'; showTyping = true;
			setTimeout(() => typingEl?.focus(), 30);
		} else if (q.mode === 'listen') {
			promptText = '🎧'; subHtml = vocab ? '들은 단어는? (🔊 다시 듣기)' : '들은 글자는? (🔊 다시 듣기)'; showPlay = true;
			choices = makeChoices(item, vocab ? jp : (c) => c.front, vocab ? same : (c) => c.back === item.back);
			setTimeout(() => speak(item.front), 250);
		} else if (q.mode === 'flash') {
			promptText = item.front; if (vocab) promptClass = 'word'; subHtml = `<span class="reading">${item.back}</span>${item.ko ? ` · ${item.ko}` : ''}`; showPlay = true;
			feedbackHtml = item.origin ? `<span class="dim">유래 ${item.origin}</span>` : '';
			hintText = '보고 소리 들었으면 · 클릭 또는 Enter로 다음';
			answered = true;
			setTimeout(armNext, 120);
			setTimeout(() => speak(item.front), 250);
		}
	}

	function finish(isCorrect: boolean, item: Item, picked?: Item) {
		if (isCorrect) correct++; else wrong.push(item);
		recordAnswer(deck!.id, item.id, mode, isCorrect, Date.now() - qStart);
		const pickedLine = !isCorrect && picked && picked.id !== item.id
			? `<div class="picked">고른 답 <b>${picked.front}</b> = ${picked.back}${picked.ko ? ` (${picked.ko})` : ''}</div>` : '';
		feedbackHtml = (isCorrect ? `<span class="ok">정답!</span>` : `<span class="no">오답.</span>`) +
			` ${item.front} = ${item.back}${item.ko ? ` (${item.ko})` : ''}${item.origin ? ` · ${item.origin} 유래` : ''}` + pickedLine;
		hintText = '클릭 또는 Enter로 다음';
		setTimeout(armNext, 60);
	}

	function pickChoice(ci: number) {
		if (answered) return;
		answered = true;
		const item = queue[idx].item;
		const chosen = choices[ci];
		choices = choices.map((c, i) => ({ ...c, cls: i === ci ? (c.correct ? 'correct' : 'wrong') : (!chosen.correct && c.correct ? 'correct' : '') }));
		finish(chosen.correct, item, chosen.item);
	}

	function submitTyping() {
		if (answered) return;
		const item = queue[idx].item;
		const raw = typingValue.trim().toLowerCase();
		if (!raw) return;
		answered = true;
		const ok = raw === item.back || (ROMAJI_ALT[item.back] || []).includes(raw) || (!!item.ko && raw === item.ko);
		finish(ok, item);
	}

	function nextOnEnter(e: KeyboardEvent) { if (e.key === 'Enter') { e.preventDefault(); goNext(); } }
	function armNext() { document.addEventListener('click', goNext, { once: true }); document.addEventListener('keydown', nextOnEnter); }
	function goNext() {
		document.removeEventListener('keydown', nextOnEnter);
		document.removeEventListener('click', goNext);
		if (!answered) return;
		idx++;
		if (idx >= queue.length) phase = 'result';
		else render();
	}

	onDestroy(() => { document.removeEventListener('keydown', nextOnEnter); document.removeEventListener('click', goNext); });

	onMount(async () => {
		const setId = page.url.searchParams.get('set');
		const deckId = page.url.searchParams.get('deck');
		try {
			if (setId) {
				const sets: StudySet[] = await fetch('/content/sets.json').then((r) => r.json());
				const s = sets.find((x) => x.id === setId);
				if (!s) { errorMsg = '세트를 찾을 수 없어.'; phase = 'result'; return; }
				deck = await fetch(`/content/${s.deck}.json`).then((r) => r.json());
				cfg = { mode: s.mode, count: s.count, tags: s.tags, itemIds: s.itemIds, title: s.title };
			} else if (deckId) {
				deck = await fetch(`/content/${deckId}.json`).then((r) => r.json());
				cfg = { mode: deck!.vocab ? 'f2b' : 'f2b', count: 20, title: deck!.title };
			} else { errorMsg = '무엇을 공부할지 지정되지 않았어.'; phase = 'result'; return; }
		} catch {
			errorMsg = '콘텐츠를 못 불러왔어.'; phase = 'result'; return;
		}
		// 서버 SRS 로드 (복습 우선·약점 가중). 실패(비로그인·오프라인)면 로컬 폴백.
		try {
			const st = await fetch('/api/state').then((r) => (r.ok ? r.json() : null));
			if (st?.srs) srsData = st.srs;
		} catch { /* 로컬 getSrs() 폴백 */ }
		const q = buildQueue();
		if (!q) { errorMsg = '범위가 너무 좁아 (보기 4개를 못 만들어).'; phase = 'result'; return; }
		queue = q; idx = 0; correct = 0; wrong = [];
		phase = 'quiz'; render();
	});

	const total = $derived(queue.length);
	const pct = $derived(total ? Math.round((correct / total) * 100) : 0);
	const isFlash = $derived(cfg?.mode === 'flash');
	const uniqWrong = $derived([...new Map(wrong.map((it) => [it.id, it])).values()]);
</script>

<div class="drill-shell">
	{#if phase === 'loading'}
		<div class="quiz-card centered"><p class="muted">불러오는 중…</p></div>
	{:else if phase === 'quiz'}
		<div class="quiz-card">
			<div class="top">
				<span>{idx + 1} / {total}</span>
				<span class="score">정답 {correct}</span>
			</div>
			<div class="bar"><span style="width:{total ? (idx / total) * 100 : 0}%"></span></div>
			<div class="body">
				<div class="prompt {promptClass}">{promptText}</div>
				<div class="sub">{@html subHtml}</div>

				{#if showPlay}
					<button class="play" onclick={(e) => { e.stopPropagation(); speak(queue[idx].item.front); }}>🔊 다시 듣기</button>
				{/if}

				{#if choices.length}
					<div class="choices">
						{#each choices as c, i (i)}
							<button class="choice {c.cls}" disabled={answered} onclick={() => pickChoice(i)}>{@html c.label}</button>
						{/each}
					</div>
				{/if}

				{#if showTyping}
					<div class="typing">
						<input bind:this={typingEl} bind:value={typingValue} disabled={answered}
							onkeydown={(e) => { if (e.key === 'Enter') submitTyping(); }} placeholder="로마자 입력 후 Enter" autocomplete="off" />
						<button onclick={submitTyping} disabled={answered}>확인</button>
					</div>
				{/if}
			</div>
			<div class="foot">
				<div class="feedback">{@html feedbackHtml}</div>
				<div class="hint">{hintText}</div>
			</div>
		</div>
	{:else}
		<div class="quiz-card result">
			<h1 class="score-big">{errorMsg ? '⚠' : (isFlash ? `${total}자 👀` : `${correct} / ${total}`)}</h1>
			{#if errorMsg}
				<p class="muted">{errorMsg}</p>
			{:else if isFlash}
				<p class="muted">다 봤어! 눈과 귀에 익혔으면 이제 퀴즈로 확인해보자.</p>
			{:else}
				<p class="muted">{pct >= 90 ? `정답률 ${pct}% — すごい！🎉` : pct >= 70 ? `정답률 ${pct}% — 좋아, 틀린 것만 다시 잡자` : `정답률 ${pct}% — 괜찮아, 반복이 답이다`}</p>
				{#if uniqWrong.length}
					<div class="weak">
						<div class="block-h">다시 볼 것 (복습 대기열로)</div>
						{#each uniqWrong as it (it.id)}
							<div class="wrow"><span class="jp">{it.front}</span><span>{it.back}{it.ko ? ` (${it.ko})` : ''}</span></div>
						{/each}
					</div>
				{/if}
			{/if}
			<div class="actions"><a class="btn" href="/">← 오늘로</a></div>
		</div>
	{/if}
</div>

<style>
	/* 집중형 카드: 화면 중앙, 폭 제한 (보기 버튼이 과하게 넓어지지 않게) */
	.drill-shell {
		min-height: calc(100dvh - 44px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 22px 18px;
	}
	.quiz-card {
		width: 100%;
		max-width: 560px;
		min-height: 500px;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 18px;
		padding: 22px 26px 20px;
		display: flex;
		flex-direction: column;
	}
	.quiz-card.centered { align-items: center; justify-content: center; }
	.muted { color: var(--sub); font-size: 15px; }
	.body { flex: 1; display: flex; flex-direction: column; justify-content: center; }
	.foot { margin-top: auto; }
	.bar { height: 4px; border-radius: 4px; background: var(--btn); overflow: hidden; margin-bottom: 6px; }
	.bar span { display: block; height: 100%; background: var(--accent); transition: width .25s ease; }
	.top { display: flex; justify-content: space-between; color: var(--sub); font-size: 13px; margin-bottom: 10px; font-variant-numeric: tabular-nums; }
	.top .score { color: var(--ok); }
	.prompt { text-align: center; font-size: 92px; font-weight: 500; padding: 12px 0 6px; font-family: var(--jp); line-height: 1.1; }
	.prompt.roman { font-size: 46px; padding: 24px 0 14px; }
	.prompt.word { font-size: 58px; padding: 18px 0 4px; }
	.sub { text-align: center; color: var(--sub); font-size: 16px; margin-bottom: 22px; min-height: 20px; }
	.sub :global(.reading) { color: var(--accent); font-size: 23px; font-weight: 600; }
	.play { display: block; margin: 0 auto 20px; padding: 16px 30px; font-size: 28px; border-radius: 50px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; }
	.choices { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
	.choice { padding: 18px 8px; font-size: 27px; border-radius: 10px; border: 1px solid var(--border); background: var(--btn); color: var(--text); cursor: pointer; font-family: var(--jp); }
	.choice :global(small) { display: block; font-size: 15px; color: var(--sub); margin-top: 3px; }
	.choice.correct { background: var(--ok-soft); border-color: var(--ok); }
	.choice.wrong { background: rgba(229,115,95,.16); border-color: var(--accent); }
	.choice:disabled { cursor: default; }
	.typing { display: flex; gap: 10px; justify-content: center; }
	.typing input { flex: 1; max-width: 420px; padding: 14px 16px; font-size: 20px; border-radius: 10px; border: 1px solid var(--border); background: var(--btn); color: var(--text); }
	.typing button { padding: 14px 22px; font-size: 17px; border: none; border-radius: 10px; background: var(--text); color: #14161b; font-weight: 700; cursor: pointer; }
	.feedback { text-align: center; margin-top: 16px; font-size: 18px; min-height: 26px; }
	.feedback :global(.ok) { color: var(--ok); font-weight: 700; }
	.feedback :global(.no) { color: var(--accent); font-weight: 700; }
	.feedback :global(.picked) { color: var(--sub); font-size: 15px; margin-top: 6px; }
	.feedback :global(.picked b) { color: var(--accent); }
	.feedback :global(.dim) { color: var(--sub); }
	.hint { text-align: center; color: var(--sub); font-size: 12px; margin-top: 8px; min-height: 16px; }
	/* 결과 카드 */
	.quiz-card.result { justify-content: center; text-align: center; }
	.score-big { font-size: 46px; font-weight: 800; letter-spacing: -0.01em; margin-bottom: 6px; }
	.result .muted { margin-bottom: 4px; }
	.weak { margin-top: 22px; text-align: left; background: var(--btn); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
	.block-h { font-size: 13px; font-weight: 700; color: var(--sub); margin-bottom: 8px; }
	.wrow { display: flex; justify-content: space-between; padding: 8px 0; border-top: 1px solid var(--border); }
	.wrow .jp { font-family: var(--jp); font-size: 22px; }
	.actions { margin-top: 24px; }
	.btn { display: inline-block; padding: 12px 22px; border-radius: 10px; border: 1px solid var(--border); background: var(--btn); color: var(--accent); font-weight: 700; }

	/* 모바일: 카드가 폭을 꽉 채우고 위에서부터 (하단 탭바 고려) */
	@media (max-width: 700px) {
		.drill-shell { min-height: 0; align-items: stretch; padding: 14px 12px 20px; }
		.quiz-card { max-width: none; min-height: calc(100dvh - 100px); border-radius: 16px; padding: 18px 18px 16px; }
		.prompt { font-size: 78px; }
		.prompt.word { font-size: 50px; }
		.prompt.roman { font-size: 40px; }
		.choice { font-size: 24px; padding: 16px 6px; }
	}
</style>
