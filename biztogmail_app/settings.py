import os
import pathlib
import subprocess
from functools import lru_cache


BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "state.db"
LOG_DIR = BASE_DIR / "logs"
RUN_DIR = BASE_DIR / "run"
SECRET_CACHE_TTL_SECONDS = 300


def configure_pop3_password_env():
    if "POP3_PASSWORD" in os.environ:
        return os.environ["POP3_PASSWORD"]
    return None
def get_gcp_project_id():
    explicit = os.environ.get("BIZTOGMAIL_GCP_PROJECT")
    if explicit is not None:
        return explicit or None
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or _get_gcloud_config_project()
    )


def get_session_secret():
    return os.environ.get("BIZTOGMAIL_SESSION_SECRET") or "biztogmail-dev-session-secret"


def get_scheduler_token():
    return os.environ.get("BIZTOGMAIL_SCHEDULER_TOKEN")


def get_google_client_id():
    return os.environ.get("GOOGLE_OIDC_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID")


def get_google_client_secret():
    return os.environ.get("GOOGLE_OIDC_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET")


def get_google_redirect_uri():
    return os.environ.get("GOOGLE_OIDC_REDIRECT_URI")


def get_secret_value(secret_ref: str | None):
    if not secret_ref:
        return None
    if secret_ref.startswith("env:"):
        return os.environ.get(secret_ref[4:])
    return None


@lru_cache(maxsize=1)
def _get_gcloud_config_project():
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    value = (result.stdout or "").strip()
    if not value or value == "(unset)":
        return None
    return value


def get_google_web_client_config():
    client_id = get_google_client_id()
    client_secret = get_google_client_secret()
    redirect_uri = get_google_redirect_uri()
    if not client_id or not client_secret:
        return None
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri] if redirect_uri else [],
        }
    }
