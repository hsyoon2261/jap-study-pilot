// 정적 배포용 발음: 미리 구운 오디오 manifest(텍스트→파일)에서 재생. 없으면 브라우저 내장 TTS 폴백.
let manifest: Record<string, string> | null = null;
let loading: Promise<void> | null = null;
const cache: Record<string, HTMLAudioElement> = {};
let current: HTMLAudioElement | null = null;
let seq = 0;

async function ensureManifest() {
	if (manifest) return;
	if (!loading) {
		loading = fetch('/audio/manifest.json')
			.then((r) => r.json())
			.then((m) => {
				manifest = m;
			})
			.catch(() => {
				manifest = {};
			});
	}
	await loading;
}

let jaVoice: SpeechSynthesisVoice | null = null;
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
	const pick = () => {
		const vs = speechSynthesis.getVoices().filter((v) => v.lang?.startsWith('ja'));
		jaVoice = vs[0] || null;
	};
	speechSynthesis.onvoiceschanged = pick;
	pick();
}

// 현재 재생 중인 발음을 즉시 중단 (영상↔발음 조율용)
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
	await ensureManifest();
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
		} catch {
			/* 폴백으로 */
		}
	}
	// 폴백: 브라우저 내장 일본어 음성
	if (jaVoice && 'speechSynthesis' in window) {
		speechSynthesis.cancel();
		const u = new SpeechSynthesisUtterance(text);
		u.voice = jaVoice;
		u.lang = jaVoice.lang;
		u.rate = slow ? 0.5 : 0.75;
		u.onend = () => { if (my === seq) onEnd?.(); };
		u.onerror = () => { if (my === seq) onEnd?.(); };
		speechSynthesis.speak(u);
	} else {
		onEnd?.();
	}
}
