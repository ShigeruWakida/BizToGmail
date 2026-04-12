import argparse

from .commands import cmd_run, cmd_scheduler
from .logging_utils import RunLogger


def build_parser():
    parser = argparse.ArgumentParser(prog="biztogmail", description="POP3 -> SMTP forward")
    sub = parser.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="Forward up to N messages via SMTP")
    p_run.add_argument("--host", required=True)
    p_run.add_argument("--user", required=True)
    p_run.add_argument("--protocol", choices=["pop3", "imap"], default="pop3")
    p_run.add_argument("--folder", help="IMAP folder name (default: INBOX)")
    p_run.add_argument("--port", type=int, default=995)
    p_run.add_argument("--ssl", action="store_true", default=True)
    p_run.add_argument("--no-ssl", dest="ssl", action="store_false")
    p_run.add_argument("--max", type=int, default=3)
    p_run.add_argument("--destination", required=True, help="Destination email address to forward to")
    p_run.add_argument("--smtp-host", help="SMTP relay host (default: POP host)")
    p_run.add_argument("--smtp-port", type=int, default=465)
    p_run.add_argument("--smtp-ssl", action="store_true", default=True)
    p_run.add_argument("--smtp-no-ssl", dest="smtp_ssl", action="store_false")
    p_run.add_argument("--smtp-user", help="SMTP auth username (default: POP user)")
    p_run.add_argument("--smtp-password", help="SMTP auth password (default: POP password)")
    p_run.add_argument("--no-leave-copy", action="store_true", help="After successful import, delete the message from the POP server")
    p_run.add_argument("--delete-after-days", type=int, help="Delete from POP server if Date header is older than N days")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.set_defaults(handler=cmd_run)

    p_scheduler = sub.add_parser("scheduler", help="Run scheduled account checks")
    p_scheduler.add_argument("--interval-seconds", type=int, default=60)
    p_scheduler.add_argument("--once", action="store_true", help="Run one scheduler tick and exit")
    p_scheduler.set_defaults(handler=cmd_scheduler)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return
    args.handler(args, RunLogger())
