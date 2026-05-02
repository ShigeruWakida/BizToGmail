#!/usr/bin/env bash
# Migrate data from Cloud SQL (PostgreSQL) to SQLite
# Run from the app directory on the e2-micro instance
#
# Prerequisites:
#   - Cloud SQL Proxy or direct PostgreSQL access
#   - psql command available (apt install postgresql-client)
#
# Usage:
#   bash scripts/migrate-cloudsql-to-sqlite.sh "postgresql://USER:PASS@HOST/DBNAME"
set -euo pipefail

PG_URL="${1:?Usage: $0 <postgresql-connection-string>}"
SQLITE_DB="state.db"
EXPORT_DIR="$(mktemp -d)"

echo "=== Exporting from PostgreSQL ==="

# Export accounts (excluding password columns - re-enter via Web UI)
psql "$PG_URL" -c "\copy (SELECT id, email, pop_host, source_username, source_protocol, source_folder, pop_port, use_ssl, destination_email, smtp_host, smtp_port, smtp_use_ssl, smtp_username, leave_copy, delete_after_days, check_interval_minutes, max_per_run, enabled, last_checked_at, next_check_at, created_at, updated_at FROM accounts) TO '$EXPORT_DIR/accounts.csv' WITH CSV HEADER"

# Export messages (dedup records)
psql "$PG_URL" -c "\copy (SELECT uidl, status, gmail_id, updated_at FROM messages) TO '$EXPORT_DIR/messages.csv' WITH CSV HEADER"

echo "=== Exported to $EXPORT_DIR ==="

echo "=== Initializing SQLite ==="
# Let the app create the schema
python3 -c "from biztogmail_app.db import ensure_schema; ensure_schema()"

echo "=== Importing accounts ==="
python3 <<PYEOF
import csv
import sqlite3

con = sqlite3.connect("$SQLITE_DB")

with open("$EXPORT_DIR/accounts.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cols = list(row.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        con.execute(
            f"INSERT OR REPLACE INTO accounts ({col_names}) VALUES ({placeholders})",
            [row[c] for c in cols],
        )

with open("$EXPORT_DIR/messages.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        con.execute(
            "INSERT OR REPLACE INTO messages (uidl, status, gmail_id, updated_at) VALUES (?, ?, ?, ?)",
            [row["uidl"], row["status"], row["gmail_id"], row["updated_at"]],
        )

con.commit()
con.close()
PYEOF

echo "=== Import complete ==="
echo ""
echo "Imported data to $SQLITE_DB"
echo ""
echo "NOTE: Passwords (pop_password, smtp_password) were NOT migrated."
echo "      They were stored in Secret Manager, not in Cloud SQL."
echo "      Re-enter passwords via the Web UI for each account."
echo ""
echo "Cleanup: rm -rf $EXPORT_DIR"
