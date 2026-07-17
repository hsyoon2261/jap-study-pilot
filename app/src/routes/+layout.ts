// 클라이언트 중심 학습 앱 → SPA 모드: 정적 셸만 미리 생성하고 화면 로직은 브라우저에서.
// 순수 정적 배포(Worker 불필요, 함수 호출 0). DB/인증 API는 나중에 별도 함수로 붙인다.
export const ssr = false;
export const prerender = true;
