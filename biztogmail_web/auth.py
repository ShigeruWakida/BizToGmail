from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from fastapi import HTTPException, Request as FastAPIRequest
from google_auth_oauthlib.flow import Flow

from biztogmail_app.settings import get_google_redirect_uri, get_google_web_client_config


GOOGLE_SCOPES = ["openid", "email", "profile"]


def build_google_flow(*, state: str | None = None, redirect_uri: str | None = None) -> Flow:
    client_config = get_google_web_client_config()
    if not client_config:
        raise HTTPException(status_code=500, detail="Google OIDC is not configured")
    resolved_redirect_uri = redirect_uri or get_google_redirect_uri()
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_SCOPES,
        state=state,
    )
    flow.redirect_uri = resolved_redirect_uri
    return flow


def get_google_user(request: FastAPIRequest) -> dict | None:
    user = request.session.get("google_user")
    if isinstance(user, dict) and user.get("email"):
        return user
    return None


def require_google_user(request: FastAPIRequest) -> dict:
    user = get_google_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Google login required")
    return user


def fetch_google_userinfo(access_token: str) -> dict:
    req = Request(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
