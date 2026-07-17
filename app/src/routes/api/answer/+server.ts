import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
export const prerender = false;

const INTERVALS = [0, 1, 3, 7, 14, 30];
const KST = 32400000; // UTC+9 (ms) — 기록/집계는 한국 날짜 기준

export async function POST({ request, platform, cookies }) {
	const uid = await verifySid(cookies.get('sid'));
	if (!uid) return json({ ok: false }, { status: 401 });
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false }, { status: 500 });
	const { deck, item, mode, correct, ms } = await request.json();
	const now = new Date(Date.now() + KST).toISOString().slice(0, 19);
	await db.prepare('INSERT INTO answer_logs(user_id,deck,item_id,mode,correct,ms,ts) VALUES(?,?,?,?,?,?,?)')
		.bind(uid, deck, item, mode ?? null, correct ? 1 : 0, ms ?? null, now).run();
	const prev: any = await db.prepare('SELECT box,right_count,wrong_count FROM review_states WHERE user_id=? AND deck=? AND item_id=?')
		.bind(uid, deck, item).first();
	let box = prev?.box ?? 0, right = prev?.right_count ?? 0, wrong = prev?.wrong_count ?? 0;
	if (correct) { right++; box = Math.min(5, box + 1); } else { wrong++; box = Math.max(0, box - 1); }
	const due = new Date(Date.now() + KST + INTERVALS[box] * 86400000).toISOString().slice(0, 19);
	await db.prepare('INSERT INTO review_states(user_id,deck,item_id,box,right_count,wrong_count,due,last) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id,deck,item_id) DO UPDATE SET box=?,right_count=?,wrong_count=?,due=?,last=?')
		.bind(uid, deck, item, box, right, wrong, due, now, box, right, wrong, due, now).run();
	return json({ ok: true });
}
