<script lang="ts">
	import { page } from '$app/state';
	const deckId = $derived(page.url.searchParams.get('deck') ?? '');
</script>

<div class="page">
	<h1 class="page-title">덱 열람 📚</h1>
	<p class="page-sub">덱 <b>{deckId || '—'}</b> · 단어를 훑어보고 발음을 듣는 화면. P2에서 이식됩니다.</p>
</div>
