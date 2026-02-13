# PostgreSQL Conversion for Koyeb - TODO List

## Phase 1: Configuration Updates
- [x] Analyze current SQLite setup
- [x] Update app/config.py for PostgreSQL support
- [x] Update requirements.txt with PostgreSQL dependencies
- [x] Update app/db/base.py for PostgreSQL compatibility

## Phase 2: Database Model Adjustments
- [x] Create PostgreSQL schema script (data/schema_postgresql.sql)
- [x] SQLAlchemy models are already compatible with PostgreSQL

## Phase 3: Environment Setup
- [x] Create comprehensive deployment guide (KOYEB_POSTGRESQL_DEPLOYMENT.md)
- [ ] Create .env.example for PostgreSQL configuration (optional)
- [ ] Test locally with PostgreSQL before Koyeb deployment

## Phase 4: Testing & Deployment
- [ ] Test connection with local PostgreSQL
- [ ] Verify all models work with PostgreSQL
- [ ] Migrate existing SQLite data to PostgreSQL
- [ ] Deploy to Koyeb staging environment
- [ ] Verify database connectivity in Koyeb logs

## Notes
- Koyeb does NOT support persistent SQLite storage
- Use external PostgreSQL (Supabase, Neon, Railway, etc.)
- Connection pool: 10-20 connections recommended
- SSL/TLS required for external databases
- Set DATABASE_URL in Koyeb environment variables

-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

