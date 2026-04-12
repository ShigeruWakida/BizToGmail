from __future__ import annotations

import smtplib
from email.parser import BytesParser
from email.policy import SMTP


def send_raw_via_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    use_ssl: bool,
    username: str | None,
    password: str | None,
    destination_email: str,
    raw_bytes: bytes,
):
    parsed = BytesParser(policy=SMTP).parsebytes(raw_bytes)
    envelope_from = username or parsed.get("From") or destination_email

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            if username and password:
                server.login(username, password)
            server.sendmail(envelope_from, [destination_email], raw_bytes)
        return

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        try:
            server.starttls()
            server.ehlo()
        except smtplib.SMTPNotSupportedError:
            pass
        if username and password:
            server.login(username, password)
        server.sendmail(envelope_from, [destination_email], raw_bytes)
