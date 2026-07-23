from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
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
@limiter.limit("10 per minute", methods=["POST"])
def profile():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_profile":
            bio = clean_text(request.form.get("bio", ""), minimum=0, maximum=500)
            if bio is None:
                flash("자기소개는 500자 이하여야 합니다.", "error")
                return render_template("auth/profile.html")
            g.user.bio = bio
            record("profile_update", "user", g.user.id)
            db.session.commit()
            flash("프로필을 수정했습니다.", "success")
            return redirect(url_for("auth.profile"))
        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            password_confirmation = request.form.get("password_confirmation", "")
            if not check_password_hash(g.user.password_hash, current_password):
                flash("현재 비밀번호가 올바르지 않습니다.", "error")
            elif new_password != password_confirmation:
                flash("새 비밀번호 확인이 일치하지 않습니다.", "error")
            elif not validate_password(new_password):
                flash(
                    "새 비밀번호는 10자 이상이며 대·소문자, 숫자, 특수문자를 포함해야 합니다.",
                    "error",
                )
            elif check_password_hash(g.user.password_hash, new_password):
                flash("현재 비밀번호와 다른 비밀번호를 사용하세요.", "error")
            else:
                user_id = g.user.id
                g.user.password_hash = generate_password_hash(
                    new_password, method="scrypt"
                )
                record("password_change", "user", user_id)
                db.session.commit()
                session.clear()
                flash("비밀번호를 변경했습니다. 새 비밀번호로 다시 로그인하세요.", "success")
                return redirect(url_for("auth.login"))
        else:
            abort(400)
    return render_template("auth/profile.html")
