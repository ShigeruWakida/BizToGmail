# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BizToGmail forwards company email (POP3/IMAP) to Gmail via SMTP. It runs on Cloud Run with a FastAPI web UI that requires Google OAuth login. The logged-in user's Gmail address is automatically used as the forwarding destination.

Cloud stack: Cloud Run, Cloud Scheduler, Neon (PostgreSQL).

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
- `secrets.py` - Secret resolution: supports `gcp:` (Secret Manager), `env:` (environment variables), and DB-direct password storage
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

- Passwords are stored directly in the DB (`pop_password`, `smtp_password` columns). Secret Manager (`gcp:` refs) is also supported but not used in the current production environment
- `BIZTOGMAIL_GCP_PROJECT` を空文字に設定すると Secret Manager を無効化し、パスワードを DB に直接保存する
- The `/scheduler/tick` endpoint is called every 5 minutes by Cloud Scheduler (authenticated via `X-Scheduler-Token` header); it processes only accounts whose `next_check_at` is due
- Effective check interval per account is `max(scheduler_interval, account.check_interval_minutes)` — setting an account's interval shorter than the Cloud Scheduler interval has no effect
- Account execution uses DB-row-level locking to prevent concurrent runs of the same account
- Message dedup keys are protocol-aware **and account-namespaced**: `imap:acct<id>:<folder>:<uid>` or `pop3:acct<id>:<uidl>` (ad-hoc CLI/Web runs with no saved account fall back to the legacy `imap:<folder>:<uid>` / `pop3:<uidl>`). The account prefix is required because IMAP UID / POP3 UIDL are numbered per-mailbox: without it, multiple accounts on the same server share one `imap:INBOX:<uid>` namespace and one account's mail gets silently dropped as a "duplicate" once its UID counter reaches a range another account already imported (see `_source_message_key` in `workflows.py`)
- Dedup checks are batched: `state.uidls_seen()` does a single `WHERE uidl IN (...)` query (chunked at 1000) rather than one query per message. Required for accounts with thousands of IMAP messages
- DB supports both PostgreSQL (production via `DATABASE_URL`) and SQLite (local dev via `state.db`)
- `db.py` includes inline migrations for schema evolution (ALTER TABLE additions)
- `db.py` automatically enables SSL for pg8000 connections to external PostgreSQL (e.g. Neon), but not for Cloud SQL unix socket connections
- For non-SQLite DB connections, `db.py` uses `NullPool` (no connection pooling — a fresh connection per request). Neon free tier auto-suspends after 5 min of inactivity and kills idle pooled connections; reusing a dead pooled connection caused intermittent 500s on `/scheduler/tick` even with `pool_pre_ping`. NullPool eliminates stale-connection reuse entirely

## Coding Conventions

- Python 4-space indent, `snake_case` for functions/variables, `UPPER_SNAKE` for constants
- Keep logic in `biztogmail_app/` modules by responsibility; don't put business logic in CLI or web layer
- Tests use `unittest` in `tests/`, named `test_<module>.py`
- Comments only where POP3/SMTP/IMAP behavior is non-obvious
- All UI text and comments in the codebase may be in Japanese

## Production Environment

- **Cloud Run**: asia-northeast1, URL: `https://biztogmail-29155682529.asia-northeast1.run.app/`
- **DB**: Neon PostgreSQL (Singapore). 接続情報は Cloud Run の環境変数 `DATABASE_URL` に直接設定
- **Cloud Scheduler**: 5分間隔で `/scheduler/tick` を POST
- **認証情報**: Secret Manager は使わず、すべて Cloud Run の環境変数に直接設定 (`BIZTOGMAIL_SESSION_SECRET`, `BIZTOGMAIL_SCHEDULER_TOKEN`, `GOOGLE_OIDC_CLIENT_SECRET` 等)
- **GCP Project**: `biztogmail` (ID: `29155682529`)

## Deployment

```powershell
# 1. コンテナビルド (プロジェクトルートで実行)
gcloud builds submit --tag gcr.io/biztogmail/biztogmail --project=biztogmail

# 2. デプロイ
gcloud run deploy biztogmail --image gcr.io/biztogmail/biztogmail --region asia-northeast1 --project biztogmail
```

`scripts/deploy-cloud-run.ps1` は旧構成 (Cloud SQL + Secret Manager) 向けのため、現在は上記コマンドを直接使用する。
