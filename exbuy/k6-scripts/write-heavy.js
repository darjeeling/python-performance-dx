// 쓰기 중심 부하 테스트
// 30% 읽기, 70% 쓰기 (트랜잭션)

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter } from 'k6/metrics';

const errorRate = new Rate('errors');
const testMarker = new Counter('test_execution_marker');

const BASE_URL = __ENV.BASE_URL ? `${__ENV.BASE_URL}/api` : 'http://localhost:9000/api';
const MAX_VU = parseInt(__ENV.MAX_VU || '200');
const DURATION = __ENV.DURATION || '2m';
const RAMP_UP = __ENV.RAMP_UP || '10s';
const RAMP_DOWN = __ENV.RAMP_DOWN || '30s';
const SERVER_TYPE = __ENV.SERVER_TYPE || 'unknown';
const SCENARIO_NAME = 'write-heavy';

export const options = {
  stages: [
    { duration: RAMP_UP, target: MAX_VU },
    { duration: DURATION, target: MAX_VU },
    { duration: RAMP_DOWN, target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<800', 'p(99)<1500'],
    http_req_failed: ['rate<0.15'],
    errors: ['rate<0.15'],
  },
  tags: {
    scenario: SCENARIO_NAME,
    server_type: SERVER_TYPE,
  },
};

// 테스트 시작 시 실행 (1회만)
export function setup() {
  const startTime = new Date().toISOString();
  console.log(`[TEST START] ${startTime} - Server: ${SERVER_TYPE}, Scenario: ${SCENARIO_NAME}, VU: ${MAX_VU}`);
  testMarker.add(1, { event: 'start', server: SERVER_TYPE, scenario: SCENARIO_NAME });
  return { startTime, server: SERVER_TYPE, scenario: SCENARIO_NAME, maxVU: MAX_VU };
}

// 테스트 종료 시 실행 (1회만)
export function teardown(data) {
  const endTime = new Date().toISOString();
  console.log(`[TEST END] ${endTime} - Server: ${data.server}, Scenario: ${data.scenario}`);
  testMarker.add(1, { event: 'end', server: data.server, scenario: data.scenario });
}

export default function () {
  const rand = Math.random();

  if (rand < 0.7) {
    // 70% 쓰기
    const writeScenarios = [
      () => testCreateOrder(),
      () => testCreateReview(),
      () => testReserveInventory(),
      () => testUpdateOrderStatus(),
    ];
    const scenario = writeScenarios[Math.floor(Math.random() * writeScenarios.length)];
    scenario();
  } else {
    // 30% 읽기
    const readScenarios = [
      () => testProductList(),
      () => testOrderDetail(),
    ];
    const scenario = readScenarios[Math.floor(Math.random() * readScenarios.length)];
    scenario();
  }

  sleep(0.2);
}

function testCreateOrder() {
  const payload = JSON.stringify({
    user_id: Math.floor(Math.random() * 10000) + 1,
    items: [
      {
        product_id: Math.floor(Math.random() * 100) + 1,  // ID 범위 축소: 1-100
        quantity: Math.floor(Math.random() * 5) + 1,
      },
      {
        product_id: Math.floor(Math.random() * 100) + 1,  // ID 범위 축소: 1-100
        quantity: Math.floor(Math.random() * 3) + 1,
      },
    ],
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'create-order' },
  };

  const res = http.post(`${BASE_URL}/orders/`, payload, params);  // trailing slash 추가
  check(res, {
    'create order status 201': (r) => r.status === 201,
  }) || errorRate.add(1);
}

function testCreateReview() {
  const payload = JSON.stringify({
    product: Math.floor(Math.random() * 100) + 1,  // ID 범위 축소: 1-100
    user_id: Math.floor(Math.random() * 10000) + 1,
    rating: Math.floor(Math.random() * 5) + 1,
    body: 'This is a test review from k6 load testing.',
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'create-review' },
  };

  const res = http.post(`${BASE_URL}/reviews/`, payload, params);  // trailing slash 추가
  check(res, {
    'create review status 201': (r) => r.status === 201,
  }) || errorRate.add(1);
}

function testReserveInventory() {
  const payload = JSON.stringify({
    product_id: Math.floor(Math.random() * 100) + 1,  // ID 범위 축소: 1-100
    quantity: Math.floor(Math.random() * 5) + 1,
  });

  const lockType = Math.random() < 0.5 ? 'optimistic' : 'pessimistic';

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: `reserve-inventory-${lockType}` },
  };

  const res = http.post(`${BASE_URL}/inventory/reserve?lock_type=${lockType}`, payload, params);
  check(res, {
    'reserve inventory status 200 or 400': (r) => r.status === 200 || r.status === 400,
  }) || errorRate.add(1);
}

function testUpdateOrderStatus() {
  const orderId = Math.floor(Math.random() * 500) + 1;  // ID 범위 축소: 1-500
  const statuses = ['processing', 'shipped', 'delivered'];
  const status = statuses[Math.floor(Math.random() * statuses.length)];

  const payload = JSON.stringify({ status });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'update-order-status' },
  };

  const res = http.patch(`${BASE_URL}/orders/${orderId}/`, payload, params);  // trailing slash 추가
  check(res, {
    'update order status 200 or 404': (r) => r.status === 200 || r.status === 404,
  }) || errorRate.add(1);
}

function testProductList() {
  const res = http.get(`${BASE_URL}/products/?page=1`, {  // trailing slash 추가
    tags: { name: 'product-list' },
  });
  check(res, {
    'product list status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testOrderDetail() {
  const orderId = Math.floor(Math.random() * 500) + 1;  // ID 범위 축소: 1-500
  const res = http.get(`${BASE_URL}/orders/${orderId}/`, {  // trailing slash 추가
    tags: { name: 'order-detail' },
  });
  check(res, {
    'order detail status 200 or 404': (r) => r.status === 200 || r.status === 404,
  }) || errorRate.add(1);
}
