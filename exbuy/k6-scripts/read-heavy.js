// 읽기 중심 부하 테스트
// 80% 읽기, 20% 쓰기

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api';

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // 워밍업
    { duration: '1m', target: 100 },   // 부하 증가
    { duration: '2m', target: 100 },   // 안정 상태
    { duration: '30s', target: 0 },    // 감소
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.1'],
    errors: ['rate<0.1'],
  },
};

export default function () {
  const scenarios = [
    () => testHealthCheck(),
    () => testProductList(),
    () => testProductDetail(),
    () => testProductSearch(),
    () => testProductListOptimized(),
    () => testProductDetailOptimized(),
    () => testReviews(),
    () => testStats(),
  ];

  // 80% 읽기 시나리오
  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  scenario();

  sleep(0.1);
}

function testHealthCheck() {
  const res = http.get(`${BASE_URL}/health`);
  check(res, {
    'health check status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductList() {
  const params = {
    tags: { name: 'product-list' },
  };
  const res = http.get(`${BASE_URL}/products?page=1`, params);
  check(res, {
    'product list status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductDetail() {
  const productId = Math.floor(Math.random() * 1000) + 1;
  const res = http.get(`${BASE_URL}/products/${productId}`, {
    tags: { name: 'product-detail' },
  });
  check(res, {
    'product detail status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductSearch() {
  const queries = ['book', 'phone', 'shirt', 'food', 'home'];
  const q = queries[Math.floor(Math.random() * queries.length)];
  const res = http.get(`${BASE_URL}/search/products?q=${q}`, {
    tags: { name: 'product-search' },
  });
  check(res, {
    'product search status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductListOptimized() {
  const res = http.get(`${BASE_URL}/products?page=1&optimize=true`, {
    tags: { name: 'product-list-optimized' },
  });
  check(res, {
    'optimized product list status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testProductDetailOptimized() {
  const productId = Math.floor(Math.random() * 1000) + 1;
  const res = http.get(`${BASE_URL}/products/${productId}?optimize=true`, {
    tags: { name: 'product-detail-optimized' },
  });
  check(res, {
    'optimized product detail status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testReviews() {
  const productId = Math.floor(Math.random() * 1000) + 1;
  const res = http.get(`${BASE_URL}/reviews?product_id=${productId}`, {
    tags: { name: 'reviews' },
  });
  check(res, {
    'reviews status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function testStats() {
  const res = http.get(`${BASE_URL}/stats/top-products?limit=10`, {
    tags: { name: 'stats' },
  });
  check(res, {
    'stats status 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}
