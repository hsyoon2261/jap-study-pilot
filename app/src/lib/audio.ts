// 정적 배포용 발음. 성우 오디오를 빌드에 구워 내장한다(기기 목록에 의존 X).
// - 기본(''):   /audio/manifest.json     (한 글자=원어민 녹음 + 단어·문장=기본 음성)
// - 마오('mao'): /audio/mao/manifest.json (전부 마오로 구운 mp3, 빌드에 내장)
// 마오는 admin만 설정에서 고를 수 있다(내장은 되어 있고, 일반 계정엔 선택 UI가 안 뜸).
// 구운 파일에 없는 텍스트는 기본 → 브라우저 내장 음성 순으로 폴백.

export type VoiceOpt = { id: string; label: string; desc: string };
export const VOICE_LIST: VoiceOpt[] = [
	{ id: '', label: '기본 (원어민+합성)', desc: '한 글자는 원어민 녹음, 단어·문장은 기본 합성음' },
	{ id: 'mao', label: '마오 (여) ⭐', desc: '자연스럽고 따뜻한 여성 (빌드에 내장)' }
];

const manifests: Record<string, Record<string, string> | undefined> = {};
const loadingM: Record<string, Promise<Record<string, string>> | undefined> = {};
const cache: Record<string, HTMLAudioElement> = {};
let current: HTMLAudioElement | null = null;
let seq = 0;

const VOICE_KEY = 'jsp_voice_v1';
let selectedVoice = '';
if (typeof localStorage !== 'undefined') {
	try { selectedVoice = localStorage.getItem(VOICE_KEY) || ''; } catch { selectedVoice = ''; }
}
export function getSelectedVoice() { return selectedVoice; }
export function setSelectedVoice(id: string) {
	selectedVoice = id || '';
	try { localStorage.setItem(VOICE_KEY, selectedVoice); } catch { /* */ }
}

function manifestUrl(slug: string) { return slug ? `/audio/${slug}/manifest.json` : '/audio/manifest.json'; }
function fileUrl(slug: string, file: string) { return slug ? `/audio/${slug}/${file}` : `/audio/${file}`; }

function ensureManifest(slug: string): Promise<Record<string, string>> {
	if (manifests[slug]) return Promise.resolve(manifests[slug]!);
	if (!loadingM[slug]) {
		loadingM[slug] = fetch(manifestUrl(slug))
			.then((r) => (r.ok ? r.json() : {}))
			.then((m) => { manifests[slug] = m; return m; })
			.catch(() => { manifests[slug] = {}; return {}; });
	}
	return loadingM[slug]!;
}

// 최종 폴백: 브라우저 내장 일본어 음성
let jaVoice: SpeechSynthesisVoice | null = null;
function pickJa() {
	if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
	const vs = speechSynthesis.getVoices().filter((v) => (v.lang || '').toLowerCase().startsWith('ja'));
	jaVoice = vs[0] || null;
}
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
	speechSynthesis.onvoiceschanged = pickJa;
	pickJa();
}
function speakBrowser(text: string, slow: boolean, onEnd?: () => void) {
	if (typeof window === 'undefined' || !('speechSynthesis' in window) || !jaVoice) { onEnd?.(); return; }
	speechSynthesis.cancel();
	const u = new SpeechSynthesisUtterance(text);
	u.voice = jaVoice; u.lang = jaVoice.lang; u.rate = slow ? 0.55 : 0.8;
	u.onend = () => onEnd?.(); u.onerror = () => onEnd?.();
	speechSynthesis.speak(u);
}

export function stopSpeak() {
	seq++;
	if (current) { current.onended = null; current.pause(); current = null; }
	if (typeof window !== 'undefined' && 'speechSynthesis' in window && speechSynthesis.speaking) speechSynthesis.cancel();
}

function playFile(url: string, slow: boolean, onEnd: (() => void) | undefined, my: number): boolean {
	try {
		if (!cache[url]) cache[url] = new Audio(url);
		if (my !== seq) return true;
		if (current) { current.onended = null; current.pause(); }
		current = cache[url];
		current.currentTime = 0;
		current.playbackRate = slow ? 0.75 : 1.0;
		current.onended = () => { if (my === seq) { current = null; onEnd?.(); } };
		current.play().catch(() => { if (my === seq) { current = null; onEnd?.(); } });
		return true;
	} catch { return false; }
}

export async function speak(text: string, opts?: { slow?: boolean; onEnd?: () => void }) {
	if (!text) { opts?.onEnd?.(); return; }
	const slow = !!opts?.slow;
	const onEnd = opts?.onEnd;
	const my = ++seq;
	const slug = selectedVoice;

	const m = await ensureManifest(slug);
	if (my !== seq) return;
	if (m[text] && playFile(fileUrl(slug, m[text]), slow, onEnd, my)) return;

	// 폴백1: 기본 성우 파일
	if (slug) {
		const dm = await ensureManifest('');
		if (my !== seq) return;
		if (dm[text] && playFile(fileUrl('', dm[text]), slow, onEnd, my)) return;
	}
	// 폴백2: 브라우저 내장 음성
	if (my === seq) speakBrowser(text, slow, onEnd);
	else onEnd?.();
}
