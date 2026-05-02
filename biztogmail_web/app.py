from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from biztogmail_app.accounts import create_saved_account, delete_saved_account, get_saved_account, list_due_accounts, list_saved_accounts, update_saved_account
from biztogmail_app.logging_utils import RunLogger
from biztogmail_app.locks import FileLock
from biztogmail_app.scheduler import AccountExecutionLockedError, run_account_now
from biztogmail_app.settings import get_scheduler_token, get_session_secret
from biztogmail_app.secrets import build_smtp_secret_ref, build_source_secret_ref, store_secret_value
from biztogmail_app.workflows import run_smtp_forward_workflow
from .auth import build_google_flow, fetch_google_userinfo, get_google_user, require_google_user
from .schemas import AccountCreate, AccountResponse, AccountUpdate, RunRequest, SchedulerRunResult, WorkflowResponse


app = FastAPI(title="BizToGmail")
app.add_middleware(SessionMiddleware, secret_key=get_session_secret())
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _external_request_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto == "https":
        return str(request.url.replace(scheme="https"))
    return str(request.url)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/session")
def auth_session(request: Request):
    user = get_google_user(request)
    return {"authenticated": bool(user), "user": user}


@app.get("/auth/login")
async def auth_login(request: Request):
    flow = build_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["google_oauth_state"] = state
    if getattr(flow, "code_verifier", None):
        request.session["google_oauth_code_verifier"] = flow.code_verifier
    return RedirectResponse(url=authorization_url)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    state = request.session.get("google_oauth_state")
    code_verifier = request.session.get("google_oauth_code_verifier")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    flow = build_google_flow(state=state)
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=_external_request_url(request))
    user = fetch_google_userinfo(flow.credentials.token)
    request.session["google_user"] = {
        "email": user["email"],
        "name": user.get("name"),
        "picture": user.get("picture"),
    }
    request.session.pop("google_oauth_state", None)
    request.session.pop("google_oauth_code_verifier", None)
    return RedirectResponse(url="/")


@app.get("/auth/logout")
def auth_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


def _filter_accounts_for_user(accounts: list[dict], user: dict):
    return [account for account in accounts if account.get("destination_email") == user["email"]]


def _get_owned_account(account_id: int, user: dict):
    account = get_saved_account(account_id)
    if account is None or account.get("destination_email") != user["email"]:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def _store_secret_or_raise(secret_ref: str, value: str, label: str):
    try:
        store_secret_value(secret_ref, value)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{label} の Secret Manager 保存に失敗しました: {exc}") from exc


def _is_scheduler_authorized(request: Request) -> bool:
    configured = get_scheduler_token()
    if not configured:
        return False
    provided = request.headers.get("X-Scheduler-Token")
    return bool(provided) and provided == configured


@app.get("/accounts", response_model=list[AccountResponse])
def list_accounts(request: Request):
    user = require_google_user(request)
    return [AccountResponse(**account) for account in _filter_accounts_for_user(list_saved_accounts(), user)]


@app.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, request: Request):
    user = require_google_user(request)
    account = _get_owned_account(account_id, user)
    return AccountResponse(**account)


@app.post("/accounts", response_model=AccountResponse)
def create_account(request: AccountCreate, http_request: Request):
    user = require_google_user(http_request)
    payload = request.model_dump()
    smtp_username = payload.get("smtp_username")
    if not smtp_username:
        raise HTTPException(status_code=400, detail="SMTP ユーザーを入力してください")
    source_username = payload.get("source_username") or smtp_username
    source_password = payload.get("pop_password")
    smtp_password = payload.get("smtp_password")
    if not smtp_password:
        raise HTTPException(status_code=400, detail="SMTP パスワードを入力してください")
    source_password = source_password or smtp_password
    payload["pop_host"] = payload.get("pop_host") or payload.get("smtp_host")
    if not payload.get("smtp_host"):
        raise HTTPException(status_code=400, detail="SMTP サーバーを入力してください")
    payload["source_username"] = source_username
    payload["smtp_username"] = smtp_username
    payload["destination_email"] = user["email"]
    payload["secret_ref"] = payload.get("secret_ref") or build_source_secret_ref(source_username)
    payload["smtp_secret_ref"] = payload.get("smtp_secret_ref") or build_smtp_secret_ref(smtp_username)
    if payload["secret_ref"] and payload["smtp_secret_ref"]:
        _store_secret_or_raise(payload["secret_ref"], source_password, "POP/IMAP パスワード")
        _store_secret_or_raise(payload["smtp_secret_ref"], smtp_password, "SMTP パスワード")
        payload["pop_password"] = None
        payload["smtp_password"] = None
    else:
        payload["pop_password"] = source_password
        payload["smtp_password"] = smtp_password
        payload["secret_ref"] = None
        payload["smtp_secret_ref"] = None
    account = create_saved_account(**payload)
    return AccountResponse(**account)


@app.patch("/accounts/{account_id}", response_model=AccountResponse)
def patch_account(account_id: int, request: AccountUpdate, http_request: Request):
    user = require_google_user(http_request)
    current = _get_owned_account(account_id, user)
    updates = request.model_dump(exclude_unset=True)
    smtp_username = updates.get("smtp_username", current.get("smtp_username"))
    if "smtp_username" in updates and not updates.get("smtp_username"):
        raise HTTPException(status_code=400, detail="SMTP ユーザーを入力してください")
    if not smtp_username:
        raise HTTPException(status_code=400, detail="SMTP ユーザーを入力してください")
    source_username = updates.get("source_username", current.get("source_username") or smtp_username)
    if "source_username" in updates:
        updates["source_username"] = source_username
    if "smtp_username" in updates:
        updates["smtp_username"] = smtp_username
    if "pop_host" in updates and not updates["pop_host"]:
        updates["pop_host"] = updates.get("smtp_host", current.get("smtp_host"))
    if updates.get("pop_password"):
        secret_ref = current.get("secret_ref") or build_source_secret_ref(source_username)
        if secret_ref:
            _store_secret_or_raise(secret_ref, updates["pop_password"], "POP/IMAP パスワード")
            updates["secret_ref"] = secret_ref
            updates["pop_password"] = None
    elif updates.get("smtp_password") and not current.get("secret_ref"):
        secret_ref = build_source_secret_ref(source_username)
        if secret_ref:
            _store_secret_or_raise(secret_ref, updates["smtp_password"], "POP/IMAP パスワード")
            updates["secret_ref"] = secret_ref
    if updates.get("smtp_password"):
        smtp_secret_ref = current.get("smtp_secret_ref") or build_smtp_secret_ref(smtp_username)
        if smtp_secret_ref:
            _store_secret_or_raise(smtp_secret_ref, updates["smtp_password"], "SMTP パスワード")
            updates["smtp_secret_ref"] = smtp_secret_ref
            updates["smtp_password"] = None
    updates.pop("destination_email", None)
    account = update_saved_account(account_id, updates)
    return AccountResponse(**account)


@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, request: Request):
    user = require_google_user(request)
    _get_owned_account(account_id, user)
    deleted = delete_saved_account(account_id)
    return {"status": "deleted", "account_id": account_id}


@app.post("/accounts/{account_id}/run", response_model=WorkflowResponse)
def run_account(account_id: int, request: Request):
    user = require_google_user(request)
    _get_owned_account(account_id, user)
    logger = RunLogger()
    logger.setup(f"account-{account_id}-web")
    try:
        result = run_account_now(account_id, logger=logger)
    except AccountExecutionLockedError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return WorkflowResponse(**result["result"])


@app.post("/scheduler/tick", response_model=list[SchedulerRunResult])
def scheduler_tick(request: Request):
    scheduler_authorized = _is_scheduler_authorized(request)
    user = None if scheduler_authorized else require_google_user(request)
    lock = FileLock("scheduler-web-tick")
    if not lock.acquire():
        raise HTTPException(status_code=409, detail="Scheduler tick already running")
    logger = RunLogger()
    logger.setup("scheduler-web")
    try:
        results = []
        due_accounts = list_due_accounts()
        if user is not None:
            due_accounts = _filter_accounts_for_user(due_accounts, user)
        for account in due_accounts:
            try:
                results.append(run_account_now(account["id"], logger=logger))
            except AccountExecutionLockedError as e:
                logger.append(f"scheduler skipped locked account_id={account['id']} error={e}")
                results.append({"account": account, "status": "locked", "error": str(e)})
            except Exception as e:
                logger.append(f"scheduler failed account_id={account['id']} error={e}", error=True)
                results.append({"account": account, "error": str(e)})
        payload = []
        for item in results:
            account = item["account"]
            if "error" in item:
                payload.append(
                    SchedulerRunResult(
                        account_id=account["id"],
                        email=account["email"],
                        status=item.get("status") or "error",
                        error=item["error"],
                    )
                )
            else:
                payload.append(
                    SchedulerRunResult(
                        account_id=account["id"],
                        email=account["email"],
                        status="ok",
                        summary=item["result"]["summary"],
                    )
                )
        return payload
    finally:
        lock.release()
@app.post("/run", response_model=WorkflowResponse)
def run_import(request: RunRequest, http_request: Request):
    user = require_google_user(http_request)
    logger = RunLogger()
    logger.setup("run-web")
    if not request.smtp_host:
        raise HTTPException(status_code=400, detail="SMTP サーバーを入力してください")
    if not request.smtp_username:
        raise HTTPException(status_code=400, detail="SMTP ユーザーを入力してください")
    result = run_smtp_forward_workflow(
        source_protocol=request.source_protocol,
        source_folder=request.source_folder,
        host=request.host,
        user=request.user,
        password=request.password,
        port=request.port,
        use_ssl=request.ssl,
        max_items=request.max,
        destination_email=user["email"],
        smtp_host=request.smtp_host,
        smtp_port=request.smtp_port,
        smtp_use_ssl=request.smtp_use_ssl,
        smtp_username=request.smtp_username,
        smtp_password=request.smtp_password or request.password,
        no_leave_copy=request.no_leave_copy,
        delete_after_days=request.delete_after_days,
        dry_run=request.dry_run,
        logger=logger,
    )
    return WorkflowResponse(**result)
