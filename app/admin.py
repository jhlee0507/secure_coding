from datetime import datetime, timezone

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .audit import record
from .extensions import db, limiter
from .models import AuditLog, Message, Product, Report, Transfer, User
from .security import admin_required


bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("")
@admin_required
def dashboard():
    users = db.session.scalars(db.select(User).order_by(User.created_at.desc())).all()
    products = db.session.scalars(db.select(Product).order_by(Product.created_at.desc())).all()
    reports = db.session.scalars(
        db.select(Report).order_by(Report.status.asc(), Report.created_at.desc())
    ).all()
    transfers = db.session.scalars(
        db.select(Transfer).order_by(Transfer.created_at.desc()).limit(50)
    ).all()
    message_count = db.session.scalar(db.select(db.func.count()).select_from(Message))
    logs = db.session.scalars(
        db.select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
    ).all()
    return render_template(
        "admin/dashboard.html",
        users=users,
        products=products,
        reports=reports,
        transfers=transfers,
        message_count=message_count,
        logs=logs,
    )


@bp.post("/users/<int:user_id>/toggle-ban")
@admin_required
@limiter.limit("30 per minute")
def toggle_user_ban(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == g.user.id or user.is_admin:
        abort(400)
    user.is_banned = not user.is_banned
    if user.is_banned:
        for product in user.products:
            product.is_hidden = True
    record("admin_toggle_user_ban", "user", user.id, str(user.is_banned))
    db.session.commit()
    flash("사용자 상태를 변경했습니다.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/products/<int:product_id>/toggle-hidden")
@admin_required
def toggle_product_hidden(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    product.is_hidden = not product.is_hidden
    record("admin_toggle_product_hidden", "product", product.id, str(product.is_hidden))
    db.session.commit()
    flash("상품 공개 상태를 변경했습니다.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/reports/<int:report_id>/handle")
@admin_required
def handle_report(report_id: int):
    report = db.session.get(Report, report_id)
    if report is None:
        abort(404)
    action = request.form.get("action")
    if action not in {"resolve", "dismiss"}:
        abort(400)

    if action == "resolve":
        if report.target_type == "user":
            target = db.session.get(User, report.target_id)
            if target and not target.is_admin:
                target.is_banned = True
                for product in target.products:
                    product.is_hidden = True
        else:
            target = db.session.get(Product, report.target_id)
            if target:
                target.is_hidden = True
        report.status = "resolved"
    else:
        report.status = "dismissed"

    report.handled_by_id = g.user.id
    report.handled_at = datetime.now(timezone.utc)
    record("admin_handle_report", "report", report.id, report.status)
    db.session.commit()
    flash("신고를 처리했습니다.", "success")
    return redirect(url_for("admin.dashboard"))

