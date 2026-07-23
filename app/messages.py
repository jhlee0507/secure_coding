from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy import and_, or_

from .audit import record
from .extensions import db, limiter
from .models import Message, User
from .security import clean_text, login_required


bp = Blueprint("messages", __name__, url_prefix="/messages")


def _other_user_or_404(user_id: int) -> User:
    other = db.session.get(User, user_id)
    if other is None or other.is_banned:
        abort(404)
    if other.id == g.user.id:
        abort(400)
    return other


def _conversation_between(other: User):
    return or_(
        and_(Message.sender_id == g.user.id, Message.recipient_id == other.id),
        and_(Message.sender_id == other.id, Message.recipient_id == g.user.id),
    )


@bp.get("")
@login_required
def inbox():
    messages = db.session.scalars(
        db.select(Message)
        .where(or_(Message.sender_id == g.user.id, Message.recipient_id == g.user.id))
        .order_by(Message.created_at.desc())
        .limit(100)
    ).all()
    partners: dict[int, User] = {}
    for message in messages:
        partner = message.recipient if message.sender_id == g.user.id else message.sender
        partners.setdefault(partner.id, partner)
    users = db.session.scalars(
        db.select(User)
        .where(User.id != g.user.id, User.is_banned.is_(False))
        .order_by(User.username)
        .limit(50)
    ).all()
    return render_template("messages/inbox.html", partners=partners.values(), users=users)


@bp.route("/<int:user_id>", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute", methods=["POST"])
def conversation(user_id: int):
    other = _other_user_or_404(user_id)

    if request.method == "POST":
        body = clean_text(request.form.get("body", ""), minimum=1, maximum=1000)
        if body is None:
            flash("메시지는 1~1000자로 입력하세요.", "error")
        else:
            message = Message(sender_id=g.user.id, recipient_id=other.id, body=body)
            db.session.add(message)
            db.session.flush()
            record("message_send", "message", message.id, f"recipient={other.id}")
            db.session.commit()
            return redirect(url_for("messages.conversation", user_id=other.id))

    conversation_messages = db.session.scalars(
        db.select(Message)
        .where(_conversation_between(other))
        .order_by(Message.created_at.asc())
        .limit(500)
    ).all()
    return render_template(
        "messages/conversation.html", other=other, messages=conversation_messages
    )


@bp.get("/<int:user_id>/updates")
@login_required
@limiter.limit("30 per minute")
def conversation_updates(user_id: int):
    other = _other_user_or_404(user_id)
    try:
        after_id = int(request.args.get("after", "0"))
    except ValueError:
        abort(400)
    if after_id < 0:
        abort(400)

    new_messages = db.session.scalars(
        db.select(Message)
        .where(_conversation_between(other), Message.id > after_id)
        .order_by(Message.id.asc())
        .limit(100)
    ).all()
    return jsonify(
        messages=[
            {
                "id": message.id,
                "sender": message.sender.username,
                "body": message.body,
                "created_at": message.created_at.isoformat(),
                "is_mine": message.sender_id == g.user.id,
            }
            for message in new_messages
        ]
    )
