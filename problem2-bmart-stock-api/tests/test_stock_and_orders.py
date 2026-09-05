"""
정상 케이스 / 재고 복구 / 품절 전환 API 자동화 테스트

각 테스트 함수 위 주석의 TC-XX는 테스트케이스 ID다. 어떤 설계기법(상태전이/경계값분석/동등분할)으로
도출됐는지는 ../TEST_DESIGN.md, 입력값·예상결과 상세 명세는 ../TEST_CASES.md 참고.
"""
from __future__ import annotations

import requests

from conftest import assert_error, assert_stock


# TC-01
def test_get_stock_returns_current_quantity(server):
    resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))
    assert resp.status_code == 200
    assert_stock(resp, expected_stock=10, expected_status="IN_STOCK")


# TC-02
def test_reading_stock_repeatedly_has_no_side_effect(server):
    """장바구니 담기는 '조회'일 뿐이므로, 여러 번 조회해도 재고는 변하지 않아야 한다."""
    for _ in range(5):
        resp = requests.get(server.url("/v1/products/snack-honeybutter-002/stock"))
        assert_stock(resp, expected_stock=3)


# TC-03
def test_successful_order_decrements_stock_and_returns_order(server):
    resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 1})
    assert resp.status_code == 201
    order = resp.json()
    assert order["status"] == "COMPLETED"
    assert order["productId"] == "chicken-fried-001"
    assert "orderId" in order and order["orderId"]

    stock_resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))
    assert_stock(stock_resp, expected_stock=9, expected_status="IN_STOCK")


# TC-04
def test_order_with_quantity_greater_than_one(server):
    resp = requests.post(server.url("/v1/orders"), json={"productId": "snack-honeybutter-002", "quantity": 2})
    assert resp.status_code == 201

    stock_resp = requests.get(server.url("/v1/products/snack-honeybutter-002/stock"))
    assert_stock(stock_resp, expected_stock=1, expected_status="IN_STOCK")


# TC-05
def test_cancel_order_restores_stock(server):
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 2})
    order_id = order_resp.json()["orderId"]

    cancel_resp = requests.post(server.url(f"/v1/orders/{order_id}/cancel"))
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    stock_resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))
    assert_stock(stock_resp, expected_stock=10, expected_status="IN_STOCK")  # 원복


# TC-06
def test_after_cancel_another_customer_can_purchase_immediately(last_unit_server):
    """취소 직후 '다른 고객'이 즉시 구매 가능한 상태로 전환되어야 한다는 비고 요건 검증."""
    server = last_unit_server
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})
    order_id = order_resp.json()["orderId"]
    assert requests.get(server.url("/v1/products/limited-edition-999/stock")).json()["status"] == "SOLD_OUT"

    requests.post(server.url(f"/v1/orders/{order_id}/cancel"))

    # 다른 고객(B)의 신규 주문 시도
    other_customer_order = requests.post(
        server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1}
    )
    assert other_customer_order.status_code == 201


# TC-07
def test_stock_reaches_zero_becomes_sold_out(last_unit_server):
    server = last_unit_server
    requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})

    stock_resp = requests.get(server.url("/v1/products/limited-edition-999/stock"))
    assert_stock(stock_resp, expected_stock=0, expected_status="SOLD_OUT")


# TC-08
def test_ordering_sold_out_product_returns_409(last_unit_server):
    server = last_unit_server
    requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})

    second_attempt = requests.post(
        server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1}
    )
    assert_error(second_attempt, expected_http_status=409, expected_error_code="SOLD_OUT")


# TC-09
def test_order_quantity_exceeds_stock_returns_409(server):
    resp = requests.post(server.url("/v1/orders"), json={"productId": "snack-honeybutter-002", "quantity": 100})
    assert_error(resp, expected_http_status=409, expected_error_code="SOLD_OUT")


# TC-10
def test_admin_can_manually_update_stock(server):
    resp = requests.patch(server.url("/v1/admin/products/chicken-fried-001/stock"), json={"stock": 50})
    assert resp.status_code == 200
    assert_stock(resp, expected_stock=50, expected_status="IN_STOCK")

    stock_resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))
    assert_stock(stock_resp, expected_stock=50)


# TC-11
def test_order_with_invalid_quantity_returns_400(server):
    resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 0})
    assert_error(resp, expected_http_status=400, expected_error_code="INVALID_QUANTITY")


# TC-12
def test_get_stock_for_unknown_product_returns_404(server):
    resp = requests.get(server.url("/v1/products/no-such-product/stock"))
    assert_error(resp, expected_http_status=404, expected_error_code="PRODUCT_NOT_FOUND")


# TC-13
def test_order_for_unknown_product_returns_404(server):
    resp = requests.post(server.url("/v1/orders"), json={"productId": "no-such-product", "quantity": 1})
    assert_error(resp, expected_http_status=404, expected_error_code="PRODUCT_NOT_FOUND")


# TC-14
def test_cancelling_already_cancelled_order_returns_409(server):
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 1})
    order_id = order_resp.json()["orderId"]
    requests.post(server.url(f"/v1/orders/{order_id}/cancel"))

    second_cancel = requests.post(server.url(f"/v1/orders/{order_id}/cancel"))
    assert_error(second_cancel, expected_http_status=409, expected_error_code="ALREADY_CANCELLED")


# TC-15
def test_cancelling_unknown_order_returns_404(server):
    resp = requests.post(server.url("/v1/orders/order-does-not-exist/cancel"))
    assert_error(resp, expected_http_status=404, expected_error_code="ORDER_NOT_FOUND")


# TC-16 (경계값 분석: quantity 하한 미만)
def test_order_with_negative_quantity_returns_400(server):
    resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": -1})
    assert_error(resp, expected_http_status=400, expected_error_code="INVALID_QUANTITY")


# TC-17 (경계값 분석: quantity = stock+1, 상한 바로 초과)
def test_order_with_quantity_exactly_one_more_than_stock_returns_409(server):
    # snack-honeybutter-002 재고 3 -> 정확히 경계 바로 위인 4개를 주문
    resp = requests.post(server.url("/v1/orders"), json={"productId": "snack-honeybutter-002", "quantity": 4})
    assert_error(resp, expected_http_status=409, expected_error_code="SOLD_OUT")

    # 경계를 넘지 않았으므로 재고 자체는 변하지 않아야 함
    stock_resp = requests.get(server.url("/v1/products/snack-honeybutter-002/stock"))
    assert_stock(stock_resp, expected_stock=3)


# TC-18 (상태 전이: SOLD_OUT -> IN_STOCK, 운영자 수동 수정으로 복구)
def test_admin_restock_sold_out_product_makes_it_available_again(last_unit_server):
    server = last_unit_server
    requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})
    assert requests.get(server.url("/v1/products/limited-edition-999/stock")).json()["status"] == "SOLD_OUT"

    restock_resp = requests.patch(server.url("/v1/admin/products/limited-edition-999/stock"), json={"stock": 5})
    assert_stock(restock_resp, expected_stock=5, expected_status="IN_STOCK")

    # 재입고 후 다른 고객이 즉시 구매 가능해야 함
    new_order = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})
    assert new_order.status_code == 201
