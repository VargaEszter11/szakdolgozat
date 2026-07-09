import smtplib

import pytest
from fastapi import HTTPException

from backend.utils.email import send_email, send_password_reset_email


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=10):
        self.host = host
        self.port = port
        self.starttls_called = False
        self.login_args = None
        self.sent_message = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def starttls(self):
        self.starttls_called = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.sent_message = message


@pytest.fixture(autouse=True)
def reset_fake_smtp():
    FakeSMTP.instances = []
    yield
    FakeSMTP.instances = []


def _set_smtp_env(monkeypatch, **overrides):
    defaults = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user@example.com",
        "SMTP_PASSWORD": "app-password",
        "SMTP_FROM": "noreply@example.com",
        "SMTP_USE_TLS": "true",
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)


def test_send_email_raises_when_smtp_host_missing(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        send_email("to@example.com", "Subject", "Body")

    assert exc_info.value.status_code == 500


def test_send_email_sends_via_smtp(monkeypatch):
    _set_smtp_env(monkeypatch)
    monkeypatch.setattr("backend.utils.email.smtplib.SMTP", FakeSMTP)

    send_email("to@example.com", "Subject", "Body text")

    assert len(FakeSMTP.instances) == 1
    server = FakeSMTP.instances[0]
    assert server.starttls_called is True
    assert server.login_args == ("user@example.com", "app-password")
    assert server.sent_message["To"] == "to@example.com"
    assert server.sent_message["From"] == "noreply@example.com"
    assert server.sent_message["Subject"] == "Subject"


def test_send_email_skips_login_when_no_username(monkeypatch):
    _set_smtp_env(monkeypatch, SMTP_USER="", SMTP_FROM="noreply@example.com")
    monkeypatch.setattr("backend.utils.email.smtplib.SMTP", FakeSMTP)

    send_email("to@example.com", "Subject", "Body")

    assert FakeSMTP.instances[0].login_args is None


def test_send_email_raises_502_on_smtp_error(monkeypatch):
    _set_smtp_env(monkeypatch)

    class FailingSMTP(FakeSMTP):
        def send_message(self, message):
            raise smtplib.SMTPException("boom")

    monkeypatch.setattr("backend.utils.email.smtplib.SMTP", FailingSMTP)

    with pytest.raises(HTTPException) as exc_info:
        send_email("to@example.com", "Subject", "Body")

    assert exc_info.value.status_code == 502


def test_send_password_reset_email_includes_url_and_ttl(monkeypatch):
    _set_smtp_env(monkeypatch)
    monkeypatch.setattr("backend.utils.email.smtplib.SMTP", FakeSMTP)

    send_password_reset_email("to@example.com", "https://app.example.com/reset-password?token=abc", 30)

    server = FakeSMTP.instances[0]
    body = server.sent_message.get_content()
    assert "https://app.example.com/reset-password?token=abc" in body
    assert "30 minutes" in body
