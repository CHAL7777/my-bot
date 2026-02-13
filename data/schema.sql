-- SQLite schema generated from SQLAlchemy models


CREATE TABLE access_audit_log (
	log_id INTEGER NOT NULL, 
	user_id BIGINT NOT NULL, 
	action VARCHAR(50) NOT NULL, 
	resource VARCHAR(100) NOT NULL, 
	access_granted BOOLEAN NOT NULL, 
	reason VARCHAR(255), 
	ip_address VARCHAR(45), 
	user_agent TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (log_id)
)

;


CREATE TABLE admin_logs (
	id INTEGER NOT NULL, 
	admin_user_id BIGINT NOT NULL, 
	action TEXT NOT NULL, 
	details TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
)

;


CREATE TABLE admin_users (
	admin_id INTEGER NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	role VARCHAR(10), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (admin_id), 
	UNIQUE (username), 
	UNIQUE (email)
)

;


CREATE TABLE subjects (
	subject_id INTEGER NOT NULL, 
	subject_name VARCHAR(100) NOT NULL, 
	description TEXT, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (subject_id), 
	UNIQUE (subject_name)
)

;


CREATE TABLE telegram_admins (
	id INTEGER NOT NULL, 
	user_id BIGINT NOT NULL, 
	username VARCHAR(255), 
	role VARCHAR(10), 
	is_active BOOLEAN, 
	added_by BIGINT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (user_id)
)

;


CREATE TABLE users (
	user_id BIGINT NOT NULL, 
	username VARCHAR(255), 
	first_name VARCHAR(255), 
	last_name VARCHAR(255), 
	role VARCHAR(7), 
	created_at DATETIME, 
	updated_at DATETIME, 
	blocked BOOLEAN, 
	approved BOOLEAN, 
	is_premium BOOLEAN, 
	referral_code VARCHAR(20), 
	referred_by BIGINT, 
	referral_count INTEGER, 
	PRIMARY KEY (user_id), 
	UNIQUE (referral_code), 
	FOREIGN KEY(referred_by) REFERENCES users (user_id) ON DELETE SET NULL
)

;


CREATE TABLE chapters (
	chapter_id INTEGER NOT NULL, 
	subject_id INTEGER, 
	chapter_name VARCHAR(100) NOT NULL, 
	chapter_order INTEGER, 
	description TEXT, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (chapter_id), 
	CONSTRAINT unique_chapter UNIQUE (subject_id, chapter_name), 
	FOREIGN KEY(subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE
)

;


CREATE TABLE contact_messages (
	message_id INTEGER NOT NULL, 
	ticket_id VARCHAR(20) NOT NULL, 
	user_id BIGINT NOT NULL, 
	category VARCHAR(10) NOT NULL, 
	subject VARCHAR(200), 
	message_text TEXT NOT NULL, 
	status VARCHAR(7), 
	admin_reply TEXT, 
	replied_by BIGINT, 
	created_at DATETIME, 
	replied_at DATETIME, 
	closed_at DATETIME, 
	PRIMARY KEY (message_id), 
	UNIQUE (ticket_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
)

;


CREATE TABLE leaderboard (
	leaderboard_id INTEGER NOT NULL, 
	user_id BIGINT, 
	period VARCHAR(7) NOT NULL, 
	total_score INTEGER, 
	total_accuracy FLOAT, 
	total_questions INTEGER, 
	rank_position INTEGER, 
	last_updated DATETIME, 
	PRIMARY KEY (leaderboard_id), 
	CONSTRAINT unique_leaderboard_entry UNIQUE (user_id, period), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
)

;


CREATE TABLE payments (
	payment_id INTEGER NOT NULL, 
	user_id BIGINT, 
	screenshot_file_id VARCHAR(255), 
	screenshot_file_path VARCHAR(500), 
	status VARCHAR(8), 
	amount FLOAT NOT NULL, 
	subscription_days INTEGER, 
	transaction_id VARCHAR(100), 
	notes TEXT, 
	approved_by BIGINT, 
	approved_at DATETIME, 
	rejected_reason TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (payment_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(approved_by) REFERENCES users (user_id) ON DELETE SET NULL
)

;


CREATE TABLE referrals (
	id INTEGER NOT NULL, 
	referrer_id BIGINT NOT NULL, 
	referred_id BIGINT NOT NULL, 
	status VARCHAR(9), 
	reward_claimed BOOLEAN, 
	created_at DATETIME, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_referral UNIQUE (referrer_id, referred_id), 
	FOREIGN KEY(referrer_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(referred_id) REFERENCES users (user_id) ON DELETE CASCADE
)

;


CREATE TABLE user_daily_limits (
	id INTEGER NOT NULL, 
	user_id BIGINT, 
	date DATE NOT NULL, 
	quiz_count INTEGER, 
	question_count INTEGER, 
	last_reset DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_user_date UNIQUE (user_id, date), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
)

;


CREATE TABLE questions (
	question_id INTEGER NOT NULL, 
	subject_id INTEGER, 
	chapter_id INTEGER, 
	difficulty VARCHAR(6) NOT NULL, 
	question_text TEXT NOT NULL, 
	option_a TEXT NOT NULL, 
	option_b TEXT NOT NULL, 
	option_c TEXT NOT NULL, 
	option_d TEXT NOT NULL, 
	correct_option VARCHAR(1) NOT NULL, 
	explanation TEXT, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (question_id), 
	FOREIGN KEY(subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE, 
	FOREIGN KEY(chapter_id) REFERENCES chapters (chapter_id) ON DELETE CASCADE
)

;


CREATE TABLE user_chapter_daily_limits (
	id INTEGER NOT NULL, 
	user_id BIGINT, 
	subject_id INTEGER, 
	chapter_id INTEGER, 
	difficulty VARCHAR(6), 
	date DATE NOT NULL, 
	question_count INTEGER, 
	last_reset DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_user_chapter_difficulty_date UNIQUE (user_id, subject_id, chapter_id, difficulty, date), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE, 
	FOREIGN KEY(chapter_id) REFERENCES chapters (chapter_id) ON DELETE CASCADE
)

;


CREATE TABLE user_progress (
	id INTEGER NOT NULL, 
	user_id BIGINT, 
	subject_id INTEGER, 
	chapter_id INTEGER, 
	difficulty VARCHAR(6), 
	total_attempts INTEGER, 
	correct_attempts INTEGER, 
	total_time_spent INTEGER, 
	last_attempt DATETIME, 
	accuracy FLOAT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_user_progress UNIQUE (user_id, subject_id, chapter_id, difficulty), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE, 
	FOREIGN KEY(chapter_id) REFERENCES chapters (chapter_id) ON DELETE CASCADE
)

;


CREATE TABLE quiz_attempts (
	attempt_id INTEGER NOT NULL, 
	user_id BIGINT, 
	question_id INTEGER, 
	selected_option VARCHAR(1), 
	is_correct BOOLEAN, 
	time_taken INTEGER, 
	quiz_session_id VARCHAR(50), 
	created_at DATETIME, 
	PRIMARY KEY (attempt_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(question_id) REFERENCES questions (question_id) ON DELETE CASCADE
)

;

CREATE INDEX idx_access_audit_user ON access_audit_log (user_id, created_at);

CREATE INDEX idx_access_audit_denied ON access_audit_log (access_granted, created_at);

CREATE INDEX idx_access_audit_resource ON access_audit_log (resource, action);

CREATE INDEX idx_admin_email ON admin_users (email);

CREATE INDEX idx_admin_username ON admin_users (username);

CREATE INDEX idx_telegram_admin_user_id ON telegram_admins (user_id);

CREATE INDEX idx_telegram_admin_role ON telegram_admins (role);

CREATE INDEX idx_users_referred_by ON users (referred_by);

CREATE INDEX idx_users_referral_code ON users (referral_code);

CREATE INDEX idx_subject_order ON chapters (subject_id, chapter_order);

CREATE INDEX idx_contact_ticket_id ON contact_messages (ticket_id);

CREATE INDEX idx_contact_user ON contact_messages (user_id, created_at);

CREATE INDEX idx_contact_status ON contact_messages (status, created_at);

CREATE INDEX idx_contact_category ON contact_messages (category);

CREATE INDEX idx_leaderboard_period ON leaderboard (period, rank_position);

CREATE INDEX idx_user_leaderboard ON leaderboard (user_id, period);

CREATE INDEX idx_user_payments ON payments (user_id, created_at);

CREATE INDEX idx_payment_status ON payments (status, created_at);

CREATE INDEX idx_referral_referrer ON referrals (referrer_id);

CREATE INDEX idx_referral_referred ON referrals (referred_id);

CREATE INDEX idx_referral_status ON referrals (status);

CREATE INDEX idx_date_limit ON user_daily_limits (date, quiz_count);

CREATE INDEX idx_difficulty ON questions (difficulty);

CREATE INDEX idx_active ON questions (is_active);

CREATE INDEX idx_subject_chapter ON questions (subject_id, chapter_id);

CREATE INDEX idx_chapter_limit_lookup ON user_chapter_daily_limits (user_id, chapter_id, difficulty, date);

CREATE INDEX idx_subject_progress ON user_progress (subject_id, chapter_id, difficulty);

CREATE INDEX idx_user_progress ON user_progress (user_id, accuracy);

CREATE INDEX idx_session ON quiz_attempts (quiz_session_id);

CREATE INDEX idx_user_attempts ON quiz_attempts (user_id, created_at);

CREATE INDEX idx_question_attempts ON quiz_attempts (question_id, is_correct);
