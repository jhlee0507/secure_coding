from flask import Blueprint, g, render_template

from .extensions import db
from .models import Product
from .security import login_required


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    products = db.session.scalars(
        db.select(Product)
        .where(Product.is_hidden.is_(False), Product.is_sold.is_(False))
        .order_by(Product.created_at.desc())
        .limit(8)
    ).all()
    return render_template("index.html", products=products)


@bp.get("/dashboard")
@login_required
def dashboard():
    products = db.session.scalars(
        db.select(Product)
        .where(Product.is_hidden.is_(False), Product.is_sold.is_(False))
        .order_by(Product.created_at.desc())
        .limit(8)
    ).all()
    own_products = db.session.scalars(
        db.select(Product)
        .where(Product.seller_id == g.user.id)
        .order_by(Product.created_at.desc())
        .limit(5)
    ).all()
    return render_template("dashboard.html", products=products, own_products=own_products)

