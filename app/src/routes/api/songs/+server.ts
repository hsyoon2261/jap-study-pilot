import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
import songsData from '$lib/data/songs.json';
export const prerender = false;

// 곡 데이터(가사 포함)는 public static에서 뺐다. 로그인한 사용자에게만 서빙.
export async function GET({ platform, cookies }) {
	const uid = await verifySid(cookies.get('sid'));
	if (!uid) return json({ ok: false, error: '로그인이 필요해.' }, { status: 401 });

	const db = platform?.env?.DB;
	// D1에 붙여넣은/불러온 원문(아직 해설 전)을 병합해서 노래 탭에서 바로 보이게
	const pasted: Record<string, string> = {};
	if (db) {
		try {
			const rows: any = await db.prepare('SELECT song_id, lyric FROM song_lyrics').all();
			for (const r of rows.results || []) pasted[r.song_id] = r.lyric;
		} catch { /* song_lyrics 없을 수 있음 */ }
	}

	const songs = (songsData as any[]).map((s) => {
		const { _unmerged, ...clean } = s; // 소절 나누기 전 백업 잔재는 응답에서 제외
		if (!clean.lyric && pasted[clean.id]) clean.pastedLyric = pasted[clean.id];
		return clean;
	});
	return json({ ok: true, songs });
}
