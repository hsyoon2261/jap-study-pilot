import { json } from '@sveltejs/kit';
import { hashPw, signUid } from '$lib/server/auth';
export const prerender = false;

const KST = 32400000;

// 회원가입: 아이디·비밀번호만 (개인정보 없음). 아이디 중복검사 = users.username UNIQUE.
export async function POST({ request, platform, cookies }) {
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false, error: 'DB 연결 안 됨' }, { status: 500 });
	const body = await request.json().catch(() => ({}));
	const username = (body.username || '').trim();
	const password = body.password || '';
	if (username.length < 2 || username.length > 20)
		return json({ ok: false, error: '아이디는 2~20자로.' }, { status: 400 });
	if (!/^[A-Za-z0-9가-힣_.-]+$/.test(username))
		return json({ ok: false, error: '아이디는 한글·영문·숫자·_.- 만.' }, { status: 400 });
	if (password.length < 4)
		return json({ ok: false, error: '비밀번호는 4자 이상.' }, { status: 400 });

	const dup: any = await db.prepare('SELECT id FROM users WHERE username = ?').bind(username).first();
	if (dup) return json({ ok: false, error: '이미 쓰는 아이디야. 다른 걸로.' }, { status: 409 });

	const id = 'u_' + crypto.randomUUID();
	const now = new Date(Date.now() + KST).toISOString().slice(0, 19);
	try {
		await db.prepare('INSERT INTO users(id,username,password_hash,created_at) VALUES(?,?,?,?)')
			.bind(id, username, await hashPw(password), now).run();
	} catch {
		return json({ ok: false, error: '가입 실패 (아이디 중복?)' }, { status: 409 });
	}
	// 가입 즉시 로그인
	cookies.set('sid', await signUid(id), { path: '/', httpOnly: true, sameSite: 'lax', secure: true, maxAge: 60 * 60 * 24 * 90 });
	return json({ ok: true, username });
}
