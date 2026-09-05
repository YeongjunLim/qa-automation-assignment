# 테스트 케이스 명세 — B마트 재고 API

각 케이스가 어떤 설계기법에서 도출됐는지는 [TEST_DESIGN.md](TEST_DESIGN.md) 참고. 이 문서는 케이스별 사전조건·입력·예상결과를 실행 가능한 수준으로 구체화한 명세다. ID는 코드의 테스트 함수와 1:1로 대응한다.

| ID | 요구사항 카테고리 | 설계기법 | 사전조건 | 입력 | 예상 결과 | 테스트 함수 |
|---|---|---|---|---|---|---|
| TC-01 | 정상 | 동등분할(유효 productId) | 상품 재고 10 | `GET /stock` | 200, stock=10, status=IN_STOCK | `test_get_stock_returns_current_quantity` |
| TC-02 | 정상 | - | 상품 재고 3 | `GET /stock` 5회 반복 | 매번 200, stock=3 불변(조회는 부작용 없음) | `test_reading_stock_repeatedly_has_no_side_effect` |
| TC-03 | 정상 | 경계값(하한 바로 위) | 재고 10 | `POST /orders` quantity=1 | 201, order.status=COMPLETED, 재고 9 | `test_successful_order_decrements_stock_and_returns_order` |
| TC-04 | 정상 | 경계값(N-1) | 재고 3 | `POST /orders` quantity=2 | 201, 재고 1 | `test_order_with_quantity_greater_than_one` |
| TC-05 | 재고복구 | 상태전이/동등분할(유효 orderId) | 재고 10, 주문 1건(quantity=2) 존재 | `POST /orders/{id}/cancel` | 200, order.status=CANCELLED, 재고 10(원복) | `test_cancel_order_restores_stock` |
| TC-06 | 재고복구 | 상태전이(SOLD_OUT→IN_STOCK) | 재고 1, 주문 완료로 SOLD_OUT 상태 | 주문 취소 후 다른 고객이 `POST /orders` 재시도 | 취소 200, 신규 주문 201 성공 | `test_after_cancel_another_customer_can_purchase_immediately` |
| TC-07 | 품절전환 | 상태전이+경계값(N, 정확히 소진) | 재고 1 | `POST /orders` quantity=1 | 201, 재고 0, status=SOLD_OUT | `test_stock_reaches_zero_becomes_sold_out` |
| TC-08 | 품절전환 | 상태전이(불허 전이) | 재고 0(SOLD_OUT) | `POST /orders` quantity=1 | 409 SOLD_OUT, 재고 그대로 0 | `test_ordering_sold_out_product_returns_409` |
| TC-09 | 품절전환 | 경계값(N+100, 극단초과) | 재고 3 | `POST /orders` quantity=100 | 409 SOLD_OUT | `test_order_quantity_exceeds_stock_returns_409` |
| TC-10 | 정상 | - | 재고 10 | `PATCH /admin/.../stock` stock=50 | 200, 재고 50 | `test_admin_can_manually_update_stock` |
| TC-11 | 예외처리 | 경계값(하한 경계) | 재고 10 | `POST /orders` quantity=0 | 400 INVALID_QUANTITY | `test_order_with_invalid_quantity_returns_400` |
| TC-12 | 예외처리 | 동등분할(무효 productId) | - | `GET /products/no-such/stock` | 404 PRODUCT_NOT_FOUND | `test_get_stock_for_unknown_product_returns_404` |
| TC-13 | 예외처리 | 동등분할(무효 productId) | - | `POST /orders` productId=no-such | 404 PRODUCT_NOT_FOUND | `test_order_for_unknown_product_returns_404` |
| TC-14 | 예외처리 | 상태전이(불허)+동등분할(무효②) | 취소된 주문 1건 존재 | 같은 주문 재취소 시도 | 409 ALREADY_CANCELLED | `test_cancelling_already_cancelled_order_returns_409` |
| TC-15 | 예외처리 | 동등분할(무효①) | - | 존재하지 않는 orderId로 취소 | 404 ORDER_NOT_FOUND | `test_cancelling_unknown_order_returns_404` |
| TC-16 | 예외처리 | 경계값(하한 미만) 🆕 | 재고 10 | `POST /orders` quantity=-1 | 400 INVALID_QUANTITY | `test_order_with_negative_quantity_returns_400` |
| TC-17 | 품절전환 | 경계값(N+1, 경계 바로 위) 🆕 | 재고 3 | `POST /orders` quantity=4 | 409 SOLD_OUT | `test_order_with_quantity_exactly_one_more_than_stock_returns_409` |
| TC-18 | 재고복구 | 상태전이(SOLD_OUT→IN_STOCK, 운영자) 🆕 | 재고 0(SOLD_OUT) | `PATCH /admin/.../stock` stock=5 | 200, status=IN_STOCK, 재고 5 | `test_admin_restock_sold_out_product_makes_it_available_again` |
| TC-19 | 정상 | 결정테이블 R1 🆕 | 재고 0 | 운영자 수정(stock=5) → 주문 quantity=3 | 수정 200(재고5) → 주문 201(재고2) | `test_order_after_admin_restock_succeeds` |
| TC-20 | 품절전환 | 결정테이블 R2 🆕 | 재고 10 | 운영자 수정(stock=1) → 주문 quantity=3 | 수정 200(재고1) → 주문 409 SOLD_OUT | `test_order_after_admin_sets_insufficient_stock_returns_409` |
| TC-21 | 결정테이블 | 결정테이블 R3 🆕 | 재고 5 | 주문 quantity=2(성공, 재고3) → 운영자 수정(stock=100) | 주문 201 → 최종 재고 100(운영자값으로 덮어써짐) | `test_admin_update_after_order_overwrites_final_stock` |
| TC-22 | 결정테이블 | 결정테이블 R4 🆕 | 재고 1 | 주문 quantity=5(품절, 409) → 운영자 수정(stock=20) | 주문 409 → 최종 재고 20(운영자값) | `test_admin_update_after_failed_order_sets_exact_value` |
| TC-23 | 동시성 | 동시성(과제 명시 시나리오) | 재고 1 | 고객 A/B가 Barrier로 동시 출발, 각각 quantity=1 | 정확히 1건 201 + 1건 409, 최종 재고 0 | `test_two_near_simultaneous_orders_on_last_unit_only_one_succeeds` |
| TC-24 | 동시성 | 동시성(강제 경합) | 재고 1 | 락 내부 80ms 지연 주입 후 2건 동시 요청 | 정확히 1건 201 + 1건 409 | `test_lock_serializes_requests_even_under_artificial_delay` |
| TC-25 | 동시성 | 동시성(고강도) | 재고 1 | 10건 동시 요청 | 정확히 1건 201 + 9건 409 | `test_no_oversell_under_high_concurrency` |

## 요구사항 카테고리별 집계

- **정상 케이스**: TC-01, TC-02, TC-03, TC-04, TC-10, TC-19 (6개)
- **재고 복구**: TC-05, TC-06, TC-18 (3개)
- **품절 전환**: TC-07, TC-08, TC-09, TC-17, TC-20 (5개)
- **예외 처리**: TC-11, TC-12, TC-13, TC-14, TC-15, TC-16 (6개)
- **결정 테이블(복합 조건)**: TC-21, TC-22 (2개)
- **동시성**: TC-23, TC-24, TC-25 (3개, 과제가 요구한 동시성 시나리오는 TC-23)

**합계 25개** — 과제 요구사항(10개 이상)을 충족하며, 그중 "정상/재고복구/품절전환" 3개 카테고리에만 14개가 배정된다.
