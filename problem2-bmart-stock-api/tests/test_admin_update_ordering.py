"""
결정 테이블(Decision Table) 기반 테스트 (TC-19~TC-22) — 운영자 재고 수동 수정과 주문 처리 순서

'재고 처리 규칙' 표의 비고: "수정 중 주문 발생 시 처리 순서 정의 필요"를 다룬다.
조건 2개(처리 순서 / 그 시점 재고가 주문 수량 이상인지)의 조합 4가지(R1~R4)를 검증한다.
설계 근거와 규칙표는 ../TEST_DESIGN.md의 "4. 결정 테이블" 섹션, 입력값 상세는 ../TEST_CASES.md 참고.

이 파일의 테스트는 "처리 순서가 이미 정해졌을 때 규칙대로 결과가 나오는가"를 검증하는 것이므로
API를 순차 호출하는 것만으로 충분하다. "실제로 동시에 요청이 왔을 때도 이 규칙대로 흘러가는가"는
test_concurrency.py가 별도로 검증한다.
"""
from __future__ import annotations

import requests

from conftest import assert_error, assert_stock


def test_tc19_admin_restock_then_order_succeeds(make_server_with):
    """
    TC-19 | 정상 | 결정테이블 R1(운영자 수정 -> 주문, 재고 충분)
    Given: 재고 0인 상품이 있다
    When:  운영자가 재고를 5개로 수정한 뒤, 3개를 주문하면
    Then:  주문이 성공하고 최종 재고는 2개(수정값 5 - 주문량 3)다
    """
    # Given
    server = make_server_with({"limited-edition-999": {"name": "한정판 치킨", "stock": 0}})

    # When
    restock_resp = requests.patch(server.url("/v1/admin/products/limited-edition-999/stock"), json={"stock": 5})
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 3})

    # Then
    assert_stock(restock_resp, expected_stock=5, expected_status="IN_STOCK")
    assert order_resp.status_code == 201
    final_stock = requests.get(server.url("/v1/products/limited-edition-999/stock"))
    assert_stock(final_stock, expected_stock=2, expected_status="IN_STOCK")


def test_tc20_admin_low_stock_then_order_rejected(make_server_with):
    """
    TC-20 | 품절전환 | 결정테이블 R2(운영자 수정 -> 주문, 재고 부족)
    Given: 재고 10인 상품이 있다
    When:  운영자가 재고를 1개로 줄인 뒤, 3개를 주문하면
    Then:  409 SOLD_OUT으로 거부되고 재고는 수정값(1) 그대로다
    """
    # Given
    server = make_server_with({"limited-edition-999": {"name": "한정판 치킨", "stock": 10}})

    # When
    restock_resp = requests.patch(server.url("/v1/admin/products/limited-edition-999/stock"), json={"stock": 1})
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 3})

    # Then
    assert_stock(restock_resp, expected_stock=1, expected_status="IN_STOCK")
    assert_error(order_resp, expected_http_status=409, expected_error_code="SOLD_OUT")
    final_stock = requests.get(server.url("/v1/products/limited-edition-999/stock"))
    assert_stock(final_stock, expected_stock=1)


def test_tc21_order_then_admin_overwrites_stock(make_server_with):
    """
    TC-21 | 결정테이블 R3(주문 -> 운영자 수정, 주문 성공)
    Given: 재고 5인 상품이 있다
    When:  2개를 주문해 성공시킨 뒤, 운영자가 재고를 100으로 수정하면
    Then:  주문 결과(재고 3)와 무관하게 최종 재고는 운영자 지정값(100)이 된다
    """
    # Given
    server = make_server_with({"limited-edition-999": {"name": "한정판 치킨", "stock": 5}})

    # When
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 2})
    assert order_resp.status_code == 201
    assert_stock(requests.get(server.url("/v1/products/limited-edition-999/stock")), expected_stock=3)
    restock_resp = requests.patch(server.url("/v1/admin/products/limited-edition-999/stock"), json={"stock": 100})

    # Then
    assert_stock(restock_resp, expected_stock=100, expected_status="IN_STOCK")
    final_stock = requests.get(server.url("/v1/products/limited-edition-999/stock"))
    assert_stock(final_stock, expected_stock=100)


def test_tc22_failed_order_then_admin_sets_stock(make_server_with):
    """
    TC-22 | 결정테이블 R4(주문 -> 운영자 수정, 주문 실패)
    Given: 재고 1인 상품이 있다
    When:  5개를 주문해 품절로 실패시킨 뒤, 운영자가 재고를 20으로 수정하면
    Then:  최종 재고는 운영자 지정값(20)이 된다
    """
    # Given
    server = make_server_with({"limited-edition-999": {"name": "한정판 치킨", "stock": 1}})

    # When
    order_resp = requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 5})
    assert_error(order_resp, expected_http_status=409, expected_error_code="SOLD_OUT")
    assert_stock(requests.get(server.url("/v1/products/limited-edition-999/stock")), expected_stock=1)  # 변화 없음
    restock_resp = requests.patch(server.url("/v1/admin/products/limited-edition-999/stock"), json={"stock": 20})

    # Then
    assert_stock(restock_resp, expected_stock=20, expected_status="IN_STOCK")
    final_stock = requests.get(server.url("/v1/products/limited-edition-999/stock"))
    assert_stock(final_stock, expected_stock=20)
