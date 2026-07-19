import { json } from '@sveltejs/kit';
import { verifySid } from '$lib/server/auth';
import songsData from '$lib/data/songs.json';
export const prerender = false;

const KST = 32400000;

async function isAdmin(db: any, uid: string | null): Promise<boolean> {
	if (!db || !uid) return false;
	const row: any = await db.prepare('SELECT username FROM users WHERE id=?').bind(uid).first();
	return row?.username === 'admin';
}

// utaten .lyricBody(.hiragana) 구조: <span class="ruby"><span class="rb">원문</span><span class="rt">후리가나</span></span> + <br>
// rt(후리가나)만 버리고 rb(원문)+줄바꿈을 남겨 깔끔한 원문 가사를 뽑는다.
function extractLyric(html: string): string | null {
	const m = html.match(/<div[^>]*class="[^"]*hiragana[^"]*"[^>]*>([\s\S]*?)<\/div>/i)
		|| html.match(/<div[^>]*class="[^"]*lyricBody[^"]*"[^>]*>([\s\S]*?)<\/div>/i);
	if (!m) return null;
	let body = m[1];
	body = body.replace(/<br\s*\/?>/gi, '\n');                                  // 줄바꿈
	body = body.replace(/<span[^>]*class="[^"]*\brt\b[^"]*"[^>]*>[\s\S]*?<\/span>/gi, ''); // 후리가나 제거
	body = body.replace(/<[^>]+>/g, '');                                        // 나머지 태그 제거
	body = body.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
		.replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&nbsp;/g, ' ');
	const lines = body.split('\n').map((l) => l.trim()).filter(Boolean);
	return lines.length ? lines.join('\n') : null;
}

// admin이 클릭하면 서버(Worker)가 우타텐에서 원문을 긁어 D1에 저장. 코드엔 가사 0.
export async function POST({ request, platform, cookies }) {
	const db = platform?.env?.DB;
	const uid = await verifySid(cookies.get('sid'));
	if (!(await isAdmin(db, uid))) return json({ ok: false, error: 'admin만 가능해.' }, { status: 403 });

	const { id } = await request.json();
	const song: any = (songsData as any[]).find((s) => s.id === id);
	if (!song) return json({ ok: false, error: '곡을 찾을 수 없어.' }, { status: 400 });
	if (!song.lyricUrl) return json({ ok: false, error: '이 곡은 우타텐 주소가 없어.' }, { status: 400 });

	let html = '';
	try {
		const res = await fetch(song.lyricUrl, {
			headers: {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
				'Accept-Language': 'ja,en;q=0.8'
			}
		});
		if (!res.ok) return json({ ok: false, error: `우타텐 응답 ${res.status} (서버 IP 차단일 수 있음 → 8765나 붙여넣기)` }, { status: 502 });
		html = await res.text();
	} catch {
		return json({ ok: false, error: '우타텐 연결 실패 (서버 차단 가능 → 8765나 붙여넣기)' }, { status: 502 });
	}

	// 잘린/차단 응답 가드: 정상 우타텐 곡 페이지는 항상 크고 lyricBody를 포함. 반쪽 가사 조용히 저장 방지.
	if (html.length < 15000 || !/class="[^"]*(?:lyricBody|hiragana)/.test(html)) {
		return json({ ok: false, error: '우타텐이 잘린/차단 응답을 줬어. 잠시 후 다시 눌러줘 (계속되면 8765나 붙여넣기).' }, { status: 502 });
	}

	const lyric = extractLyric(html);
	if (!lyric) return json({ ok: false, error: '가사 파싱 실패 (우타텐 구조 변경?)' }, { status: 502 });

	const now = new Date(Date.now() + KST).toISOString().slice(0, 19);
	await db.prepare('INSERT INTO song_lyrics(song_id,lyric,updated_by,updated_at) VALUES(?,?,?,?) ON CONFLICT(song_id) DO UPDATE SET lyric=?,updated_by=?,updated_at=?')
		.bind(id, lyric, uid, now, lyric, uid, now).run();

	return json({ ok: true, lyric });
}
