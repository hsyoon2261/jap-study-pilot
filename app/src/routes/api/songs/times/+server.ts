import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
export const prerender = false;

const KST = 32400000;

async function isAdmin(db: any, uid: string | null): Promise<boolean> {
	if (!db || !uid) return false;
	const row: any = await db.prepare('SELECT username FROM users WHERE id=?').bind(uid).first();
	return row?.username === 'admin';
}

// 탭 싱크 결과(lineTimes) 저장. admin 전용.
export async function POST({ request, platform, cookies }) {
	const db = platform?.env?.DB;
	const uid = await verifySid(cookies.get('sid'));
	if (!(await isAdmin(db, uid))) return json({ ok: false, error: 'admin만 가능해.' }, { status: 403 });

	const { id, times } = await request.json();
	if (!id || !Array.isArray(times) || !times.length) return json({ ok: false, error: 'id와 times가 필요해.' }, { status: 400 });
	const clean = times
		.map((t: any) => ({ start: Number(t.start), end: Number(t.end) }))
		.filter((t: any) => Number.isFinite(t.start) && Number.isFinite(t.end) && t.start >= 0 && t.end > t.start);
	if (!clean.length) return json({ ok: false, error: '유효한 타이밍이 없어.' }, { status: 400 });

	await db.prepare('CREATE TABLE IF NOT EXISTS song_times(song_id TEXT PRIMARY KEY, times TEXT NOT NULL, updated_by TEXT, updated_at TEXT)').run();
	const now = new Date(Date.now() + KST).toISOString().slice(0, 19);
	const jsonTimes = JSON.stringify(clean);
	await db.prepare('INSERT INTO song_times(song_id,times,updated_by,updated_at) VALUES(?,?,?,?) ON CONFLICT(song_id) DO UPDATE SET times=?,updated_by=?,updated_at=?')
		.bind(id, jsonTimes, uid, now, jsonTimes, uid, now).run();
	return json({ ok: true, count: clean.length });
}
