// 순수 읽기 전용 부하 테스트 (5분 30초)
// 100% 읽기 작업만 수행

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');
const BASE_URL = __ENV.BASE_URL ? `${__ENV.BASE_URL}/api` : 'http://localhost:9000/api';
const MAX_VU = parseInt(__ENV.MAX_VU || '200');

export const options = {
  stages: [
    { duration: '30s', target: MAX_VU },   // 램프업
    { duration: '5m', target: MAX_VU },    // 안정 상태 5분
  ],
  thresholds: {
    http_req_duration: ['p(95)<800', 'p(99)<1500'],
    http_req_failed: ['rate<0.1'],
    errors: ['rate<0.1'],
  },
};

export default function () {
  // 읽기 시나리오만 실행
  const scenarios = [
    () => testHealthCheck(),
    () => testProductList(),
    () => testProductDetail(),
    () => testProductSearch(),
    () => testProductListOptimized(),
    () => testProductDetailOptimized(),
    () => testReviews(),
    () => testOrderDetail(),
    () => testStats(),
  ];

  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  scenario();

  sleep(0.1);
}

// === 읽기 시나리오 ===
function testHealthCheck() {
  const res = http.get(`${BASE_URL}/health`, {
    tags: { name: 'health-check' },
  });
  check(res, {
    'health check status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductList() {
  const page = Math.floor(Math.random() * 3) + 1;  // 페이지 범위 축소: 1-3
  const res = http.get(`${BASE_URL}/products/?page=${page}`, {  // trailing slash 추가
    tags: { name: 'product-list' },
  });
  check(res, {
    'product list status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductDetail() {
  const productId = Math.floor(Math.random() * 100) + 1;  // ID 범위 축소: 1-100
  const res = http.get(`${BASE_URL}/products/${productId}/`, {  // trailing slash 추가
    tags: { name: 'product-detail' },
  });
  check(res, {
    'product detail status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductSearch() {
  const queries = ['book', 'phone', 'shirt', 'laptop', 'food', 'home', 'electronics'];
  const q = queries[Math.floor(Math.random() * queries.length)];
  const categories = ['electronics', 'clothing', 'food', 'books', 'home'];
  const category = Math.random() < 0.5 ? `&category=${categories[Math.floor(Math.random() * categories.length)]}` : '';

  const res = http.get(`${BASE_URL}/search/products?q=${q}${category}`, {
    tags: { name: 'product-search' },
  });
  check(res, {
    'product search status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductListOptimized() {
  const page = Math.floor(Math.random() * 3) + 1;  // 페이지 범위 축소: 1-3
  const res = http.get(`${BASE_URL}/products/?page=${page}&optimize=true`, {  // trailing slash 추가
    tags: { name: 'product-list-optimized' },
  });
  check(res, {
    'optimized product list status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductDetailOptimized() {
  const productId = Math.floor(Math.random() * 100) + 1;  // ID 범위 축소: 1-100
  const res = http.get(`${BASE_URL}/products/${productId}/?optimize=true`, {  // trailing slash 추가
    tags: { name: 'product-detail-optimized' },
  });
  check(res, {
    'optimized product detail status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testReviews() {
  const productId = Math.floor(Math.random() * 100) + 1;  // ID 범위 축소: 1-100
  const optimize = Math.random() < 0.3 ? '&optimize=true' : '';
  const res = http.get(`${BASE_URL}/reviews/?product_id=${productId}${optimize}`, {  // trailing slash 추가
    tags: { name: 'reviews' },
  });
  check(res, {
    'reviews status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testOrderDetail() {
  const orderId = Math.floor(Math.random() * 500) + 1;  // ID 범위 축소: 1-500
  const optimize = Math.random() < 0.5 ? '?optimize=true' : '';
  const res = http.get(`${BASE_URL}/orders/${orderId}/${optimize}`, {  // trailing slash 추가
    tags: { name: 'order-detail' },
  });
  check(res, {
    'order detail status 200 or 404': (r) => r.status === 200 || r.status === 404,
  }) || errorRate.add(1);
}

function testStats() {
  const limit = [5, 10, 20][Math.floor(Math.random() * 3)];
  const res = http.get(`${BASE_URL}/stats/top-products?limit=${limit}`, {
    tags: { name: 'stats-top-products' },
  });
  check(res, {
    'stats status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}
