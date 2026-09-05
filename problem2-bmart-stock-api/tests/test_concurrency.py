"""
동시성 테스트 — '재고 1개 남은 상품에 두 요청이 수십 ms 간격으로 도달' 시나리오

설계 의도
    1. test_two_near_simultaneous_orders_on_last_unit_*
       threading.Barrier로 두 스레드를 동시에 출발시켜, 실제 두 고객(A, B)이 각자의 클라이언트에서
       "거의 동시에" 결제 버튼을 누른 상황을 재현한다. 두 요청이 서버에 도달하는 실제 시간 간격을
       측정해 로그로 남기되(수십 ms 수준이 되는지는 OS 스케줄링에 달려 있어 하드 어서션은 하지 않는다 —
       타이밍을 하드 어서션하면 그 자체가 flaky의 원인이 되기 때문), 도달 순서와 무관하게
       "정확히 1건 성공 + 나머지는 품절"이라는 비즈니스 불변식(invariant)만 엄격히 검증한다.

    2. test_lock_serializes_requests_even_under_artificial_delay
       Barrier만으로는 두 요청이 서버의 critical section 안에서 실제로 겹치는지 보장할 수 없다
       (스케줄링이 빨라 겹치지 않고 순차 처리될 수도 있음). 그래서 mock_server의 디버그 훅
       (_artificialDelaySeconds)으로 lock 내부에서 일부러 sleep을 주입해, 두 요청이 반드시
       critical section 안에서 경합하도록 강제한 뒤에도 정합성이 깨지지 않는지 검증한다.
       => (1)이 '현실적 타이밍 재현', (2)가 '락 정합성의 결정적 증명' 역할을 분담한다.

    3. test_no_oversell_under_high_concurrency
       요청 2건이 아니라 10건을 동시에 쏘아도 정확히 1건만 성공하는지 확인해, 동시성 정도가
       늘어나도 이중 판매(oversell)가 발생하지 않음을 추가로 보증한다.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests


def _fire_order_with_barrier(base_url: str, barrier: threading.Barrier, product_id: str) -> tuple[float, requests.Response]:
    barrier.wait()  # 모든 스레드가 여기 도달할 때까지 대기했다가 동시에 출발
    sent_at = time.perf_counter()
    resp = requests.post(f"{base_url}/v1/orders", json={"productId": product_id, "quantity": 1})
    return sent_at, resp


def test_two_near_simultaneous_orders_on_last_unit_only_one_succeeds(last_unit_server):
    server = last_unit_server
    barrier = threading.Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(_fire_order_with_barrier, server.base_url, barrier, "limited-edition-999")
        future_b = pool.submit(_fire_order_with_barrier, server.base_url, barrier, "limited-edition-999")
        sent_at_a, resp_a = future_a.result()
        sent_at_b, resp_b = future_b.result()

    gap_ms = abs(sent_at_a - sent_at_b) * 1000
    print(f"[timing] 두 요청 발사 간격: {gap_ms:.2f} ms")  # pytest -s 로 확인 가능

    statuses = sorted([resp_a.status_code, resp_b.status_code])
    assert statuses == [201, 409], f"정확히 1건 성공(201) + 1건 품절(409)이어야 함. 실제: {statuses}"

    success_count = sum(1 for r in (resp_a, resp_b) if r.status_code == 201)
    soldout_count = sum(1 for r in (resp_a, resp_b) if r.status_code == 409)
    assert success_count == 1
    assert soldout_count == 1
    for resp in (resp_a, resp_b):
        if resp.status_code == 409:
            assert resp.json()["error"] == "SOLD_OUT"

    final_stock = requests.get(server.url("/v1/products/limited-edition-999/stock")).json()
    assert final_stock["stock"] == 0
    assert final_stock["status"] == "SOLD_OUT"


def test_lock_serializes_requests_even_under_artificial_delay(last_unit_server):
    """
    lock 내부에서 80ms 씩 지연시켜, 두 요청이 critical section 안에서 반드시 겹치도록 강제한다.
    (Barrier 타이밍만으로는 우연히 겹치지 않을 수 있어, 이 테스트가 '항상 재현되는' 회귀 방지망 역할을 한다.)
    """
    server = last_unit_server
    barrier = threading.Barrier(2)

    def _order():
        barrier.wait()
        return requests.post(
            f"{server.base_url}/v1/orders",
            json={"productId": "limited-edition-999", "quantity": 1, "_artificialDelaySeconds": 0.08},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_order)
        f2 = pool.submit(_order)
        resp1, resp2 = f1.result(), f2.result()

    statuses = sorted([resp1.status_code, resp2.status_code])
    assert statuses == [201, 409]

    final_stock = requests.get(server.url("/v1/products/limited-edition-999/stock")).json()
    assert final_stock["stock"] == 0, "락이 정상 동작하지 않으면 재고가 음수가 되거나 두 건 모두 성공할 수 있다."


def test_no_oversell_under_high_concurrency(last_unit_server):
    """재고 1개 상품에 10개의 동시 요청을 던져도 성공은 정확히 1건이어야 한다 (oversell 방지 회귀 테스트)."""
    server = last_unit_server
    n_requests = 10
    barrier = threading.Barrier(n_requests)

    def _order():
        barrier.wait()
        return requests.post(server.url("/v1/orders"), json={"productId": "limited-edition-999", "quantity": 1})

    with ThreadPoolExecutor(max_workers=n_requests) as pool:
        responses = list(pool.map(lambda _: _order(), range(n_requests)))

    success = [r for r in responses if r.status_code == 201]
    soldout = [r for r in responses if r.status_code == 409]

    assert len(success) == 1, f"동시 요청 {n_requests}건 중 정확히 1건만 성공해야 함. 성공 {len(success)}건"
    assert len(soldout) == n_requests - 1

    final_stock = requests.get(server.url("/v1/products/limited-edition-999/stock")).json()
    assert final_stock["stock"] == 0
