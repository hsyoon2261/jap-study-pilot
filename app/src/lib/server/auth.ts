// 최소 인증: 비번 SHA-256 해시 + 세션 쿠키(HMAC 서명). 개인정보 없음.
const SECRET = 'jsp-koto37-2026-secret';
const enc = new TextEncoder();
const hex = (b: ArrayBuffer) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');

export async function hashPw(pw: string): Promise<string> {
	return hex(await crypto.subtle.digest('SHA-256', enc.encode('jsp:' + pw)));
}

async function hmac(msg: string): Promise<string> {
	const key = await crypto.subtle.importKey('raw', enc.encode(SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
	return hex(await crypto.subtle.sign('HMAC', key, enc.encode(msg)));
}

export async function signUid(uid: string): Promise<string> {
	return uid + '.' + (await hmac(uid));
}

export async function verifySid(sid: string | undefined): Promise<string | null> {
	if (!sid) return null;
	const i = sid.lastIndexOf('.');
	if (i < 0) return null;
	const uid = sid.slice(0, i);
	return (await signUid(uid)) === sid ? uid : null;
}
