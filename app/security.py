import re
from functools import wraps
from urllib.parse import urljoin, urlparse

from flask import abort, flash, g, redirect, request, url_for


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("로그인이 필요합니다.", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def is_safe_redirect(target: str | None) -> bool:
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {"http", "https"} and host_url.netloc == redirect_url.netloc


def validate_username(username: str) -> bool:
    return bool(USERNAME_RE.fullmatch(username))


def validate_password(password: str) -> bool:
    return (
        10 <= len(password) <= 128
        and any(ch.islower() for ch in password)
        and any(ch.isupper() for ch in password)
        and any(ch.isdigit() for ch in password)
        and any(not ch.isalnum() for ch in password)
    )


def clean_text(value: str, *, minimum: int, maximum: int) -> str | None:
    value = " ".join(value.strip().split())
    if not minimum <= len(value) <= maximum:
        return None
    return value

