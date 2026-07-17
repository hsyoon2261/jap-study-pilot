// 학습 기록·SRS 로컬 저장 (정적 배포 임시 — 나중에 로그인+D1으로 이관).
// 라이트너 박스 0~5, 간격(일) [0,1,3,7,14,30].
type Srs = { box: number; right: number; wrong: number; due: string; last: string };
const INTERVALS = [0, 1, 3, 7, 14, 30];
const SRS_KEY = 'jsp_srs_v1';
const LOG_KEY = 'jsp_logs_v1';

function read<T>(k: string, fallback: T): T {
	if (typeof localStorage === 'undefined') return fallback;
	try {
		const v = localStorage.getItem(k);
		return v ? (JSON.parse(v) as T) : fallback;
	} catch {
		return fallback;
	}
}
function write(k: string, v: unknown) {
	try {
		localStorage.setItem(k, JSON.stringify(v));
	} catch {
		/* 용량 초과 등 무시 */
	}
}

export function getSrs(): Record<string, Srs> {
	return read<Record<string, Srs>>(SRS_KEY, {});
}

export function srsKey(deck: string, itemId: string) {
	return deck + ':' + itemId;
}

const KST = 32400000; // UTC+9 (ms) — 서버(D1)와 동일 기준으로 맞춰 due 비교 skew 방지
export function nowIso() {
	return new Date(Date.now() + KST).toISOString().slice(0, 19);
}

// 답안 기록 + SRS 갱신
export function recordAnswer(
	deck: string,
	itemId: string,
	mode: string,
	correct: boolean,
	ms: number | null
) {
	// 로그인돼 있으면 서버(D1)에도 전송 (오프라인·비로그인이면 로컬만)
	if (typeof fetch !== 'undefined') {
		fetch('/api/answer', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ deck, item: itemId, mode, correct, ms })
		}).catch(() => {});
	}
	// 로그 append
	const logs = read<unknown[]>(LOG_KEY, []);
	logs.push({ ts: nowIso(), deck, item: itemId, mode, correct, ms });
	write(LOG_KEY, logs);

	// SRS
	const srs = getSrs();
	const key = srsKey(deck, itemId);
	const s: Srs = srs[key] || { box: 0, right: 0, wrong: 0, due: nowIso(), last: nowIso() };
	if (correct) {
		s.right++;
		s.box = Math.min(5, s.box + 1);
	} else {
		s.wrong++;
		s.box = Math.max(0, s.box - 1);
	}
	const days = INTERVALS[s.box];
	const due = new Date(Date.now() + KST + days * 86400000);
	s.due = due.toISOString().slice(0, 19);
	s.last = nowIso();
	srs[key] = s;
	write(SRS_KEY, srs);
}
