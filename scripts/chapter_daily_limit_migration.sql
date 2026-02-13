-- Migration: Add UserChapterDailyLimit table for 25 questions per day per chapter + level feature
-- This enables tracking: 25 questions per day per (chapter, difficulty) combination

-- Create enum for chapter limit difficulty if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chapter_limit_difficulty') THEN
        CREATE TYPE chapter_limit_difficulty AS ENUM ('simple', 'medium', 'hard');
    END IF;
END $$;

-- Create the user_chapter_daily_limits table
CREATE TABLE IF NOT EXISTS user_chapter_daily_limits (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    difficulty chapter_limit_difficulty NOT NULL,
    date DATE NOT NULL,
    question_count INTEGER DEFAULT 0,
    last_reset TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint to ensure one record per user per chapter per difficulty per date
    CONSTRAINT unique_user_chapter_difficulty_date UNIQUE (user_id, subject_id, chapter_id, difficulty, date)
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_chapter_limit_lookup 
ON user_chapter_daily_limits (user_id, chapter_id, difficulty, date);

CREATE INDEX IF NOT EXISTS idx_chapter_limit_user_date 
ON user_chapter_daily_limits (user_id, date);

CREATE INDEX IF NOT EXISTS idx_chapter_limit_chapter 
ON user_chapter_daily_limits (chapter_id, difficulty);

-- Add comments for documentation
COMMENT ON TABLE user_chapter_daily_limits IS 'Tracks daily question limits per user per chapter per difficulty level. Enables 25 questions per day per (chapter, level) combination.';
COMMENT ON COLUMN user_chapter_daily_limits.user_id IS 'User ID';
COMMENT ON COLUMN user_chapter_daily_limits.subject_id IS 'Subject ID';
COMMENT ON COLUMN user_chapter_daily_limits.chapter_id IS 'Chapter ID';
COMMENT ON COLUMN user_chapter_daily_limits.difficulty IS 'Question difficulty level (simple/medium/hard)';
COMMENT ON COLUMN user_chapter_daily_limits.date IS 'Date for this limit record';
COMMENT ON COLUMN user_chapter_daily_limits.question_count IS 'Number of questions answered today for this chapter+level';
COMMENT ON COLUMN user_chapter_daily_limits.last_reset IS 'When this record was last updated';

-- Migration completed successfully
DO $$
BEGIN
    RAISE NOTICE 'Migration completed: user_chapter_daily_limits table created successfully';
    RAISE NOTICE 'This enables the 25 questions per day per chapter + difficulty feature';
END $$;

