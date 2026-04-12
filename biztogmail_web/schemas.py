from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    source_protocol: str = "pop3"
    source_folder: str | None = None
    host: str
    user: str
    password: str
    port: int = 995
    ssl: bool = True
    max: int = Field(default=3, ge=1)
    no_leave_copy: bool = False
    delete_after_days: int | None = Field(default=None, ge=1)
    dry_run: bool = False
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_username: str | None = None
    smtp_password: str | None = None


class WorkflowResponse(BaseModel):
    events: list[str]
    summary: dict[str, int]


class AccountBase(BaseModel):
    email: str
    source_username: str | None = None
    source_protocol: str = "pop3"
    source_folder: str | None = None
    pop_host: str | None = None
    pop_port: int = 995
    use_ssl: bool = True
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_username: str | None = None
    leave_copy: bool = True
    delete_after_days: int | None = Field(default=None, ge=1)
    check_interval_minutes: int = Field(default=5, ge=1)
    enabled: bool = True


class AccountCreate(AccountBase):
    pop_password: str | None = None
    secret_ref: str | None = None
    smtp_password: str | None = None
    smtp_secret_ref: str | None = None


class AccountUpdate(BaseModel):
    email: str | None = None
    source_username: str | None = None
    source_protocol: str | None = None
    source_folder: str | None = None
    pop_host: str | None = None
    pop_password: str | None = None
    secret_ref: str | None = None
    pop_port: int | None = None
    use_ssl: bool | None = None
    destination_email: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_use_ssl: bool | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_secret_ref: str | None = None
    leave_copy: bool | None = None
    delete_after_days: int | None = Field(default=None, ge=1)
    check_interval_minutes: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    last_checked_at: str | None = None
    next_check_at: str | None = None


class AccountResponse(AccountBase):
    id: int
    secret_ref: str | None = None
    smtp_secret_ref: str | None = None
    smtp_password: str | None = None
    last_checked_at: str | None = None
    next_check_at: str | None = None
    created_at: str
    updated_at: str


class SchedulerRunResult(BaseModel):
    account_id: int
    email: str
    status: str
    summary: dict[str, int] | None = None
    error: str | None = None
