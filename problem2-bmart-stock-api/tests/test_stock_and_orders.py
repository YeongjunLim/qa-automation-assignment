"""
정상 케이스 / 재고 복구 / 품절 전환 API 자동화 테스트 (TC-01~TC-18)

함수명은 `test_tc{번호}_{짧은 요약}` 규칙을 따른다. 각 함수 docstring에 TC-ID·카테고리·적용기법과
Given/When/Then을 명시하고, 본문에도 동일한 흐름을 주석으로 표시했다. 기법/근거 상세는
../TEST_DESIGN.md, 입력값·예상결과 표는 ../TEST_CASES.md 참고.
"""
from __future__ import annotations

import requests

from conftest import assert_error, assert_stock


def test_tc01_get_current_stock(server):
    """
    TC-01 | 정상 | 동등분할(유효 productId)
    Given: 재고 10개인 상품이 있다
    When:  재고를 조회하면
    Then:  200과 함께 현재 재고·IN_STOCK 상태가 반환된다
    """
    # Given: server fixture가 chicken-fried-001(재고 10)을 준비해준다

    # When
    resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))

    # Then
    assert resp.status_code == 200
    assert_stock(resp, expected_stock=10, expected_status="IN_STOCK")


def test_tc02_repeated_read_has_no_side_effect(server):
    """
    TC-02 | 정상
    Given: 재고 3개인 상품이 있다
    When:  같은 상품을 5번 반복 조회하면 (장바구니 담기는 '조회'일 뿐)
    Then:  매번 재고가 그대로 3개다 (조회는 재고를 변화시키지 않는다)
    """
    # Given: server fixture가 snack-honeybutter-002(재고 3)을 준비해준다

    # When / Then: 조회를 반복하며 매번 즉시 검증
    for _ in range(5):
        resp = requests.get(server.url("/v1/products/snack-honeybutter-002/stock"))
        assert_stock(resp, expected_stock=3)


def test_tc03_order_decrements_stock(server):
    """
    TC-03 | 정상 | 경계값(하한 바로 위, quantity=1)
    Given: 재고 10개인 상품이 있다
    When:  수량 1개로 주문하면
    Then:  주문이 성공(COMPLETED)하고 재고가 9개로 줄어든다
    """
    # Given: server fixture가 chicken-fried-001(재고 10)을 준비해준다

    # When
    resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 1})

    # Then
    assert resp.status_code == 201
    order = resp.json()
    assert order["status"] == "COMPLETED"
    assert order["productId"] == "chicken-fried-001"
    assert "orderId" in order and order["orderId"]

    stock_resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))
    assert_stock(stock_resp, expected_stock=9, expected_status="IN_STOCK")


def test_tc04_order_multiple_quantity(server):
    """
    TC-04 | 정상 | 경계값(N-1, 상한 미만)
    Given: 재고 3개인 상품이 있다
    When:  수량 2개로 주문하면
    Then:  주문이 성공하고 재고가 1개(여유) 남는다
    """
    # Given: server fixture가 snack-honeybutter-002(재고 3)을 준비해준다

    # When
    resp = requests.post(server.url("/v1/orders"), json={"productId": "snack-honeybutter-002", "quantity": 2})

    # Then
    assert resp.status_code == 201
    stock_resp = requests.get(server.url("/v1/products/snack-honeybutter-002/stock"))
    assert_stock(stock_resp, expected_stock=1, expected_status="IN_STOCK")


def test_tc05_cancel_restores_stock(server):
    """
    TC-05 | 재고복구 | 상태전이 + 동등분할(유효 orderId)
    Given: 재고 10개인 상품에 2개짜리 주문을 완료해뒀다
    When:  그 주문을 취소하면
    Then:  주문 상태는 CANCELLED, 재고는 10개로 원복된다
    """
    # Given
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 2})
    order_id = order_resp.json()["orderId"]

    # When
    cancel_resp = requests.post(server.url(f"/v1/orders/{order_id}/cancel"))

    # Then
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
    stock_resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))
    assert_stock(stock_resp, expected_stock=10, expected_status="IN_STOCK")


def test_tc06_cancel_then_other_customer_can_repurchase(last_unit_server):
    """
    TC-06 | 재고복구 | 상태전이(SOLD_OUT -> IN_STOCK)
    Given: 재고 1개인 상품을 고객 A가 구매해 품절(SOLD_OUT)됐다
    When:  고객 A가 주문을 취소한 뒤, 고객 B가 같은 상품을 주문하면
    Then:  고객 B의 주문이 성공한다 (취소 직후 즉시 구매 가능해야 한다는 비고 요건)
    """
    server = last_unit_server

    # Given
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})
    order_id = order_resp.json()["orderId"]
    assert requests.get(server.url("/v1/products/limited-edition-999/stock")).json()["status"] == "SOLD_OUT"

    # When
    requests.post(server.url(f"/v1/orders/{order_id}/cancel"))
    other_customer_order = requests.post(
        server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1}
    )

    # Then
    assert other_customer_order.status_code == 201


def test_tc07_stock_zero_becomes_soldout(last_unit_server):
    """
    TC-07 | 품절전환 | 상태전이 + 경계값(N, 정확히 소진)
    Given: 재고 1개인 상품이 있다
    When:  수량 1개로 주문해 정확히 소진시키면
    Then:  재고 0, 상태가 SOLD_OUT으로 전환된다
    """
    server = last_unit_server

    # When
    requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})

    # Then
    stock_resp = requests.get(server.url("/v1/products/limited-edition-999/stock"))
    assert_stock(stock_resp, expected_stock=0, expected_status="SOLD_OUT")


def test_tc08_order_on_soldout_is_rejected(last_unit_server):
    """
    TC-08 | 품절전환 | 상태전이(불허 전이)
    Given: 재고 1개인 상품을 이미 다 팔아 SOLD_OUT 상태다
    When:  같은 상품을 또 주문하면
    Then:  409 SOLD_OUT으로 거부된다 (상태는 그대로 유지)
    """
    server = last_unit_server

    # Given
    requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})

    # When
    second_attempt = requests.post(
        server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1}
    )

    # Then
    assert_error(second_attempt, expected_http_status=409, expected_error_code="SOLD_OUT")


def test_tc09_order_far_exceeds_stock_rejected(server):
    """
    TC-09 | 품절전환 | 경계값(N+100, 상한 훨씬 초과)
    Given: 재고 3개인 상품이 있다
    When:  수량 100개(극단적으로 재고를 초과)로 주문하면
    Then:  409 SOLD_OUT으로 거부된다
    """
    # When
    resp = requests.post(server.url("/v1/orders"), json={"productId": "snack-honeybutter-002", "quantity": 100})

    # Then
    assert_error(resp, expected_http_status=409, expected_error_code="SOLD_OUT")


def test_tc10_admin_updates_stock(server):
    """
    TC-10 | 정상
    Given: 재고 10개인 상품이 있다
    When:  운영자가 재고를 50개로 수동 수정하면
    Then:  즉시 50개로 반영된다
    """
    # When
    resp = requests.patch(server.url("/v1/admin/products/chicken-fried-001/stock"), json={"stock": 50})

    # Then
    assert resp.status_code == 200
    assert_stock(resp, expected_stock=50, expected_status="IN_STOCK")
    stock_resp = requests.get(server.url("/v1/products/chicken-fried-001/stock"))
    assert_stock(stock_resp, expected_stock=50)


def test_tc11_order_zero_quantity_rejected(server):
    """
    TC-11 | 예외처리 | 경계값(하한 경계값, quantity=0)
    Given: 재고가 충분한 상품이 있다
    When:  수량 0으로 주문하면
    Then:  400 INVALID_QUANTITY로 거부된다
    """
    # When
    resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 0})

    # Then
    assert_error(resp, expected_http_status=400, expected_error_code="INVALID_QUANTITY")


def test_tc12_unknown_product_stock_404(server):
    """
    TC-12 | 예외처리 | 동등분할(무효 productId)
    Given: 존재하지 않는 productId다
    When:  그 재고를 조회하면
    Then:  404 PRODUCT_NOT_FOUND가 반환된다
    """
    # When
    resp = requests.get(server.url("/v1/products/no-such-product/stock"))

    # Then
    assert_error(resp, expected_http_status=404, expected_error_code="PRODUCT_NOT_FOUND")


def test_tc13_order_unknown_product_404(server):
    """
    TC-13 | 예외처리 | 동등분할(무효 productId)
    Given: 존재하지 않는 productId다
    When:  그 상품으로 주문을 시도하면
    Then:  404 PRODUCT_NOT_FOUND가 반환된다
    """
    # When
    resp = requests.post(server.url("/v1/orders"), json={"productId": "no-such-product", "quantity": 1})

    # Then
    assert_error(resp, expected_http_status=404, expected_error_code="PRODUCT_NOT_FOUND")


def test_tc14_cancel_twice_rejected(server):
    """
    TC-14 | 예외처리 | 상태전이(불허) + 동등분할(무효② 이미 취소된 주문)
    Given: 이미 취소된 주문이 하나 있다
    When:  같은 주문을 다시 취소하면
    Then:  409 ALREADY_CANCELLED로 거부된다 (재고 중복 복구 방지)
    """
    # Given
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": 1})
    order_id = order_resp.json()["orderId"]
    requests.post(server.url(f"/v1/orders/{order_id}/cancel"))

    # When
    second_cancel = requests.post(server.url(f"/v1/orders/{order_id}/cancel"))

    # Then
    assert_error(second_cancel, expected_http_status=409, expected_error_code="ALREADY_CANCELLED")


def test_tc15_cancel_unknown_order_404(server):
    """
    TC-15 | 예외처리 | 동등분할(무효① 존재하지 않는 orderId)
    Given: 존재하지 않는 orderId다
    When:  그 주문을 취소하면
    Then:  404 ORDER_NOT_FOUND가 반환된다
    """
    # When
    resp = requests.post(server.url("/v1/orders/order-does-not-exist/cancel"))

    # Then
    assert_error(resp, expected_http_status=404, expected_error_code="ORDER_NOT_FOUND")


def test_tc16_order_negative_quantity_rejected(server):
    """
    TC-16 | 예외처리 | 경계값(하한 미만, quantity=-1)
    Given: 재고가 충분한 상품이 있다
    When:  수량 -1로 주문하면
    Then:  400 INVALID_QUANTITY로 거부된다
    """
    # When
    resp = requests.post(server.url("/v1/orders"), json={"productId": "chicken-fried-001", "quantity": -1})

    # Then
    assert_error(resp, expected_http_status=400, expected_error_code="INVALID_QUANTITY")


def test_tc17_order_one_over_stock_rejected(server):
    """
    TC-17 | 품절전환 | 경계값(N+1, 상한 바로 초과)
    Given: 재고 3개인 상품이 있다
    When:  경계 바로 위인 수량 4개로 주문하면
    Then:  409 SOLD_OUT으로 거부되고, 재고는 변하지 않는다
    """
    # Given: snack-honeybutter-002 재고 3

    # When
    resp = requests.post(server.url("/v1/orders"), json={"productId": "snack-honeybutter-002", "quantity": 4})

    # Then
    assert_error(resp, expected_http_status=409, expected_error_code="SOLD_OUT")
    stock_resp = requests.get(server.url("/v1/products/snack-honeybutter-002/stock"))
    assert_stock(stock_resp, expected_stock=3)


def test_tc18_admin_restocks_soldout_product(last_unit_server):
    """
    TC-18 | 재고복구 | 상태전이(SOLD_OUT -> IN_STOCK, 운영자 수동 수정)
    Given: 재고 1개인 상품이 판매되어 SOLD_OUT 상태다
    When:  운영자가 재고를 5개로 수동 수정하면
    Then:  IN_STOCK으로 전환되고, 다른 고객이 즉시 구매 가능하다
    """
    server = last_unit_server

    # Given
    requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})
    assert requests.get(server.url("/v1/products/limited-edition-999/stock")).json()["status"] == "SOLD_OUT"

    # When
    restock_resp = requests.patch(server.url("/v1/admin/products/limited-edition-999/stock"), json={"stock": 5})

    # Then
    assert_stock(restock_resp, expected_stock=5, expected_status="IN_STOCK")
    new_order = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})
    assert new_order.status_code == 201
