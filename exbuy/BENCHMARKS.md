# 벤치마크 가이드

ExBuy 성능 테스트 시나리오별 기대값 및 비교 방법론입니다.

## 목차
- [벤치마크 시나리오](#벤치마크-시나리오)
- [서버 구성 비교](#서버-구성-비교)
- [최적화 레벨 비교](#최적화-레벨-비교)
- [동시성 제어 비교](#동시성-제어-비교)
- [측정 방법론](#측정-방법론)

## 벤치마크 시나리오

### 1. Read-Heavy (읽기 중심)
**비율:** 80% 읽기, 20% 쓰기

**엔드포인트 분포:**
- GET /health (5%)
- GET /products (25%)
- GET /products/{id} (20%)
- GET /search/products (15%)
- GET /products/{id}/reviews (15%)
- GET /reviews (10%)
- GET /stats/top-products (10%)

**기대 성능:**
| 메트릭 | 목표 | 우수 |
|--------|------|------|
| p95 응답시간 | < 500ms | < 200ms |
| p99 응답시간 | < 1000ms | < 500ms |
| RPS (4 workers) | > 500 | > 1000 |
| 에러율 | < 1% | < 0.1% |

**테스트 명령:**
```bash
BASE_URL=http://localhost:8000 k6 run k6-scripts/read-heavy.js
```

### 2. Write-Heavy (쓰기 중심)
**비율:** 30% 읽기, 70% 쓰기

**엔드포인트 분포:**
- POST /orders (30%)
- POST /reviews (20%)
- POST /inventory/reserve (15%)
- PATCH /orders/{id} (5%)
- GET /products (20%)
- GET /orders/{id} (10%)

**기대 성능:**
| 메트릭 | 목표 | 우수 |
|--------|------|------|
| p95 응답시간 | < 1000ms | < 500ms |
| p99 응답시간 | < 2000ms | < 1000ms |
| RPS (4 workers) | > 200 | > 500 |
| 에러율 | < 5% | < 1% |

**주의:** 재고 부족 오류는 정상 동작 (400 에러)

**테스트 명령:**
```bash
BASE_URL=http://localhost:8000 k6 run k6-scripts/write-heavy.js
```

### 3. Mixed (혼합)
**비율:** 60% 읽기, 40% 쓰기

**엔드포인트 분포:**
- GET 엔드포인트 (60%)
- POST/PATCH 엔드포인트 (40%)

**기대 성능:**
| 메트릭 | 목표 | 우수 |
|--------|------|------|
| p95 응답시간 | < 800ms | < 400ms |
| p99 응답시간 | < 1500ms | < 800ms |
| RPS (4 workers) | > 300 | > 600 |
| 에러율 | < 3% | < 0.5% |

**테스트 명령:**
```bash
BASE_URL=http://localhost:8000 k6 run k6-scripts/mixed.js
```

## 서버 구성 비교

### 테스트 매트릭스

| 서버 타입 | Worker 클래스 | 포트 | 장점 | 단점 | 추천 시나리오 |
|----------|--------------|------|------|------|--------------|
| Gunicorn | sync | 8000 | 안정성, 디버깅 용이 | I/O 블로킹 | CPU 바운드 작업 |
| Gunicorn | gevent | 8001 | I/O 동시성 우수 | CPU 바운드 느림 | 읽기 중심, 많은 I/O |
| Gunicorn | gthread | 8002 | 균형잡힌 성능 | 메모리 사용 증가 | 혼합 워크로드 |
| Uvicorn | ASGI | 8003 | 비동기 우수, 낮은 지연 | 디버깅 어려움 | WebSocket, SSE |

### 비교 테스트 절차

#### 1. 동시 실행
```bash
# 모든 서버 시작
docker compose --profile gunicorn-sync \
               --profile gunicorn-gevent \
               --profile gunicorn-gthread \
               --profile uvicorn up -d

# 각 서버 상태 확인
curl http://localhost:8000/api/health  # sync
curl http://localhost:8001/api/health  # gevent
curl http://localhost:8002/api/health  # gthread
curl http://localhost:8003/api/health  # uvicorn
```

#### 2. 순차 테스트 (동일 시나리오)
```bash
# 1. Gunicorn sync
BASE_URL=http://localhost:8000 k6 run --out json=results/sync-read.json k6-scripts/read-heavy.js

# 2. Gunicorn gevent
BASE_URL=http://localhost:8001 k6 run --out json=results/gevent-read.json k6-scripts/read-heavy.js

# 3. Gunicorn gthread
BASE_URL=http://localhost:8002 k6 run --out json=results/gthread-read.json k6-scripts/read-heavy.js

# 4. Uvicorn
BASE_URL=http://localhost:8003 k6 run --out json=results/uvicorn-read.json k6-scripts/read-heavy.js
```

#### 3. 결과 비교
```bash
# JSON 결과 비교
python scripts/compare_results.py results/

# 또는 Makefile 사용
make compare-servers
```

### 기대 결과

**Read-Heavy 시나리오:**
```
예상 순위 (RPS 기준):
1. Gunicorn gevent (I/O 바운드에 유리)
2. Uvicorn (비동기 처리)
3. Gunicorn gthread (균형)
4. Gunicorn sync (블로킹)
```

**Write-Heavy 시나리오:**
```
예상 순위 (지연시간 기준):
1. Gunicorn gthread (DB 트랜잭션 처리)
2. Gunicorn sync (안정성)
3. Gunicorn gevent
4. Uvicorn (DB 동기 드라이버 제약)
```

## 최적화 레벨 비교

### Level A: 최적화 없음
```bash
# 기본 쿼리, N+1 문제 발생 가능
curl "http://localhost:8000/api/products/1"
curl "http://localhost:8000/api/products/1/reviews"
```

### Level B: 부분 최적화
```bash
# select_related / prefetch_related 적용
curl "http://localhost:8000/api/products/1?optimize=true"
curl "http://localhost:8000/api/products/1/reviews?optimize=true"
```

### 비교 테스트

#### 단일 엔드포인트 비교
```bash
# 최적화 없음
ab -n 1000 -c 10 http://localhost:8000/api/products/1

# 최적화 적용
ab -n 1000 -c 10 http://localhost:8000/api/products/1?optimize=true
```

#### K6 시나리오 수정
```javascript
// k6-scripts/optimization-test.js
export default function () {
  // 50% 최적화 없음, 50% 최적화 적용
  if (Math.random() < 0.5) {
    http.get(`${BASE_URL}/products/${productId}`);
  } else {
    http.get(`${BASE_URL}/products/${productId}?optimize=true`);
  }
}
```

### 기대 개선율

| 엔드포인트 | 최적화 없음 | 최적화 적용 | 개선율 |
|-----------|-------------|-------------|--------|
| GET /products/{id} | ~200ms | ~50ms | 75% ↓ |
| GET /products/{id}/reviews | ~500ms | ~100ms | 80% ↓ |
| GET /orders/{id} | ~300ms | ~80ms | 73% ↓ |

## 동시성 제어 비교

### 낙관적 락 vs 비관적 락

#### 테스트 설정
```bash
# 동시 재고 예약 요청 (100 VUs)
k6 run --vus 100 --duration 30s k6-scripts/concurrency-test.js
```

#### 비교 포인트

**1. 낙관적 락 (F() 사용)**
```bash
curl -X POST http://localhost:8000/api/inventory/reserve?lock_type=optimistic \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}'
```

**장점:**
- 높은 처리량 (TPS)
- 낮은 DB 락 경합

**단점:**
- 재시도 로직 필요
- 높은 동시성 시 실패율 증가

**2. 비관적 락 (SELECT FOR UPDATE)**
```bash
curl -X POST http://localhost:8000/api/inventory/reserve?lock_type=pessimistic \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}'
```

**장점:**
- 데이터 정합성 보장
- 예측 가능한 동작

**단점:**
- 낮은 처리량
- 락 대기 시간 증가

### 기대 결과

| 메트릭 | 낙관적 락 | 비관적 락 |
|--------|----------|----------|
| 처리량 (TPS) | ~500 | ~200 |
| 평균 응답시간 | 50ms | 150ms |
| p99 응답시간 | 200ms | 500ms |
| 실패율 (동시성↑) | 5-10% | <1% |

## 측정 방법론

### 1. 테스트 환경 통제

**고정 변수:**
- CPU cores: 4
- Memory: 8GB
- Workers: 4
- DB connections: 200
- 데이터 규모: 10K products, 50K orders

**변경 변수:**
- 서버 타입
- Worker 클래스
- 최적화 레벨
- 동시성 제어 방식

### 2. Warmup 필수
```bash
# 테스트 전 반드시 실행
./warmup.sh

# 또는
for i in {1..100}; do
  curl -s http://localhost:8000/api/products/$i > /dev/null
done
```

### 3. 반복 테스트
```bash
# 각 시나리오 3회 반복, 중간값 사용
for i in {1..3}; do
  BASE_URL=http://localhost:8000 k6 run \
    --out json=results/run-$i.json \
    k6-scripts/mixed.js
  sleep 60  # 테스트 간 대기
done
```

### 4. 리소스 모니터링
```bash
# 테스트 중 리소스 사용량 기록
docker stats --no-stream > results/resources.log &
TEST_PID=$!

# 테스트 실행
k6 run k6-scripts/mixed.js

# 모니터링 종료
kill $TEST_PID
```

### 5. 결과 분석

**주요 메트릭:**
1. **처리량**: `http_reqs` (RPS)
2. **지연시간**: `http_req_duration` (p50, p95, p99)
3. **에러율**: `http_req_failed`
4. **리소스**: CPU%, Memory%

**분석 도구:**
```bash
# K6 요약
k6 run --summary-export=summary.json k6-scripts/mixed.js

# Grafana 대시보드
http://localhost:3000

# Prometheus 쿼리
rate(django_http_requests_total[1m])
```

## 권장 테스트 순서

1. **기본 성능 측정** (Gunicorn sync, 최적화 없음)
2. **Worker 타입 비교** (sync vs gevent vs gthread vs uvicorn)
3. **최적화 효과 측정** (optimize=false vs optimize=true)
4. **동시성 제어 비교** (optimistic vs pessimistic)
5. **스케일링 테스트** (workers: 2 → 4 → 8)

## 결과 리포트 예시

```markdown
## 테스트 결과 요약

**환경:**
- 서버: Gunicorn sync, 4 workers
- 데이터: 10K products, 50K orders
- 시나리오: Mixed (60% read, 40% write)

**결과:**
- RPS: 450
- p95 latency: 650ms
- p99 latency: 1200ms
- Error rate: 1.2%

**개선 사항:**
1. gevent worker로 변경 → RPS 30% 증가
2. prefetch_related 적용 → latency 40% 감소
```

## 다음 단계

성능 개선을 위한 구체적인 방법은 `PERFORMANCE.md`를 참고하세요.
