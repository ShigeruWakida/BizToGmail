from __future__ import annotations

import getpass
from .logging_utils import RunLogger
from .scheduler_runner import run_scheduler_loop
from .settings import configure_pop3_password_env
from .workflows import run_smtp_forward_workflow


def _get_password(user: str, host: str) -> str:
    env_password = configure_pop3_password_env()
    if env_password is not None:
        return env_password
    return getpass.getpass(prompt=f"POP3 password ({user}@{host}): ")

def cmd_run(args, logger: RunLogger):
    logger.setup("run")
    pop_password = _get_password(args.user, args.host)
    smtp_password = args.smtp_password if getattr(args, "smtp_password", None) else pop_password
    result = run_smtp_forward_workflow(
        source_protocol=args.protocol,
        source_folder=getattr(args, "folder", None),
        host=args.host,
        user=args.user,
        password=pop_password,
        port=args.port,
        use_ssl=args.ssl,
        max_items=args.max,
        destination_email=args.destination,
        smtp_host=args.smtp_host or args.host,
        smtp_port=args.smtp_port,
        smtp_use_ssl=args.smtp_ssl,
        smtp_username=args.smtp_user or args.user,
        smtp_password=smtp_password,
        no_leave_copy=args.no_leave_copy,
        delete_after_days=args.delete_after_days,
        dry_run=args.dry_run,
        logger=logger,
    )
    for event in result["events"]:
        print(event)
    summary = result["summary"]
    print(f"done: forwarded={summary['imported']}, skipped={summary['skipped']}, errors={summary['errors']}")
    if logger.log_file_path is not None:
        print(f"log file: {logger.log_file_path}")


def cmd_scheduler(args, logger: RunLogger):
    logger.setup("scheduler-cli")
    try:
        run_scheduler_loop(
            interval_seconds=args.interval_seconds,
            once=args.once,
            logger=logger,
        )
    except RuntimeError as e:
        print(str(e))
        logger.append(str(e), error=True)
