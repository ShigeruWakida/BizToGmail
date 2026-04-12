# Initial Release

## Suggested tag

`v1.0.0`

## Suggested title

`BizToGmail v1.0.0`

## Suggested release notes

Initial public release of BizToGmail.

BizToGmail is a small web app that fetches company mail via POP3 or IMAP and forwards it to Gmail via SMTP. The web UI uses Google login, and the logged-in Google account's Gmail address is used as the forwarding destination.

Highlights:

- POP3 and IMAP support
- SMTP forwarding to Gmail
- Google-authenticated web UI
- Cloud Run deployment
- Cloud Scheduler-based periodic checks
- Cloud SQL persistence
- Secret Manager integration
- Per-account execution locking to avoid duplicate runs
- Operations and monitoring documentation

Current deployment model:

- Cloud Run
- Cloud Scheduler
- Cloud SQL for PostgreSQL
- Secret Manager
- Google OAuth (test user mode)

Notes:

- Google OAuth is currently intended for test-user operation
- Cloud deployment and operations guidance are documented in `README.md`, `OPERATIONS.md`, and `MONITORING.md`
