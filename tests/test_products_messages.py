from app.extensions import db
from app.models import Message, Product


def test_product_create_and_search(client, app, make_user, login):
    make_user("alice")
    login("alice")
    response = client.post(
        "/products/new",
        data={"title": "안전한 키보드", "description": "상태가 매우 좋은 키보드입니다", "price": "25000"},
    )
    assert response.status_code == 302
    response = client.get("/products?q=키보드")
    assert "안전한 키보드" in response.get_data(as_text=True)
    with app.app_context():
        product = db.session.scalar(db.select(Product))
        assert product.seller.username == "alice"


def test_non_owner_cannot_edit_product(client, app, make_user, login):
    alice_id = make_user("alice")
    make_user("bob")
    with app.app_context():
        product = Product(title="상품", description="충분히 긴 상품 설명", price=1000, seller_id=alice_id)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    login("bob")
    response = client.post(
        f"/products/{product_id}/edit",
        data={"title": "탈취", "description": "수정하면 안 되는 설명", "price": "1"},
    )
    assert response.status_code == 403


def test_hidden_products_are_not_searchable(client, app, make_user):
    alice_id = make_user("alice")
    with app.app_context():
        db.session.add(Product(title="비밀 상품", description="검색되면 안 됩니다", price=1000, seller_id=alice_id, is_hidden=True))
        db.session.commit()
    response = client.get("/products?q=비밀")
    assert "비밀 상품" not in response.get_data(as_text=True)


def test_message_sender_comes_from_session(client, app, make_user, login):
    alice_id = make_user("alice")
    bob_id = make_user("bob")
    login("alice")
    response = client.post(f"/messages/{bob_id}", data={"body": "안녕하세요"})
    assert response.status_code == 302
    with app.app_context():
        message = db.session.scalar(db.select(Message))
        assert message.sender_id == alice_id
        assert message.recipient_id == bob_id


def test_cannot_message_self(client, make_user, login):
    alice_id = make_user("alice")
    login("alice")
    assert client.post(f"/messages/{alice_id}", data={"body": "self"}).status_code == 400


def test_authenticated_pages_render(client, make_user, login):
    make_user("alice")
    make_user("bob")
    login("alice")
    for path in ("/dashboard", "/messages", "/wallet", "/auth/profile"):
        response = client.get(path)
        assert response.status_code == 200, path


def test_owner_can_edit_sell_and_hide_product(client, app, make_user, login):
    alice_id = make_user("alice")
    with app.app_context():
        product = Product(title="원래 상품", description="수정 전 상품 설명입니다", price=1000, seller_id=alice_id)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    login("alice")
    assert client.post(
        f"/products/{product_id}/edit",
        data={"title": "수정 상품", "description": "수정한 상품 설명입니다", "price": "2000"},
    ).status_code == 302
    assert client.post(f"/products/{product_id}/toggle-sold").status_code == 302
    assert client.post(f"/products/{product_id}/delete").status_code == 302
    with app.app_context():
        product = db.session.get(Product, product_id)
        assert (product.title, product.price, product.is_sold, product.is_hidden) == (
            "수정 상품", 2000, True, True
        )


def test_user_content_is_html_escaped(client, app, make_user):
    alice_id = make_user("alice")
    with app.app_context():
        product = Product(
            title="<script>alert(1)</script>",
            description="충분히 긴 상품 설명입니다",
            price=1000,
            seller_id=alice_id,
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    page = client.get(f"/products/{product_id}").get_data(as_text=True)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)</script>" not in page


def test_message_updates_only_return_current_conversation(
    client, app, make_user, login
):
    alice_id = make_user("alice")
    bob_id = make_user("bob")
    charlie_id = make_user("charlie")
    with app.app_context():
        db.session.add_all(
            [
                Message(
                    sender_id=bob_id,
                    recipient_id=alice_id,
                    body="<script>안전하게 표시</script>",
                ),
                Message(
                    sender_id=bob_id,
                    recipient_id=charlie_id,
                    body="다른 사람의 비공개 메시지",
                ),
            ]
        )
        db.session.commit()
    login("alice")
    response = client.get(f"/messages/{bob_id}/updates?after=0")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["body"] == "<script>안전하게 표시</script>"
    assert payload["messages"][0]["is_mine"] is False
    assert "다른 사람의 비공개 메시지" not in response.get_data(as_text=True)


def test_message_updates_validate_cursor(client, make_user, login):
    make_user("alice")
    bob_id = make_user("bob")
    login("alice")
    assert client.get(f"/messages/{bob_id}/updates?after=-1").status_code == 400
    assert client.get(f"/messages/{bob_id}/updates?after=invalid").status_code == 400
