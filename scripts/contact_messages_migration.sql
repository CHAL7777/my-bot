-- Migration: Update contact_messages table for new ticket system
-- This migration adds ticket_id field and updates status values

-- Add ticket_id column if not exists
ALTER TABLE contact_messages
ADD COLUMN IF NOT EXISTS ticket_id VARCHAR(20) UNIQUE NOT NULL AFTER message_id;

-- Drop old enum type if exists and create new one
DROP TYPE IF EXISTS contact_status_old;
DROP TYPE IF EXISTS contact_status CASCADE;

CREATE TYPE contact_status AS ENUM('open', 'replied', 'closed');

-- Update status values: new -> open, read -> open
UPDATE contact_messages SET status = 'open' WHERE status IN ('new', 'read');

-- Alter status column to use new enum
ALTER TABLE contact_messages
ALTER COLUMN status TYPE VARCHAR(20);

ALTER TABLE contact_messages
ALTER COLUMN status SET DEFAULT 'open';

-- Add closed_at column if not exists
ALTER TABLE contact_messages
ADD COLUMN IF NOT EXISTS closed_at DATETIME NULL;

-- Add index on ticket_id
CREATE INDEX IF NOT EXISTS idx_contact_ticket_id ON contact_messages(ticket_id);

-- Add comment
ALTER TABLE contact_messages COMMENT = 'Stores user-to-admin support tickets';

-- Update existing rows with ticket_id if they don't have one
-- This will generate ticket IDs like SUP-1001, SUP-1002, etc.
DO $$
DECLARE
    msg RECORD;
    new_id INT := 1000;
BEGIN
    FOR msg IN SELECT message_id FROM contact_messages WHERE ticket_id IS NULL ORDER BY message_id LOOP
        new_id := new_id + 1;
        UPDATE contact_messages SET ticket_id = 'SUP-' || new_id WHERE message_id = msg.message_id;
    END LOOP;
END $$;

-- Make ticket_id NOT NULL after updating
ALTER TABLE contact_messages ALTER COLUMN ticket_id SET NOT NULL;

-- Update the __repr__ method reference in model (Python code change)
-- The model now uses ticket_id instead of message_id for display

