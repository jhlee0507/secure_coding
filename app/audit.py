from flask import g

from .extensions import db
from .models import AuditLog


def record(action: str, target_type: str, target_id: int | None, detail: str = "") -> None:
    actor_id = g.user.id if getattr(g, "user", None) else None
    db.session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail[:500],
        )
    )

