import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
export const prerender = false;

const KST = 32400000;

async function isAdmin(db: any, uid: string | null): Promise<boolean> {
	if (!uid) return false;
	const row: any = await db.prepare('SELECT username FROM users WHERE id=?').bind(uid).first();
	return row?.username === 'admin';
}

// GET ?id=곡id → 그 곡의 붙여넣은 가사 / id 없으면 붙여넣은 곡 목록
export async function GET({ url, platform }) {
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false }, { status: 500 });
	const id = url.searchParams.get('id');
	if (id) {
		const row: any = await db.prepare('SELECT lyric, updated_at FROM song_lyrics WHERE song_id=?').bind(id).first();
		return json({ ok: true, lyric: row?.lyric ?? null, updatedAt: row?.updated_at ?? null });
	}
	const rows: any = await db.prepare('SELECT song_id, updated_at FROM song_lyrics').all();
	const pasted: Record<string, string> = {};
	for (const r of rows.results || []) pasted[r.song_id] = r.updated_at;
	return json({ ok: true, pasted });
}

// POST {id, lyric} → admin만. 붙여넣은 가사 저장(upsert).
export async function POST({ request, platform, cookies }) {
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false }, { status: 500 });
	const uid = await verifySid(cookies.get('sid'));
	if (!(await isAdmin(db, uid))) return json({ ok: false, error: 'admin만 가능해.' }, { status: 403 });
	const { id, lyric } = await request.json();
	if (!id || !lyric || !String(lyric).trim()) return json({ ok: false, error: '곡과 가사가 필요해.' }, { status: 400 });
	const now = new Date(Date.now() + KST).toISOString().slice(0, 19);
	await db.prepare('INSERT INTO song_lyrics(song_id,lyric,updated_by,updated_at) VALUES(?,?,?,?) ON CONFLICT(song_id) DO UPDATE SET lyric=?,updated_by=?,updated_at=?')
		.bind(id, lyric, uid, now, lyric, uid, now).run();
	return json({ ok: true });
}
