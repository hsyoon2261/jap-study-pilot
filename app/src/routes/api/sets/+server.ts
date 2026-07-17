import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
export const prerender = false;

const KST = 32400000; // UTC+9 (ms)
const nowKst = () => new Date(Date.now() + KST).toISOString().slice(0, 19);

// GET: 이 사용자의 세트 완료 상태 맵 { set_id: {done, doneAt} }
export async function GET({ platform, cookies }) {
	const uid = await verifySid(cookies.get('sid'));
	if (!uid) return json({ ok: false }, { status: 401 });
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false }, { status: 500 });
	const rows: any = await db.prepare('SELECT set_id,done,done_at FROM set_progress WHERE user_id=?').bind(uid).all();
	const map: Record<string, { done: boolean; doneAt: string | null }> = {};
	for (const r of rows.results || []) map[r.set_id] = { done: !!r.done, doneAt: r.done_at };
	return json({ ok: true, sets: map });
}

// POST {id, done}: 세트 완료 토글
export async function POST({ request, platform, cookies }) {
	const uid = await verifySid(cookies.get('sid'));
	if (!uid) return json({ ok: false }, { status: 401 });
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false }, { status: 500 });
	const { id, done } = await request.json();
	if (!id) return json({ ok: false, error: 'no id' }, { status: 400 });
	const d = done ? 1 : 0;
	const at = done ? nowKst() : null;
	await db.prepare('INSERT INTO set_progress(user_id,set_id,done,done_at) VALUES(?,?,?,?) ON CONFLICT(user_id,set_id) DO UPDATE SET done=?,done_at=?')
		.bind(uid, id, d, at, d, at).run();
	return json({ ok: true });
}
