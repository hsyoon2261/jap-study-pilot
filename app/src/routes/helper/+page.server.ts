import { redirect } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';

// 헬퍼는 admin 전용. SPA(정적 프리렌더) 대신 이 라우트만 동적(Worker)으로 돌려서
// 요청마다 서버에서 세션을 검사한다. UI 숨김이 아니라 접근 자체를 차단.
export const prerender = false;
export const ssr = true;

export async function load({ cookies, platform }) {
	const uid = await verifySid(cookies.get('sid'));
	const db = platform?.env?.DB;
	let admin = false;
	if (uid && db) {
		const row: any = await db.prepare('SELECT username FROM users WHERE id = ?').bind(uid).first();
		admin = row?.username === 'admin';
	}
	// admin 세션이 아니면 접근 불가 → 홈으로 리다이렉트
	if (!admin) throw redirect(303, '/');
	return {};
}
