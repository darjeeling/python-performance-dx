# 성능 테스트 실행 가이드

ExBuy 성능 테스트를 위한 단계별 실행 가이드입니다.

## 목차
- [사전 준비](#사전-준비)
- [1단계: 환경 구성](#1단계-환경-구성)
- [2단계: 데이터 시딩](#2단계-데이터-시딩)
- [3단계: 서버 실행](#3단계-서버-실행)
- [4단계: 부하 테스트 실행](#4단계-부하-테스트-실행)
- [5단계: 결과 분석](#5단계-결과-분석)
- [문제 해결](#문제-해결)

## 사전 준비

### 필수 소프트웨어
- Docker & Docker Compose
- K6 (부하 테스트 도구)
- 최소 사양: 4GB RAM, 4 CPU cores

### K6 설치 (Ubuntu/Debian)
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

## 1단계: 환경 구성

### 1.1 모니터링 네트워크 생성
```bash
# monitoring 스택이 있다면 해당 네트워크를 사용
# 없다면 수동으로 생성
docker network create monitoring-network
```

### 1.2 환경 변수 설정 (선택)
```bash
# 리눅스 테스트용 환경 변수 사용
cp .env.linux .env

# 또는 수동으로 설정
export DB_CONN_MAX_AGE=600
export WORKERS=4
```

## 2단계: 데이터 시딩

### 2.1 DB 및 기본 서비스 시작
```bash
# DB만 먼저 시작
docker compose up -d db

# DB가 준비될 때까지 대기
docker compose exec db pg_isready -U postgres
```

### 2.2 마이그레이션 실행
```bash
# 임시 컨테이너로 마이그레이션
docker compose run --rm web-gunicorn-sync python manage.py migrate
```

### 2.3 데이터 생성
```bash
# 소규모 테스트 (1K products, 5K orders, 10K reviews)
docker compose run --rm web-gunicorn-sync python manage.py seed_data \
    --products 1000 \
    --orders 5000 \
    --reviews 10000

# 중규모 테스트 (10K products, 50K orders, 100K reviews)
docker compose run --rm web-gunicorn-sync python manage.py seed_data \
    --products 10000 \
    --orders 50000 \
    --reviews 100000

# 대규모 테스트 (100K products, 500K orders, 1M reviews)
docker compose run --rm web-gunicorn-sync python manage.py seed_data \
    --products 100000 \
    --orders 500000 \
    --reviews 1000000 \
    --batch-size 5000
```

## 3단계: 서버 실행

### 3.1 서버 타입별 실행

#### Gunicorn - sync worker
```bash
docker compose --profile gunicorn-sync up -d
# 포트: 8000
```

#### Gunicorn - gevent worker
```bash
docker compose --profile gunicorn-gevent up -d
# 포트: 8001
```

#### Gunicorn - gthread worker
```bash
docker compose --profile gunicorn-gthread up -d
# 포트: 8002
```

#### Uvicorn (ASGI)
```bash
docker compose --profile uvicorn up -d
# 포트: 8003
```

#### 모든 서버 동시 실행 (비교 테스트)
```bash
docker compose --profile gunicorn-sync --profile gunicorn-gevent --profile gunicorn-gthread --profile uvicorn up -d
```

### 3.2 서비스 상태 확인
```bash
# 컨테이너 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f web-gunicorn-sync

# 헬스체크
curl http://localhost:8000/api/health
```

## 4단계: 부하 테스트 실행

### 4.1 Warmup (캐시 워밍업)
```bash
# 데이터베이스 및 애플리케이션 캐시 워밍업
./warmup.sh
```

### 4.2 테스트 시나리오 실행

#### 읽기 중심 테스트 (80% 읽기, 20% 쓰기)
```bash
# Gunicorn sync
BASE_URL=http://localhost:8000 k6 run k6-scripts/read-heavy.js

# Uvicorn
BASE_URL=http://localhost:8003 k6 run k6-scripts/read-heavy.js
```

#### 쓰기 중심 테스트 (30% 읽기, 70% 쓰기)
```bash
BASE_URL=http://localhost:8000 k6 run k6-scripts/write-heavy.js
```

#### 혼합 테스트 (60% 읽기, 40% 쓰기)
```bash
BASE_URL=http://localhost:8000 k6 run k6-scripts/mixed.js
```

### 4.3 결과 저장
```bash
# JSON 형식으로 저장
BASE_URL=http://localhost:8000 k6 run --out json=results/gunicorn-sync-read.json k6-scripts/read-heavy.js

# HTML 리포트 생성 (k6-reporter 필요)
BASE_URL=http://localhost:8000 k6 run --out json=results/test.json k6-scripts/mixed.js
```

### 4.4 Makefile을 사용한 자동화
```bash
# 특정 서버의 모든 시나리오 테스트
make test-gunicorn-sync

# 특정 시나리오만 테스트
make test-read-heavy SERVER=gunicorn-sync

# 모든 서버 비교 테스트
make test-all
```

## 5단계: 결과 분석

### 5.1 K6 메트릭 이해

**주요 메트릭:**
- `http_req_duration`: 요청 지연 시간
  - `p(95)`: 95% 요청이 이 값 이하
  - `p(99)`: 99% 요청이 이 값 이하
- `http_req_failed`: 실패율
- `http_reqs`: 초당 요청 수 (RPS)

**임계값:**
- Read-heavy: p95 < 500ms, p99 < 1000ms
- Write-heavy: p95 < 1000ms, p99 < 2000ms
- Mixed: p95 < 800ms, p99 < 1500ms

### 5.2 Prometheus 메트릭 확인
```bash
# Django 메트릭 확인
curl http://localhost:8000/metrics

# 주요 메트릭
# - django_http_requests_latency_seconds
# - django_db_query_duration_seconds
# - django_http_requests_total_by_method
```

### 5.3 Grafana 대시보드
```
http://localhost:3000
- Dashboard: "ExBuy Performance"
- 실시간 RPS, 지연시간, 에러율 확인
```

### 5.4 로그 분석
```bash
# 에러 로그 확인
docker compose logs web-gunicorn-sync | grep ERROR

# SQL 쿼리 로그 (DB_LOG_LEVEL=DEBUG 설정 필요)
docker compose logs web-gunicorn-sync | grep "SELECT\|INSERT\|UPDATE"
```

## 6단계: 테스트 간 초기화

### 6.1 데이터 리셋
```bash
# 재고 및 주문 상태 초기화
./reset-test.sh

# 또는 전체 데이터 재생성
docker compose run --rm web-gunicorn-sync python manage.py seed_data --products 10000
```

### 6.2 서버 재시작
```bash
# 특정 서버만 재시작
docker compose restart web-gunicorn-sync

# 모든 서버 재시작
docker compose restart
```

## 문제 해결

### DB 연결 오류
```bash
# DB 상태 확인
docker compose exec db pg_isready -U postgres

# DB 로그 확인
docker compose logs db

# DB 재시작
docker compose restart db
```

### 메모리 부족
```bash
# 리소스 사용량 확인
docker stats

# 불필요한 컨테이너 정리
docker compose down
docker system prune -a
```

### 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tlnp | grep :8000

# docker-compose.yml에서 포트 변경
```

### 네트워크 오류
```bash
# monitoring-network 확인
docker network ls
docker network inspect monitoring-network

# 네트워크 재생성
docker network rm monitoring-network
docker network create monitoring-network
```

### K6 타임아웃
```bash
# k6-scripts에서 timeout 증가
export const options = {
  ...
  timeout: '5m',
}
```

## 고급 테스트

### CPU 고정 (성능 일관성)
```bash
# 특정 CPU 코어에 컨테이너 고정
docker compose run --cpuset-cpus="0,1" web-gunicorn-sync
```

### 동시성 레벨 조정
```bash
# k6 VU(Virtual Users) 조정
k6 run --vus 100 --duration 5m k6-scripts/mixed.js
```

### 데이터베이스 인덱스 테스트
```bash
# 인덱스 없이 테스트
docker compose exec db psql -U postgres -d exbuy -c "DROP INDEX ..."

# 테스트 실행

# 인덱스 재생성
docker compose exec db psql -U postgres -d exbuy -c "CREATE INDEX ..."
```

## 다음 단계

테스트 결과를 바탕으로:
1. `BENCHMARKS.md`: 서버별 성능 비교
2. `PERFORMANCE.md`: 최적화 가이드 참고
3. Grafana 대시보드로 실시간 모니터링
