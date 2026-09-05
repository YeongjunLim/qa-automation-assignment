"""
공용 pytest fixture 모음.

설계 의도
    - 각 테스트는 '자기만의 서버 인스턴스'를 갖는다 (test isolation). 상태를 공유하는 순간
      테스트 실행 순서에 따라 결과가 달라지는 flaky의 씨앗이 되기 때문에, 매 테스트마다
      새 in-memory store로 서버를 띄우고 끝나면 종료한다.
    - 실제 소켓으로 HTTP 요청을 주고받는 '진짜 서버'를 띄운다 (Flask test_client가 아니라
      werkzeug 실서버 + requests 조합). 그래야 문제2에서 요구하는 '병렬 요청이 수십 ms 간격으로
      서버에 도달하는' 동시성 테스트를 네트워크 레벨에서 그대로 재현할 수 있다.
    - product/order 데이터 준비는 fixture factory 패턴(`make_server`)으로 제공해,
      테스트마다 필요한 초기 재고 상태를 자유롭게 구성할 수 있게 한다.
"""
from __future__ import annotations

import socket
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict

import pytest
import requests
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mock_server import create_app  # noqa: E402


def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class LiveServer:
    base_url: str

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"


class _ServerThread:
    def __init__(self, app):
        self.port = _find_free_port()
        self.server = make_server("127.0.0.1", self.port, app)
        self._thread = None

    def start(self):
        import threading

        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        self._wait_until_ready()

    def _wait_until_ready(self, timeout: float = 3.0):
        base_url = f"http://127.0.0.1:{self.port}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                requests.get(f"{base_url}/v1/products/__healthcheck__/stock", timeout=0.2)
                return
            except requests.exceptions.ConnectionError:
                time.sleep(0.02)
        raise RuntimeError("mock server did not start in time")

    def stop(self):
        self.server.shutdown()
        if self._thread:
            self._thread.join(timeout=2)


@pytest.fixture
def make_server_with(request):
    """
    초기 상품 데이터를 받아 실행 중인 mock 서버를 반환하는 factory fixture.

    사용 예:
        server = make_server_with({"chicken-001": {"name": "후라이드", "stock": 5}})
        resp = requests.get(server.url("/v1/products/chicken-001/stock"))
    """
    created: list[_ServerThread] = []

    def _factory(initial_products: Dict[str, dict]) -> LiveServer:
        app = create_app(initial_products)
        server_thread = _ServerThread(app)
        server_thread.start()
        created.append(server_thread)
        return LiveServer(base_url=f"http://127.0.0.1:{server_thread.port}")

    yield _factory

    for s in created:
        s.stop()


@pytest.fixture
def server(make_server_with) -> LiveServer:
    """기본 상품 세트(재고 여유 있음)로 띄운 서버 — 단순 조회/주문 테스트용."""
    return make_server_with(
        {
            "chicken-fried-001": {"name": "후라이드 치킨", "stock": 10},
            "snack-honeybutter-002": {"name": "허니버터칩", "stock": 3},
        }
    )


@pytest.fixture
def last_unit_server(make_server_with) -> LiveServer:
    """재고가 정확히 1개 남은 상품 — 동시성/품절 전환 테스트용."""
    return make_server_with({"limited-edition-999": {"name": "한정판 치킨", "stock": 1}})


# ---- 검증 헬퍼 (assertion helper) ----
# 응답 바디를 매번 손으로 파싱/검증하지 않도록 공용 헬퍼를 제공한다.


def assert_stock(response: requests.Response, expected_stock: int, expected_status: str | None = None):
    body = response.json()
    assert body["stock"] == expected_stock, f"기대 재고 {expected_stock}, 실제 {body['stock']} (body={body})"
    if expected_status:
        assert body["status"] == expected_status, f"기대 상태 {expected_status}, 실제 {body['status']}"


def assert_error(response: requests.Response, expected_http_status: int, expected_error_code: str):
    assert response.status_code == expected_http_status, response.text
    body = response.json()
    assert body["error"] == expected_error_code, f"기대 에러코드 {expected_error_code}, 실제 body={body}"
