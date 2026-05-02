# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BizToGmail forwards company email (POP3/IMAP) to Gmail via SMTP. It runs on Cloud Run with a FastAPI web UI that requires Google OAuth login. The logged-in user's Gmail address is automatically used as the forwarding destination.

Cloud stack: Cloud Run, Cloud Scheduler, Cloud SQL (PostgreSQL), Secret Manager.

## Commands

```bash
# Activate venv (PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m unittest discover -s tests -v

# Run a single test file
python -m unittest tests.test_workflows -v

# Run the web server locally
uvicorn biztogmail_web.app:app --reload --port 8080

# CLI dry-run (forwarding check without sending)
python biztogmail.py run --host <host> --user <user> --destination <gmail> --max 1 --dry-run

# CLI scheduler one-shot
python biztogmail.py scheduler --once
```

## Architecture

**`biztogmail_app/`** - Core logic, no web dependencies:
- `workflows.py` - Main forwarding pipeline: fetch mail (POP3/IMAP) -> send via SMTP -> track in DB -> optionally delete from source
- `scheduler.py` / `scheduler_runner.py` - Per-account execution with DB-level locking (`account_execution_locks` table) to prevent double runs
- `accounts.py` - CRUD for saved mail accounts
- `db.py` - SQLAlchemy Core tables (`messages`, `accounts`, `account_execution_locks`) with auto-migration. Uses `DATABASE_URL` env var or falls back to local `state.db` (SQLite)
- `state.py` - Message dedup tracking (UIDL-based for POP3, UID-based for IMAP)
- `secrets.py` - Google Cloud Secret Manager integration for storing/retrieving mail passwords
- `settings.py` - All config via env vars (see `.env.example`)
- `pop3_client.py` / `imap_client.py` / `smtp_client.py` - Mail protocol clients
- `locks.py` - File-based locking for scheduler tick
- `services.py` - Deletion policy logic (leave copy, delete after N days)

**`biztogmail_web/`** - FastAPI layer:
- `app.py` - All HTTP endpoints. Key routes: `/accounts` (CRUD), `/accounts/{id}/run` (manual trigger), `/scheduler/tick` (Cloud Scheduler entry point), `/auth/*` (Google OAuth)
- `auth.py` - Google OIDC flow
- `schemas.py` - Pydantic request/response models

**`biztogmail.py`** - CLI entry point, delegates to `biztogmail_app/cli.py`

## Key Design Decisions

- Passwords entered in the web UI are stored in Secret Manager; only `secret_ref` pointers are saved in the DB
- The `/scheduler/tick` endpoint is called every minute by Cloud Scheduler (authenticated via `X-Scheduler-Token` header); it processes only accounts whose `next_check_at` is due
- Account execution uses DB-row-level locking to prevent concurrent runs of the same account
- Message dedup keys are protocol-aware: `pop3:<uidl>` or `imap:<folder>:<uid>`
- DB supports both PostgreSQL (production via `DATABASE_URL`) and SQLite (local dev via `state.db`)
- `db.py` includes inline migrations for schema evolution (ALTER TABLE additions)

## Coding Conventions

- Python 4-space indent, `snake_case` for functions/variables, `UPPER_SNAKE` for constants
- Keep logic in `biztogmail_app/` modules by responsibility; don't put business logic in CLI or web layer
- Tests use `unittest` in `tests/`, named `test_<module>.py`
- Comments only where POP3/SMTP/IMAP behavior is non-obvious
- All UI text and comments in the codebase may be in Japanese

## Deployment

Cloud Run deploys use `scripts/deploy-cloud-run.ps1` (PowerShell). Container builds via `gcloud builds submit`. See README.md for full deploy flow.
