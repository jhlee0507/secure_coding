from app.extensions import db
from app.models import Product, Report, Transfer, User


def test_atomic_transfer_updates_balances(client, app, make_user, login):
    alice_id = make_user("alice", balance=50_000)
    bob_id = make_user("bob", balance=10_000)
    login("alice")
    response = client.post(
        "/wallet/transfer",
        data={"receiver": "bob", "amount": "15000", "password": "Valid!Pass1"},
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(User, alice_id).balance == 35_000
        assert db.session.get(User, bob_id).balance == 25_000
        transfer = db.session.scalar(db.select(Transfer))
        assert transfer.amount == 15_000


def test_negative_and_self_transfer_are_rejected(client, app, make_user, login):
    alice_id = make_user("alice", balance=50_000)
    login("alice")
    client.post(
        "/wallet/transfer",
        data={"receiver": "alice", "amount": "-100", "password": "Valid!Pass1"},
    )
    response = client.post(
        "/wallet/transfer",
        data={"receiver": "alice", "amount": "100", "password": "Valid!Pass1"},
    )
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(User, alice_id).balance == 50_000
        assert db.session.scalar(db.select(db.func.count()).select_from(Transfer)) == 0


def test_admin_can_ban_reported_user(client, app, make_user, login):
    admin_id = make_user("admin", is_admin=True)
    reporter_id = make_user("reporter")
    target_id = make_user("target")
    with app.app_context():
        db.session.add(Report(reporter_id=reporter_id, target_type="user", target_id=target_id, reason="반복적으로 사기 메시지를 보냈습니다"))
        db.session.commit()
        report_id = db.session.scalar(db.select(Report.id))
    login("admin")
    response = client.post(f"/admin/reports/{report_id}/handle", data={"action": "resolve"})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(User, target_id).is_banned is True
        assert db.session.get(Report, report_id).status == "resolved"


def test_non_admin_cannot_access_admin(client, make_user, login):
    make_user("alice")
    login("alice")
    assert client.get("/admin").status_code == 403


def test_admin_dashboard_renders_all_management_sections(client, make_user, login):
    make_user("admin", is_admin=True)
    make_user("alice")
    login("admin")
    response = client.get("/admin")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "사용자 관리" in page
    assert "상품 관리" in page
    assert "신고 관리" in page
    assert "감사 로그" in page


def test_report_product_and_admin_resolution(client, app, make_user, login):
    seller_id = make_user("seller")
    make_user("reporter")
    make_user("admin", is_admin=True)
    with app.app_context():
        product = Product(title="의심 상품", description="신고 대상 상품 설명", price=9999, seller_id=seller_id)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    login("reporter")
    response = client.post(
        "/reports/new",
        data={"target_type": "product", "target_id": product_id, "reason": "허위 판매가 의심되는 상품입니다"},
    )
    assert response.status_code == 302
    client.post("/auth/logout")
    login("admin")
    with app.app_context():
        report_id = db.session.scalar(db.select(Report.id))
    assert client.post(
        f"/admin/reports/{report_id}/handle", data={"action": "resolve"}
    ).status_code == 302
    with app.app_context():
        assert db.session.get(Product, product_id).is_hidden is True


def test_duplicate_pending_report_is_rejected(client, app, make_user, login):
    target_id = make_user("target")
    make_user("reporter")
    login("reporter")
    data = {"target_type": "user", "target_id": target_id, "reason": "반복적으로 부적절한 메시지를 보냅니다"}
    assert client.post("/reports/new", data=data).status_code == 302
    response = client.post("/reports/new", data=data)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Report)) == 1


def test_wrong_password_and_insufficient_balance_do_not_transfer(client, app, make_user, login):
    alice_id = make_user("alice", balance=100)
    make_user("bob", balance=0)
    login("alice")
    for amount, password in ((50, "wrong"), (101, "Valid!Pass1")):
        assert client.post(
            "/wallet/transfer", data={"receiver": "bob", "amount": amount, "password": password}
        ).status_code == 302
    with app.app_context():
        assert db.session.get(User, alice_id).balance == 100
        assert db.session.scalar(db.select(db.func.count()).select_from(Transfer)) == 0
