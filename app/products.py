from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import or_

from .audit import record
from .extensions import db, limiter
from .models import Product
from .security import clean_text, login_required


bp = Blueprint("products", __name__, url_prefix="/products")


def _product_or_404(product_id: int, include_hidden: bool = False) -> Product:
    product = db.session.get(Product, product_id)
    if product is None or (product.is_hidden and not include_hidden):
        abort(404)
    return product


def _parse_product_form():
    title = clean_text(request.form.get("title", ""), minimum=2, maximum=100)
    description = clean_text(request.form.get("description", ""), minimum=5, maximum=2000)
    try:
        price = int(request.form.get("price", ""))
    except ValueError:
        price = 0
    if title is None or description is None or not 1 <= price <= 1_000_000_000:
        return None
    return title, description, price


@bp.get("")
def list_products():
    query = clean_text(request.args.get("q", ""), minimum=0, maximum=100)
    if query is None:
        abort(400)
    statement = db.select(Product).where(
        Product.is_hidden.is_(False), Product.is_sold.is_(False)
    )
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(Product.title.ilike(pattern), Product.description.ilike(pattern))
        )
    products = db.session.scalars(statement.order_by(Product.created_at.desc())).all()
    return render_template("products/list.html", products=products, query=query)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per hour", methods=["POST"])
def create():
    if request.method == "POST":
        values = _parse_product_form()
        if values is None:
            flash("상품명·설명·가격을 올바르게 입력하세요.", "error")
        else:
            product = Product(title=values[0], description=values[1], price=values[2], seller=g.user)
            db.session.add(product)
            db.session.flush()
            record("product_create", "product", product.id)
            db.session.commit()
            flash("상품을 등록했습니다.", "success")
            return redirect(url_for("products.detail", product_id=product.id))
    return render_template("products/form.html", product=None)


@bp.get("/<int:product_id>")
def detail(product_id: int):
    product = _product_or_404(product_id)
    return render_template("products/detail.html", product=product)


@bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit(product_id: int):
    product = _product_or_404(product_id, include_hidden=True)
    if product.seller_id != g.user.id:
        abort(403)
    if request.method == "POST":
        values = _parse_product_form()
        if values is None:
            flash("상품명·설명·가격을 올바르게 입력하세요.", "error")
        else:
            product.title, product.description, product.price = values
            record("product_update", "product", product.id)
            db.session.commit()
            flash("상품을 수정했습니다.", "success")
            return redirect(url_for("products.detail", product_id=product.id))
    return render_template("products/form.html", product=product)


@bp.post("/<int:product_id>/toggle-sold")
@login_required
def toggle_sold(product_id: int):
    product = _product_or_404(product_id, include_hidden=True)
    if product.seller_id != g.user.id:
        abort(403)
    product.is_sold = not product.is_sold
    record("product_toggle_sold", "product", product.id, str(product.is_sold))
    db.session.commit()
    flash("판매 상태를 변경했습니다.", "success")
    return redirect(url_for("main.dashboard"))


@bp.post("/<int:product_id>/delete")
@login_required
def delete(product_id: int):
    product = _product_or_404(product_id, include_hidden=True)
    if product.seller_id != g.user.id:
        abort(403)
    product.is_hidden = True
    record("product_owner_hide", "product", product.id)
    db.session.commit()
    flash("상품을 비공개 처리했습니다.", "success")
    return redirect(url_for("main.dashboard"))

