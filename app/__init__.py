import os

import click
from flask import Flask, g, render_template, session
from flask_wtf.csrf import CSRFError
from werkzeug.security import generate_password_hash

from .config import Config
from .extensions import csrf, db, limiter
from .models import User


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    secret_key = app.config.get("SECRET_KEY") or ""
    production_mode = app.config.get("APP_ENV") == "production"
    if (production_mode or app.config.get("SESSION_COOKIE_SECURE")) and (
        secret_key.startswith("development-only-") or len(secret_key) < 32
    ):
        raise RuntimeError("Set a strong SECRET_KEY before enabling production mode.")
    if production_mode and not app.config.get("SESSION_COOKIE_SECURE"):
        raise RuntimeError("Set COOKIE_SECURE=true in production mode.")

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .messages import bp as messages_bp
    from .products import bp as products_bp
    from .reports import bp as reports_bp
    from .wallet import bp as wallet_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def load_user() -> None:
        user_id = session.get("user_id")
        g.user = db.session.get(User, user_id) if user_id else None
        if g.user is not None and g.user.is_banned:
            session.clear()
            g.user = None

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self'; "
            "script-src 'self'; "
            "img-src 'self' data:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
            "form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return render_template("error.html", code=400, message="요청이 만료되었거나 유효하지 않습니다."), 400

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template("error.html", code=400, message="올바르지 않은 요청입니다."), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, message="이 작업을 수행할 권한이 없습니다."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="요청한 페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(429)
    def rate_limited(_error):
        return render_template("error.html", code=429, message="요청이 너무 많습니다. 잠시 후 다시 시도하세요."), 429

    @app.cli.command("init-db")
    def init_db_command() -> None:
        db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin_command(username: str, password: str) -> None:
        from .security import validate_password, validate_username

        if not validate_username(username) or not validate_password(password):
            raise click.ClickException(
                "Username or password does not meet the documented policy."
            )
        if db.session.scalar(db.select(User).where(User.username == username)):
            raise click.ClickException("Username already exists.")
        user = User(
            username=username,
            password_hash=generate_password_hash(password, method="scrypt"),
            is_admin=True,
            balance=app.config["INITIAL_DEMO_BALANCE"],
        )
        db.session.add(user)
        db.session.commit()
        click.echo("Administrator created.")

    return app
