from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_user_balance_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(255))
    bio: Mapped[str] = mapped_column(db.String(500), default="")
    is_admin: Mapped[bool] = mapped_column(default=False, index=True)
    is_banned: Mapped[bool] = mapped_column(default=False, index=True)
    balance: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    products: Mapped[list["Product"]] = relationship(back_populates="seller")


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_product_price_positive"),
        Index("ix_products_visibility_created", "is_hidden", "is_sold", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(db.String(100), index=True)
    description: Mapped[str] = mapped_column(db.String(2000))
    price: Mapped[int] = mapped_column()
    seller_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), index=True)
    is_hidden: Mapped[bool] = mapped_column(default=False, index=True)
    is_sold: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    seller: Mapped[User] = relationship(back_populates="products")


class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("sender_id <> recipient_id", name="ck_message_not_self"),
        Index("ix_messages_conversation", "sender_id", "recipient_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(db.String(1000))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])


class Transfer(db.Model):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transfer_amount_positive"),
        CheckConstraint("sender_id <> recipient_id", name="ck_transfer_not_self"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])


class Report(db.Model):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("target_type IN ('user', 'product')", name="ck_report_target_type"),
        CheckConstraint(
            "status IN ('pending', 'resolved', 'dismissed')", name="ck_report_status"
        ),
        Index(
            "uq_pending_report",
            "reporter_id",
            "target_type",
            "target_id",
            unique=True,
            sqlite_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(db.String(10), index=True)
    target_id: Mapped[int] = mapped_column(index=True)
    reason: Mapped[str] = mapped_column(db.String(500))
    status: Mapped[str] = mapped_column(db.String(10), default="pending", index=True)
    handled_by_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    handled_at: Mapped[datetime | None] = mapped_column()

    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])
    handled_by: Mapped[User | None] = relationship(foreign_keys=[handled_by_id])


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(db.String(50), index=True)
    target_type: Mapped[str] = mapped_column(db.String(30))
    target_id: Mapped[int | None] = mapped_column()
    detail: Mapped[str] = mapped_column(db.String(500), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    actor: Mapped[User | None] = relationship()
