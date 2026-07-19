-- 일본어 학습앱 DB 스키마 (SQLite = Cloudflare D1 호환)
-- 콘텐츠(덱·단어·노래)는 정적 파일. DB에는 계정과 "사람마다 다른 것"만 저장한다.

-- 계정 (개인정보 없음 — 아이디·비번·세션만)
CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  username      TEXT NOT NULL UNIQUE,          -- 중복검사 = 이 UNIQUE 제약
  password_hash TEXT NOT NULL,
  created_at    TEXT NOT NULL
);

-- 답안 로그 (한 문제 풀 때마다 한 줄) — 통계·기록 화면의 원천
CREATE TABLE IF NOT EXISTS answer_logs (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id  TEXT NOT NULL REFERENCES users(id),
  deck     TEXT NOT NULL,
  item_id  TEXT NOT NULL,
  mode     TEXT,                                -- f2b·b2f·typing·listen·flash
  correct  INTEGER NOT NULL,                    -- 0/1
  ms       INTEGER,                             -- 응답 속도(ms), 없으면 NULL
  ts       TEXT NOT NULL                        -- ISO 시각
);
CREATE INDEX IF NOT EXISTS idx_answer_user_ts   ON answer_logs(user_id, ts);
CREATE INDEX IF NOT EXISTS idx_answer_user_item ON answer_logs(user_id, deck, item_id);

-- SRS 상태 (항목별 라이트너 박스·다음 복습일)
CREATE TABLE IF NOT EXISTS review_states (
  user_id     TEXT NOT NULL REFERENCES users(id),
  deck        TEXT NOT NULL,
  item_id     TEXT NOT NULL,
  box         INTEGER NOT NULL DEFAULT 0,       -- 0~5
  right_count INTEGER NOT NULL DEFAULT 0,
  wrong_count INTEGER NOT NULL DEFAULT 0,
  due         TEXT,                             -- 다음 복습 시각
  last        TEXT,                             -- 마지막 학습 시각
  PRIMARY KEY (user_id, deck, item_id)
);
CREATE INDEX IF NOT EXISTS idx_review_due ON review_states(user_id, due);

-- 세트(오늘의 세트) 완료 상태
CREATE TABLE IF NOT EXISTS set_progress (
  user_id  TEXT NOT NULL REFERENCES users(id),
  set_id   TEXT NOT NULL,
  done     INTEGER NOT NULL DEFAULT 0,
  done_at  TEXT,
  PRIMARY KEY (user_id, set_id)
);

-- 사용자(admin)가 웹에서 붙여넣은 곡 가사 원문. 튜터가 이걸 읽어 lineNotes를 달아 songs.json에 반영.
CREATE TABLE IF NOT EXISTS song_lyrics (
  song_id    TEXT PRIMARY KEY,
  lyric      TEXT NOT NULL,
  updated_by TEXT,
  updated_at TEXT NOT NULL
);
