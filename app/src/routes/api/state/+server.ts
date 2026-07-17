import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
export const prerender = false;

// 기록/통계 조회: SRS 상태 + 날짜별 집계 + 오답 top
export async function GET({ platform, cookies }) {
	const uid = await verifySid(cookies.get('sid'));
	if (!uid) return json({ ok: false }, { status: 401 });
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false }, { status: 500 });
	const srsRows: any = await db.prepare('SELECT deck,item_id,box,right_count,wrong_count,due FROM review_states WHERE user_id=?').bind(uid).all();
	const byDay: any = await db.prepare("SELECT substr(ts,1,10) d, COUNT(*) n, SUM(correct) ok, AVG(ms) avg FROM answer_logs WHERE user_id=? GROUP BY d ORDER BY d").bind(uid).all();
	const tot: any = await db.prepare('SELECT COUNT(*) n, SUM(correct) ok FROM answer_logs WHERE user_id=?').bind(uid).first();
	const srs: Record<string, any> = {};
	for (const r of srsRows.results || []) srs[r.deck + ':' + r.item_id] = { box: r.box, right: r.right_count, wrong: r.wrong_count, due: r.due };
	return json({ ok: true, srs, byDay: byDay.results || [], total: tot?.n || 0, correct: tot?.ok || 0 });
}
