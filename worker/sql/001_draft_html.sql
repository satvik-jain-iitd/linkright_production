-- Migration 001: Add draft_html column to resume_jobs
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor > New query)

ALTER TABLE resume_jobs ADD COLUMN IF NOT EXISTS draft_html text;
