# 문제2. B마트 재고 API 테스트 자동화 구현

[![Problem2 Tests](https://github.com/YeongjunLim/woowahan-qa-assignment/actions/workflows/problem2-tests.yml/badge.svg)](https://github.com/YeongjunLim/woowahan-qa-assignment/actions/workflows/problem2-tests.yml)

## 실행 방법

```bash
cd problem2-bmart-stock-api
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest tests/ -v
# 동시성 테스트의 타이밍 로그까지 보려면:
pytest tests/ -v -s
```

실제 서버가 없으므로 `src/mock_server.py`에 **Flask 기반 스텁 서버**를 직접 구현했다. 외부 Mock 도구(WireMock 등) 대신 직접 구현을 택한 이유는, 문제2의 핵심이 "재고 차감/복구의 **동시성 정합성**"이기 때문에 실제 `threading.Lock` 기반 임계구역 처리를 서버 쪽에 넣어야 동시성 테스트가 의미를 가지기 때문이다 (단순 응답 스텁으로는 락 경쟁 상황 자체를 재현할 수 없다).

## API 명세 (지원자 정의)

과제에 주어진 3개 API에, '재고 처리 규칙' 표의 "운영자 재고 수동 수정" 이벤트를 커버하기 위한 API를 하나 추가로 정의했다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/v1/products/{productId}/stock` | 재고 조회 → `{productId, name, stock, status}` (`status`는 `IN_STOCK`/`SOLD_OUT`) |
| POST | `/v1/orders` | 주문 생성. body: `{productId, quantity}` → 성공 시 201 + 주문 정보, 재고 부족 시 409 `SOLD_OUT` |
| POST | `/v1/orders/{orderId}/cancel` | 주문 취소, 재고 복구 → 200. 이미 취소된 주문이면 409 `ALREADY_CANCELLED` |
| PATCH | `/v1/admin/products/{productId}/stock` | (추가 정의) 운영자 수동 재고 수정. body: `{stock}` → 200 |

에러는 모두 `{"error": "<CODE>", "message": "..."}` 형태로 통일했다.

## 테스트 케이스 설계

테스트는 감으로 나열하지 않고 **블랙박스 테스트 설계기법**(상태 전이/경계값 분석/동등 분할/결정 테이블)으로 도출했다. 기법별 설계 근거와 다이어그램은 [TEST_DESIGN.md](TEST_DESIGN.md), 케이스별 입력값·예상결과 명세는 [TEST_CASES.md](TEST_CASES.md) 참고. 전체 **25개 테스트, TC-01~TC-25**로 ID를 부여했고 코드 주석과 1:1 대응한다.

과제 요구사항 대비 매핑:

| 요구사항 | 해당 TC |
|---|---|
| 정상 케이스 | TC-01, TC-02, TC-03, TC-04, TC-10, TC-19 |
| 재고 복구 | TC-05, TC-06, TC-18 |
| 품절 전환 | TC-07, TC-08, TC-09, TC-17, TC-20 |
| 동시성(재고 1개, 수십 ms 간격 도달) | **TC-23** (요구사항 시나리오 그 자체), TC-24·TC-25(보강) |

## 테스트 코드 구조

```
tests/
  conftest.py                    # fixture, 서버 기동/종료, 검증 헬퍼
  test_stock_and_orders.py       # 정상/재고복구/품절전환/경계값/상태전이 (TC-01~TC-18)
  test_admin_update_ordering.py  # 결정 테이블: 운영자 수정 vs 주문 처리 순서 (TC-19~TC-22)
  test_concurrency.py            # 동시 주문 3개 케이스 (TC-23~TC-25)
```

### fixture 설계
- `make_server_with(initial_products)`: 원하는 초기 재고로 **매 테스트마다 격리된** 서버 인스턴스를 띄우는 factory fixture. 테스트 간 상태 공유로 인한 flaky를 원천 차단하기 위해, 공용 서버를 재사용하지 않고 테스트마다 새 in-memory store + 새 포트로 서버를 기동한다.
- `server`: 재고가 여유 있는 기본 상품 세트 (일반 케이스용)
- `last_unit_server`: 재고 1개 상품 (품절 전환/동시성 케이스용)
- 서버는 `werkzeug.serving.make_server`로 별도 스레드에서 실제 소켓을 열어 구동한다. Flask의 `test_client()`를 쓰지 않은 이유는, 동시성 테스트가 **진짜 네트워크 요청**으로 서버에 동시에 도달하는 상황을 재현해야 하기 때문이다.

### 데이터 준비 / 검증 헬퍼
- `assert_stock(response, expected_stock, expected_status)` / `assert_error(response, http_status, error_code)`: 응답 바디를 매번 손으로 파싱하지 않도록 공용 검증 헬퍼로 분리. 테스트 본문이 "무엇을 검증하는지"에만 집중하도록 했다.
- docstring에 '재고 처리 규칙' 표의 이벤트 → 테스트 함수 매핑을 명시해, 요구사항 대비 커버리지를 한눈에 추적할 수 있게 했다.

## 동시성 테스트 설계 (핵심)

`mock_server.py`는 상품별 `threading.Lock`으로 "재고 확인 → 차감"을 하나의 임계구역으로 묶어 처리한다. 이 락이 없으면 두 요청이 동시에 `stock < quantity` 체크를 통과해버려 재고가 음수가 되거나 이중 판매가 발생한다.

이를 검증하기 위해 3개의 상호 보완적인 테스트를 작성했다.

1. **`test_tc23_concurrent_orders_on_last_unit`**
   `threading.Barrier(2)`로 두 스레드를 동시에 출발시켜 실제 고객 A/B가 거의 동시에 결제하는 상황을 재현. 실제 도달 간격을 로그로 남기되(환경마다 달라질 수 있어 하드 어서션은 하지 않음), "정확히 1건 성공 + 1건 품절"이라는 비즈니스 불변식만 엄격히 검증한다.
2. **`test_tc24_lock_serializes_under_artificial_delay`**
   Barrier만으로는 두 요청이 서버의 critical section 안에서 실제로 겹친다는 보장이 없다(스케줄링이 빨라 우연히 순차 처리될 수 있음). 그래서 서버에 디버그용 `_artificialDelaySeconds` 파라미터를 훅으로 열어두고, lock 내부에서 강제로 지연시켜 두 요청이 **반드시** 경합하도록 만든 뒤에도 정합성이 깨지지 않는지 결정적으로 증명한다.
3. **`test_tc25_no_oversell_under_high_concurrency`**
   2건이 아니라 10건을 동시에 쏘아도 성공은 정확히 1건이어야 함을 검증해, 동시성 정도가 늘어나도 락이 견고한지 추가로 보증한다.

> 왜 타이밍을 하드 어서션하지 않았는가: "정확히 수십 ms 간격"을 CI 환경에서 강제로 재현/검증하려 하면 그 자체가 새로운 flaky 원인이 된다. 대신 (1) 실제 근접 타이밍 재현 + 로그 기록, (2) 인위적 지연으로 경합을 강제해 결정적으로 검증, 두 가지를 분리해 "현실성"과 "재현 가능성"을 모두 확보했다.

## AI 도구 활용 내역
README 하단 [최상위 README](../README.md#ai-도구-활용-내역)에 통합 기재.
