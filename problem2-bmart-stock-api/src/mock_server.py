"""
B마트 재고/주문 API Mock 서버

과제 PDF에 주어진 3개 엔드포인트에 더해, '재고 처리 규칙' 표에 등장하는
"운영자 재고 수동 수정"을 지원자가 합리적으로 정의한 4번째 엔드포인트로 추가했다.
(명세는 지원자가 합리적으로 정의하라는 지시에 따름 — README 참고)

엔드포인트
    GET   /v1/products/{productId}/stock         재고 조회
    POST  /v1/orders                              주문 생성 (재고 차감)
    POST  /v1/orders/{orderId}/cancel             주문 취소 (재고 복구)
    PATCH /v1/admin/products/{productId}/stock    운영자 재고 수동 수정 (추가 정의)

동시성 보장
    상품별로 threading.Lock 을 두고, "재고 확인 → 차감"을 하나의 임계구역(critical section)으로
    묶어 원자적으로 처리한다. 이렇게 해야 동시 주문 시 재고가 마이너스로 내려가거나
    이중 판매(oversell)가 발생하지 않는다. (문제2 동시성 시나리오의 핵심 검증 포인트)
"""
from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from flask import Flask, jsonify, request


@dataclass
class Product:
    product_id: str
    name: str
    stock: int
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def status(self) -> str:
        return "SOLD_OUT" if self.stock <= 0 else "IN_STOCK"

    def to_dict(self) -> dict:
        return {"productId": self.product_id, "name": self.name, "stock": self.stock, "status": self.status}


@dataclass
class Order:
    order_id: str
    product_id: str
    quantity: int
    status: str  # COMPLETED | CANCELLED

    def to_dict(self) -> dict:
        return {
            "orderId": self.order_id,
            "productId": self.product_id,
            "quantity": self.quantity,
            "status": self.status,
        }


class StockStore:
    """서버의 인메모리 상태. 테스트마다 새 인스턴스를 만들어 격리한다."""

    def __init__(self, initial_products: Optional[Dict[str, dict]] = None):
        self.products: Dict[str, Product] = {}
        if initial_products:
            for pid, info in initial_products.items():
                self.products[pid] = Product(product_id=pid, name=info.get("name", pid), stock=info["stock"])
        self.orders: Dict[str, Order] = {}
        self._order_seq = itertools.count(1)
        self._orders_lock = threading.Lock()

    def get_product(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)

    def create_order(self, product_id: str, quantity: int, artificial_delay: float = 0.0) -> tuple[int, dict]:
        product = self.products.get(product_id)
        if product is None:
            return 404, {"error": "PRODUCT_NOT_FOUND", "message": f"상품을 찾을 수 없습니다: {product_id}"}
        if quantity <= 0:
            return 400, {"error": "INVALID_QUANTITY", "message": "주문 수량은 1 이상이어야 합니다."}

        # --- 임계구역: 재고 확인과 차감을 원자적으로 수행 ---
        with product.lock:
            # 동시성 테스트에서 두 요청이 lock 대기 중 겹치도록 인위적 지연을 줄 수 있게 훅을 둔다.
            if artificial_delay:
                time.sleep(artificial_delay)
            if product.stock < quantity:
                return 409, {
                    "error": "SOLD_OUT",
                    "message": f"재고가 부족합니다. (요청 {quantity}, 재고 {product.stock})",
                }
            product.stock -= quantity
        # --- 임계구역 종료 ---

        with self._orders_lock:
            order_id = f"order-{next(self._order_seq)}"
            order = Order(order_id=order_id, product_id=product_id, quantity=quantity, status="COMPLETED")
            self.orders[order_id] = order

        return 201, order.to_dict()

    def cancel_order(self, order_id: str) -> tuple[int, dict]:
        order = self.orders.get(order_id)
        if order is None:
            return 404, {"error": "ORDER_NOT_FOUND", "message": f"주문을 찾을 수 없습니다: {order_id}"}
        if order.status == "CANCELLED":
            return 409, {"error": "ALREADY_CANCELLED", "message": "이미 취소된 주문입니다."}

        product = self.products.get(order.product_id)
        with product.lock:
            product.stock += order.quantity
        order.status = "CANCELLED"

        return 200, order.to_dict()

    def admin_update_stock(self, product_id: str, new_stock: int) -> tuple[int, dict]:
        product = self.products.get(product_id)
        if product is None:
            return 404, {"error": "PRODUCT_NOT_FOUND", "message": f"상품을 찾을 수 없습니다: {product_id}"}
        if new_stock < 0:
            return 400, {"error": "INVALID_STOCK", "message": "재고 수량은 0 이상이어야 합니다."}
        with product.lock:
            product.stock = new_stock
        return 200, product.to_dict()


def create_app(initial_products: Optional[Dict[str, dict]] = None) -> Flask:
    """테스트마다 독립된 상태를 가진 Flask 앱을 생성한다."""
    app = Flask(__name__)
    app.config["store"] = StockStore(initial_products)

    @app.get("/v1/products/<product_id>/stock")
    def get_stock(product_id: str):
        store: StockStore = app.config["store"]
        product = store.get_product(product_id)
        if product is None:
            return jsonify({"error": "PRODUCT_NOT_FOUND", "message": f"상품을 찾을 수 없습니다: {product_id}"}), 404
        return jsonify(product.to_dict()), 200

    @app.post("/v1/orders")
    def create_order():
        store: StockStore = app.config["store"]
        body = request.get_json(silent=True) or {}
        product_id = body.get("productId")
        quantity = body.get("quantity", 1)
        # 테스트에서 lock 경합 구간을 넓히기 위한 디버그 전용 파라미터 (운영 API에는 없음)
        artificial_delay = float(body.get("_artificialDelaySeconds", 0) or 0)

        if not product_id:
            return jsonify({"error": "INVALID_REQUEST", "message": "productId는 필수입니다."}), 400

        status_code, payload = store.create_order(product_id, quantity, artificial_delay)
        return jsonify(payload), status_code

    @app.post("/v1/orders/<order_id>/cancel")
    def cancel_order(order_id: str):
        store: StockStore = app.config["store"]
        status_code, payload = store.cancel_order(order_id)
        return jsonify(payload), status_code

    @app.patch("/v1/admin/products/<product_id>/stock")
    def admin_update_stock(product_id: str):
        store: StockStore = app.config["store"]
        body = request.get_json(silent=True) or {}
        if "stock" not in body:
            return jsonify({"error": "INVALID_REQUEST", "message": "stock 필드는 필수입니다."}), 400
        status_code, payload = store.admin_update_stock(product_id, body["stock"])
        return jsonify(payload), status_code

    return app


if __name__ == "__main__":
    # 로컬에서 수동으로 API를 찔러보고 싶을 때: python src/mock_server.py
    demo_app = create_app({"chicken-fried-001": {"name": "후라이드 치킨", "stock": 5}})
    demo_app.run(port=5001, debug=True)
