from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .audit import record
from .extensions import db, limiter
from .models import User
from .security import clean_text, is_safe_redirect, login_required, validate_password, validate_username


bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    if g.user:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not validate_username(username):
            flash("사용자명은 영문, 숫자, 밑줄로 구성된 3~20자여야 합니다.", "error")
        elif not validate_password(password):
            flash("비밀번호는 10자 이상이며 대·소문자, 숫자, 특수문자를 포함해야 합니다.", "error")
        else:
            user = User(
                username=username,
                password_hash=generate_password_hash(password, method="scrypt"),
                balance=current_app.config["INITIAL_DEMO_BALANCE"],
            )
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("이미 사용 중인 사용자명입니다.", "error")
            else:
                flash("회원가입이 완료되었습니다.", "success")
                return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if g.user:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user is None or not check_password_hash(user.password_hash, password) or user.is_banned:
            flash("사용자명 또는 비밀번호가 올바르지 않습니다.", "error")
        else:
            session.clear()
            session["user_id"] = user.id
            session.permanent = True
            record("login", "user", user.id)
            db.session.commit()
            next_url = request.args.get("next")
            return redirect(next_url if is_safe_redirect(next_url) else url_for("main.dashboard"))
    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    user_id = g.user.id
    record("logout", "user", user_id)
    db.session.commit()
    session.clear()
    flash("로그아웃했습니다.", "success")
    return redirect(url_for("main.index"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        bio = clean_text(request.form.get("bio", ""), minimum=0, maximum=500)
        if bio is None:
            flash("자기소개는 500자 이하여야 합니다.", "error")
        else:
            g.user.bio = bio
            record("profile_update", "user", g.user.id)
            db.session.commit()
            flash("프로필을 수정했습니다.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html")

