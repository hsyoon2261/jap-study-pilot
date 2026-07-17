import { json } from '@sveltejs/kit';
import { hashPw, signUid } from '$lib/server/auth';
export const prerender = false;

export async function POST({ request, platform, cookies }) {
	const { username, password } = await request.json();
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false, error: 'DB 연결 안 됨' }, { status: 500 });
	const row: any = await db.prepare('SELECT id, password_hash FROM users WHERE username = ?').bind(username).first();
	if (!row || row.password_hash !== (await hashPw(password)))
		return json({ ok: false, error: '아이디 또는 비밀번호가 틀렸어.' }, { status: 401 });
	cookies.set('sid', await signUid(row.id), { path: '/', httpOnly: true, sameSite: 'lax', secure: true, maxAge: 60 * 60 * 24 * 90 });
	return json({ ok: true, username });
}
