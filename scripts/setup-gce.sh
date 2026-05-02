#!/usr/bin/env bash
# BizToGmail - GCE e2-micro setup script
# Run as root on a fresh Debian/Ubuntu e2-micro instance
set -euo pipefail

APP_DIR="/opt/biztogmail"
APP_USER="biztogmail"

echo "=== 1. Install system packages ==="
apt-get update -qq
apt-get install -y -qq python3 python3-venv git nginx certbot python3-certbot-nginx

echo "=== 2. Create app user ==="
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$APP_USER"
fi

echo "=== 3. Deploy app ==="
if [ -d "$APP_DIR/.git" ]; then
    echo "Repo already exists, pulling latest..."
    cd "$APP_DIR" && git pull
else
    git clone https://github.com/ShigeruWakida/BizToGmail.git "$APP_DIR"
fi
cd "$APP_DIR"

echo "=== 4. Setup Python venv ==="
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "=== 5. Create .env file ==="
if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" <<'ENVEOF'
# Google OAuth (required for web login)
GOOGLE_OIDC_CLIENT_ID=your-google-client-id
GOOGLE_OIDC_CLIENT_SECRET=your-google-client-secret
GOOGLE_OIDC_REDIRECT_URI=https://your-domain/auth/callback

# Session secret (change this)
BIZTOGMAIL_SESSION_SECRET=change-this-to-a-random-string

# Scheduler token (for manual curl testing; not required for systemd timer)
BIZTOGMAIL_SCHEDULER_TOKEN=change-this-scheduler-token

# No DATABASE_URL = SQLite (state.db in app directory)
# No BIZTOGMAIL_GCP_PROJECT = passwords stored in DB directly
ENVEOF
    echo ">>> .env created at $APP_DIR/.env - edit it with your credentials"
fi

echo "=== 6. Fix permissions ==="
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "=== 7. Install systemd units ==="
cp "$APP_DIR/scripts/biztogmail.service" /etc/systemd/system/
cp "$APP_DIR/scripts/biztogmail-scheduler.service" /etc/systemd/system/
cp "$APP_DIR/scripts/biztogmail-scheduler.timer" /etc/systemd/system/
systemctl daemon-reload

echo "=== 8. Setup nginx reverse proxy ==="
if [ ! -f /etc/nginx/sites-available/biztogmail ]; then
    cat > /etc/nginx/sites-available/biztogmail <<'NGINXEOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF
    ln -sf /etc/nginx/sites-available/biztogmail /etc/nginx/sites-enabled/biztogmail
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit $APP_DIR/.env with your Google OAuth credentials"
echo "  2. Start the services:"
echo "       systemctl enable --now biztogmail.service"
echo "       systemctl enable --now biztogmail-scheduler.timer"
echo "  3. (Optional) Setup HTTPS with Let's Encrypt:"
echo "       certbot --nginx -d your-domain.com"
echo "  4. Update Google OAuth redirect URI to https://your-domain.com/auth/callback"
