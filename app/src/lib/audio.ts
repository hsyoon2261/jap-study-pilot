// 정적 배포용 발음.
// - 기본: /audio/manifest.json (한 글자=원어민 녹음 + 단어·문장=기본 음성). 서버 없이 최고 음질.
// - (admin이 설정에서 고른 경우) 브라우저 내장 일본어 음성으로 전부 재생.
// 캐릭터 성우 로스터는 배포 안 함(용량·취향). 성우 선택 = 기기의 일반 TTS 음성 중에서.
let manifest: Record<string, string> | null = null;
let loading: Promise<void> | null = null;
const cache: Record<string, HTMLAudioElement> = {};
let current: HTMLAudioElement | null = null;
let seq = 0;

const VOICE_KEY = 'jsp_voice_v1'; // '' = 기본(구운 음성), 그 외 = 브라우저 음성 이름
let selectedVoice = '';
if (typeof localStorage !== 'undefined') {
	try { selectedVoice = localStorage.getItem(VOICE_KEY) || ''; } catch { selectedVoice = ''; }
}

async function ensureManifest() {
	if (manifest) return;
	if (!loading) {
		loading = fetch('/audio/manifest.json')
			.then((r) => r.json())
			.then((m) => { manifest = m; })
			.catch(() => { manifest = {}; });
	}
	await loading;
}

// ── 브라우저 일본어 음성 (기기 내장 일반 TTS) ──
function jaVoices(): SpeechSynthesisVoice[] {
	if (typeof window === 'undefined' || !('speechSynthesis' in window)) return [];
	return speechSynthesis.getVoices().filter((v) => (v.lang || '').toLowerCase().startsWith('ja'));
}
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
	speechSynthesis.onvoiceschanged = () => { /* 목록 준비되면 갱신됨 */ };
	jaVoices();
}
// 설정(admin)용: 선택 가능한 음성 목록 (기본 + 기기 일본어 음성)
export function listVoices(): { id: string; label: string }[] {
	const out = [{ id: '', label: '기본 (미리 녹음 · 고음질)' }];
	for (const v of jaVoices()) {
		const short = v.name.replace(/^Microsoft\s+/i, '').replace(/\s*-\s*Japanese.*/i, '').replace(/\s*\(.*\)$/, '').trim();
		out.push({ id: v.name, label: short || v.name });
	}
	return out;
}
export function onVoicesReady(cb: () => void) {
	if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
	if (jaVoices().length) { cb(); return; }
	const prev = speechSynthesis.onvoiceschanged;
	speechSynthesis.onvoiceschanged = (e) => { if (typeof prev === 'function') (prev as any).call(speechSynthesis, e); cb(); };
	setTimeout(cb, 1200);
}
export function getSelectedVoice() { return selectedVoice; }
export function setSelectedVoice(id: string) {
	selectedVoice = id || '';
	try { localStorage.setItem(VOICE_KEY, selectedVoice); } catch { /* */ }
}

function speakBrowser(text: string, voiceName: string, slow: boolean, onEnd?: () => void) {
	if (typeof window === 'undefined' || !('speechSynthesis' in window)) { onEnd?.(); return; }
	speechSynthesis.cancel();
	const u = new SpeechSynthesisUtterance(text);
	const v = jaVoices().find((x) => x.name === voiceName) || jaVoices()[0];
	if (v) { u.voice = v; u.lang = v.lang; } else u.lang = 'ja-JP';
	u.rate = slow ? 0.55 : 0.85;
	u.onend = () => onEnd?.();
	u.onerror = () => onEnd?.();
	speechSynthesis.speak(u);
}

export function stopSpeak() {
	seq++;
	if (current) { current.onended = null; current.pause(); current = null; }
	if (typeof window !== 'undefined' && 'speechSynthesis' in window && speechSynthesis.speaking) speechSynthesis.cancel();
}

export async function speak(text: string, opts?: { slow?: boolean; onEnd?: () => void }) {
	if (!text) { opts?.onEnd?.(); return; }
	const slow = !!opts?.slow;
	const onEnd = opts?.onEnd;
	const my = ++seq;

	// admin이 브라우저 음성을 골랐으면 그걸로 (구운 음성 건너뜀)
	if (selectedVoice) { speakBrowser(text, selectedVoice, slow, onEnd); return; }

	// 기본: 미리 구운 manifest
	await ensureManifest();
	if (my !== seq) return;
	const file = manifest?.[text];
	if (file) {
		try {
			if (!cache[text]) cache[text] = new Audio('/audio/' + file);
			if (my !== seq) return;
			if (current) { current.onended = null; current.pause(); }
			current = cache[text];
			current.currentTime = 0;
			current.playbackRate = slow ? 0.75 : 1.0;
			current.onended = () => { if (my === seq) { current = null; onEnd?.(); } };
			await current.play();
			return;
		} catch { /* 폴백 */ }
	}
	// 폴백: 브라우저 내장 음성
	if (my === seq) speakBrowser(text, '', slow, onEnd);
	else onEnd?.();
}
