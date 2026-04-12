from __future__ import annotations

import re
import time

try:
    from google.cloud import secretmanager
except Exception:  # pragma: no cover
    secretmanager = None

try:
    from google.api_core.exceptions import AlreadyExists, NotFound
except Exception:  # pragma: no cover
    AlreadyExists = NotFound = Exception

from .settings import SECRET_CACHE_TTL_SECONDS, get_gcp_project_id, get_secret_value


_SECRET_CACHE: dict[str, tuple[float, str]] = {}
_GCP_SECRET_REF_RE = re.compile(
    r"^projects/(?P<project>[^/]+)/secrets/(?P<secret>[^/]+)/versions/(?P<version>[^/]+)$"
)


def resolve_account_password(account: dict) -> str | None:
    if account.get("secret_ref"):
        secret = resolve_secret_ref(account["secret_ref"])
        if secret:
            return secret
    return account.get("pop_password") or account.get("smtp_password") or resolve_account_smtp_password(account)


def resolve_account_smtp_password(account: dict, source_password: str | None = None) -> str | None:
    if account.get("smtp_secret_ref"):
        secret = resolve_secret_ref(account["smtp_secret_ref"])
        if secret:
            return secret
    return account.get("smtp_password") or source_password


def resolve_secret_ref(secret_ref: str | None, *, force_refresh: bool = False) -> str | None:
    if not secret_ref:
        return None
    if not force_refresh:
        cached = _SECRET_CACHE.get(secret_ref)
        if cached and cached[0] > time.time():
            return cached[1]
    if secret_ref.startswith("env:"):
        value = get_secret_value(secret_ref)
    elif secret_ref.startswith("gcp:"):
        value = _resolve_gcp_secret(secret_ref[4:])
    else:
        value = None
    if value:
        _SECRET_CACHE[secret_ref] = (time.time() + SECRET_CACHE_TTL_SECONDS, value)
    return value


def invalidate_secret_ref(secret_ref: str | None):
    if secret_ref:
        _SECRET_CACHE.pop(secret_ref, None)


def build_gcp_secret_ref(email: str, project_id: str | None = None, *, prefix: str = "source-password") -> str | None:
    resolved_project = project_id or get_gcp_project_id()
    if not resolved_project or not email:
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", email.strip().lower()).strip("-")
    if not slug:
        return None
    return f"gcp:projects/{resolved_project}/secrets/{prefix}-{slug}/versions/latest"


def build_source_secret_ref(username: str, project_id: str | None = None) -> str | None:
    return build_gcp_secret_ref(username, project_id, prefix="source-password")


def build_smtp_secret_ref(username: str, project_id: str | None = None) -> str | None:
    return build_gcp_secret_ref(username, project_id, prefix="smtp-password")


def store_secret_value(secret_ref: str | None, value: str) -> str | None:
    if not secret_ref or not value:
        return secret_ref
    if secret_ref.startswith("gcp:"):
        _store_gcp_secret(secret_ref[4:], value)
    elif secret_ref.startswith("env:"):
        raise ValueError("env secret_ref does not support write operations")
    else:
        raise ValueError(f"Unsupported secret_ref: {secret_ref}")
    _SECRET_CACHE[secret_ref] = (time.time() + SECRET_CACHE_TTL_SECONDS, value)
    return secret_ref


def _resolve_gcp_secret(resource_name: str) -> str | None:
    if secretmanager is None:
        return None
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": resource_name})
    return response.payload.data.decode("utf-8")


def _store_gcp_secret(resource_name: str, value: str):
    if secretmanager is None:
        raise ValueError("google-cloud-secret-manager is not available")
    match = _GCP_SECRET_REF_RE.match(resource_name)
    if not match:
        raise ValueError(f"Invalid GCP secret resource: {resource_name}")

    parent = f"projects/{match.group('project')}"
    secret_id = match.group("secret")
    client = secretmanager.SecretManagerServiceClient()
    try:
        client.get_secret(request={"name": f"{parent}/secrets/{secret_id}"})
    except NotFound:
        try:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except AlreadyExists:
            pass
    client.add_secret_version(
        request={
            "parent": f"{parent}/secrets/{secret_id}",
            "payload": {"data": value.encode("utf-8")},
        }
    )
