import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
export const prerender = false;

export async function GET({ platform, cookies }) {
	const uid = await verifySid(cookies.get('sid'));
	if (!uid) return json({ ok: false }, { status: 401 });
	const db = platform?.env?.DB;
	const row: any = db ? await db.prepare('SELECT username FROM users WHERE id = ?').bind(uid).first() : null;
	return json({ ok: true, uid, username: row?.username ?? '' });
}

export async function POST({ cookies }) {
	// 로그아웃
	cookies.delete('sid', { path: '/' });
	return json({ ok: true });
}
