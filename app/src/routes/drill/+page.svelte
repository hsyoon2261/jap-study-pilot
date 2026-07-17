<script lang="ts">
	import { page } from '$app/state';
	const setId = $derived(page.url.searchParams.get('set') ?? '');
</script>

<div class="page">
	<h1 class="page-title">드릴</h1>
	<p class="page-sub">세트 <b>{setId || '—'}</b> · 이 학습 화면은 다음 단계(P2)에서 이식됩니다. 뜻·글자·익숙해지기 모드와 채점, SRS까지 그대로 옮깁니다.</p>
	<p class="page-sub" style="margin-top:14px"><a href="/" style="color:var(--accent)">← 오늘로</a></p>
</div>
