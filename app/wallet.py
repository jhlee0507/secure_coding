from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import or_, update
from werkzeug.security import check_password_hash

from .audit import record
from .extensions import db, limiter
from .models import Transfer, User
from .security import login_required, validate_username


bp = Blueprint("wallet", __name__, url_prefix="/wallet")


@bp.get("")
@login_required
def overview():
    transfers = db.session.scalars(
        db.select(Transfer)
        .where(or_(Transfer.sender_id == g.user.id, Transfer.recipient_id == g.user.id))
        .order_by(Transfer.created_at.desc())
        .limit(50)
    ).all()
    return render_template("wallet/overview.html", transfers=transfers)


@bp.post("/transfer")
@login_required
@limiter.limit("5 per minute")
def transfer():
    receiver_name = request.form.get("receiver", "").strip()
    password = request.form.get("password", "")
    try:
        amount = int(request.form.get("amount", ""))
    except ValueError:
        amount = 0

    if not validate_username(receiver_name) or not 1 <= amount <= 10_000_000:
        flash("수신자와 1~10,000,000 사이의 금액을 입력하세요.", "error")
        return redirect(url_for("wallet.overview"))
    if not check_password_hash(g.user.password_hash, password):
        flash("본인 확인에 실패했습니다.", "error")
        return redirect(url_for("wallet.overview"))

    receiver = db.session.scalar(db.select(User).where(User.username == receiver_name))
    if receiver is None or receiver.is_banned:
        flash("송금할 수 없는 사용자입니다.", "error")
        return redirect(url_for("wallet.overview"))
    if receiver.id == g.user.id:
        abort(400)

    debit = db.session.execute(
        update(User)
        .where(User.id == g.user.id, User.balance >= amount)
        .values(balance=User.balance - amount)
    )
    if debit.rowcount != 1:
        db.session.rollback()
        flash("잔액이 부족합니다.", "error")
        return redirect(url_for("wallet.overview"))

    db.session.execute(
        update(User).where(User.id == receiver.id).values(balance=User.balance + amount)
    )
    transfer_entry = Transfer(sender_id=g.user.id, recipient_id=receiver.id, amount=amount)
    db.session.add(transfer_entry)
    db.session.flush()
    record("transfer", "transfer", transfer_entry.id, f"amount={amount};recipient={receiver.id}")
    db.session.commit()
    flash(f"{receiver.username}님에게 {amount:,}포인트를 보냈습니다.", "success")
    return redirect(url_for("wallet.overview"))

