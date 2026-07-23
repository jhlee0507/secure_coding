from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from .audit import record
from .extensions import db, limiter
from .models import Product, Report, User
from .security import clean_text, login_required


bp = Blueprint("reports", __name__, url_prefix="/reports")


def _target_exists(target_type: str, target_id: int) -> bool:
    if target_type == "user":
        return db.session.get(User, target_id) is not None
    if target_type == "product":
        return db.session.get(Product, target_id) is not None
    return False


@bp.route("/new", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per hour", methods=["POST"])
def create():
    target_type = request.values.get("target_type", "")
    try:
        target_id = int(request.values.get("target_id", ""))
    except ValueError:
        target_id = 0

    if request.method == "POST":
        reason = clean_text(request.form.get("reason", ""), minimum=10, maximum=500)
        if target_type not in {"user", "product"} or not _target_exists(target_type, target_id):
            abort(400)
        if target_type == "user" and target_id == g.user.id:
            abort(400)
        if reason is None:
            flash("신고 사유를 10~500자로 입력하세요.", "error")
        else:
            report = Report(
                reporter_id=g.user.id,
                target_type=target_type,
                target_id=target_id,
                reason=reason,
            )
            db.session.add(report)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                flash("동일한 대상에 처리 중인 신고가 있습니다.", "error")
            else:
                record("report_create", "report", report.id)
                db.session.commit()
                flash("신고를 접수했습니다.", "success")
                return redirect(url_for("main.dashboard"))
    return render_template(
        "reports/form.html", target_type=target_type, target_id=target_id
    )

