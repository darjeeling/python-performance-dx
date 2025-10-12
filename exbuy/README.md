# ExBuy - Django/DRF 성능 테스트용 커머스 API

성능 테스트를 위한 전형적인 커머스 축소판 API 서버입니다. 다양한 복잡도의 엔드포인트와 최적화 옵션을 제공하여 Django/DRF의 성능을 측정하고 비교할 수 있습니다.

## 목차
- [특징](#특징)
- [아키텍처](#아키텍처)
- [API 엔드포인트](#api-엔드포인트)
- [빠른 시작](#빠른-시작)
- [성능 최적화 옵션](#성능-최적화-옵션)
- [부하 테스트](#부하-테스트)
- [모니터링](#모니터링)

## 특징

### 도메인 모델
- **Product**: 상품 (name, price, stock, category)
- **Order**: 주문 (user_id, status, total_price)
- **OrderItem**: 주문 아이템 (order, product, quantity, unit_price)
- **Review**: 리뷰 (product, user_id, rating, body)

### 15개 API 엔드포인트
1. `GET /api/health` - 헬스체크 (Level A)
2. `GET /api/products` - 상품 목록 (Level B)
3. `GET /api/products/{id}` - 상품 상세 (Level A)
4. `GET /api/products/{id}/reviews` - 상품별 리뷰 (Level B)
5. `GET /api/search/products` - 상품 검색 (Level B)
6. `POST /api/orders` - 주문 생성 (Level C)
7. `GET /api/orders/{id}` - 주문 상세 (Level B)
8. `PATCH /api/orders/{id}` - 주문 상태 업데이트 (Level A)
9. `POST /api/orders/bulk` - 벌크 주문 생성 (Level C)
10. `POST /api/inventory/reserve` - 재고 예약 (Level C)
11. `GET /api/stats/top-products` - 인기 상품 통계 (Level C)
12. `POST /api/reviews` - 리뷰 생성 (Level A)
13. `GET /api/reviews` - 리뷰 목록 (Level B)
14. `POST /api/uploads` - 파일 업로드 (Level A-B)
15. `DELETE /api/products/{id}` - 상품 삭제 (Level A)

**복잡도 레벨:**
- **Level A**: 단순 CRUD (PK 조회, 간단한 업데이트)
- **Level B**: 필터링/정렬/페이지네이션, 1-2개 조인
- **Level C**: 트랜잭션, 벌크 연산, 집계 쿼리, 동시성 제어

## 아키텍처

```
exbuy/
├── config/              # Django 설정
│   ├── settings.py     # DB, DRF, Prometheus 설정
│   └── urls.py
├── shop/               # 메인 앱
│   ├── models.py       # 도메인 모델
│   ├── serializers.py  # DRF Serializers
│   ├── views.py        # API Views
│   ├── urls.py         # URL 라우팅
│   └── management/
│       └── commands/
│           └── seed_data.py  # 데이터 시딩
├── k6-scripts/         # 부하 테스트 스크립트
│   ├── read-heavy.js   # 읽기 중심 (80% 읽기)
│   ├── write-heavy.js  # 쓰기 중심 (70% 쓰기)
│   └── mixed.js        # 혼합 (60% 읽기, 40% 쓰기)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API 엔드포인트

### 1. 헬스체크
```bash
GET /api/health
```

### 2. 상품 API
```bash
# 목록 조회 (필터링, 정렬, 페이지네이션)
GET /api/products?category=electronics&min_price=100&max_price=1000&ordering=-price&page=1

# 최적화 옵션
GET /api/products/{id}?optimize=true  # prefetch_related 적용

# 검색
GET /api/search/products?q=laptop&category=electronics&in_stock=true

# 상품별 리뷰
GET /api/products/{id}/reviews?optimize=true  # select_related 적용
```

### 3. 주문 API
```bash
# 주문 생성
POST /api/orders
{
  "user_id": 1,
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 5, "quantity": 1}
  ]
}

# 주문 상세
GET /api/orders/{id}?optimize=true  # prefetch items__product

# 상태 업데이트
PATCH /api/orders/{id}
{
  "status": "shipped"
}

# 벌크 생성
POST /api/orders/bulk
{
  "orders": [
    {"user_id": 1, "items": [...]},
    {"user_id": 2, "items": [...]}
  ]
}
```

### 4. 재고 관리
```bash
# 재고 예약 (동시성 제어)
POST /api/inventory/reserve?lock_type=optimistic|pessimistic
{
  "product_id": 1,
  "quantity": 5
}
```

### 5. 통계
```bash
# 인기 상품 TOP N
GET /api/stats/top-products?limit=10
```

### 6. 리뷰 API
```bash
# 리뷰 생성
POST /api/reviews
{
  "product": 1,
  "user_id": 100,
  "rating": 5,
  "body": "Great product!"
}

# 리뷰 목록
GET /api/reviews?product_id=1&optimize=true
```

## 빠른 시작

### 1. Makefile을 사용한 자동 설정 (추천)

```bash
cd exbuy

# 전체 자동 설정 (빌드 → DB 시작 → 마이그레이션 → 시딩 → 서버 시작)
make quickstart

# 개별 명령어
make build              # 이미지 빌드
make up                 # DB 시작
make migrate            # 마이그레이션
make seed-medium        # 데이터 시딩 (10K/50K/100K)
make up-sync WORKERS=8  # Gunicorn sync 서버 시작 (WORKERS 지정)

# 서버 전환
make switch TO=gevent WORKERS=8

# 상태 확인
make status
make check-health

# 전체 명령어 목록
make help
```

### 2. Docker Compose로 직접 실행

```bash
cd exbuy

# 빌드
docker compose build

# 실행 (WORKERS 환경변수 지정 가능)
WORKERS=8 docker compose --profile gunicorn-sync up -d

# 로그 확인
docker compose logs -f web-gunicorn-sync

# Django 관리 명령 실행
docker compose run --rm web-gunicorn-sync python manage.py migrate
docker compose run --rm web-gunicorn-sync python manage.py seed_data --products 10000

# 서비스 종료
docker compose down
```

### 3. 로컬 개발 환경

```bash
cd exbuy

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# PostgreSQL 준비 (Docker 또는 로컬)
docker run -d --name exbuy-db \
  -e POSTGRES_DB=exbuy \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16-alpine

# 환경 변수 설정
export DB_HOST=localhost
export DB_NAME=exbuy
export DB_USER=postgres
export DB_PASSWORD=postgres

# 마이그레이션
python manage.py migrate

# 데이터 시딩
python manage.py seed_data --products 1000 --orders 5000 --reviews 10000

# 개발 서버 실행
python manage.py runserver
```

### 4. Gunicorn/Uvicorn으로 실행

```bash
# Gunicorn (WSGI)
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Uvicorn (ASGI)
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4

# Docker Compose로 Uvicorn 실행
docker compose --profile uvicorn up -d web-uvicorn
```

## 성능 최적화 옵션

### 쿼리 최적화
API에 `?optimize=true` 파라미터를 추가하면 최적화된 쿼리를 사용합니다.

```bash
# 최적화 전 (N+1 쿼리 발생)
GET /api/products/1

# 최적화 후 (prefetch_related 적용)
GET /api/products/1?optimize=true
```

**최적화 내용:**
- `select_related()`: ForeignKey 조인
- `prefetch_related()`: ManyToMany, Reverse ForeignKey
- `.values()` / `.values_list()`: 직렬화 성능 향상

### 동시성 제어 비교
```bash
# 낙관적 락 (F() 객체 사용)
POST /api/inventory/reserve?lock_type=optimistic

# 비관적 락 (SELECT FOR UPDATE)
POST /api/inventory/reserve?lock_type=pessimistic
```

## 부하 테스트

### Makefile을 사용한 테스트 (추천)

```bash
# 기본 테스트
make test-mixed              # 혼합 테스트 (60% 읽기, 40% 쓰기)
make test-read-heavy         # 읽기 중심 (80% 읽기)
make test-write-heavy        # 쓰기 중심 (70% 쓰기)
make test-read-only          # 순수 읽기 (100% 읽기)

# 파라미터 커스터마이징
make test-mixed MAX_VU=300 DURATION=10m
make test-read-only SERVER=uvicorn MAX_VU=500 DURATION=15m

# 빠른 벤치마크 (1분)
make benchmark SERVER=sync MAX_VU=200

# 서버별 전체 테스트 (워밍업 + 3개 시나리오)
make test-gunicorn-sync
make test-gunicorn-gevent

# 결과 비교
make compare-results
make show-history
```

**사용 가능한 파라미터:**
- `SERVER`: gunicorn-sync, gunicorn-gevent, gunicorn-gthread, uvicorn
- `WORKERS`: Worker 프로세스 수 (기본: 4)
- `MAX_VU`: Virtual Users (기본: 200)
- `DURATION`: 테스트 지속 시간 (기본: 5m)
- `RAMP_UP/RAMP_DOWN`: 램프업/다운 시간 (기본: 30s)

### K6 직접 실행

```bash
cd exbuy

# 환경변수로 파라미터 지정
MAX_VU=300 DURATION=10m SERVER_TYPE=gunicorn-sync k6 run k6-scripts/mixed.js

# BASE_URL 지정
BASE_URL=http://localhost:9001 k6 run k6-scripts/read-heavy.js
```

### 테스트 이력 및 결과 분석

모든 테스트는 자동으로 `results/test-history.jsonl`에 기록됩니다:
- 타임스탬프
- 서버 타입
- 시나리오
- VU/Duration/Workers

```bash
# 테스트 이력 조회
make show-history

# 결과 비교
make compare-results

# Grafana에서 확인 (타임라인에 테스트 마커 표시)
open http://localhost:3000
```

## 모니터링

### Prometheus 메트릭

Django-Prometheus가 자동으로 메트릭을 수집합니다:

```bash
# 메트릭 확인
curl http://localhost:8000/metrics
```

**주요 메트릭:**
- `django_http_requests_total_by_method_total`
- `django_http_requests_latency_seconds`
- `django_db_query_duration_seconds`

### 로그 레벨 설정

```bash
# 환경 변수로 설정
LOG_LEVEL=DEBUG
DJANGO_LOG_LEVEL=INFO
DB_LOG_LEVEL=DEBUG  # SQL 쿼리 로그

docker compose up -d
```

### DB 쿼리 분석

```python
# settings.py에서 활성화
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',  # SQL 쿼리 출력
        },
    },
}
```

## 데이터 시딩 옵션

```bash
# 기본 (10K products, 50K orders, 100K reviews)
python manage.py seed_data

# 소규모 테스트
python manage.py seed_data --products 100 --orders 500 --reviews 1000

# 대규모 부하 테스트
python manage.py seed_data --products 100000 --orders 500000 --reviews 1000000

# 배치 크기 조정
python manage.py seed_data --batch-size 5000
```

## 환경 변수

### 서버 설정

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DEBUG` | `True` | 디버그 모드 |
| `DB_HOST` | `localhost` | PostgreSQL 호스트 |
| `DB_NAME` | `exbuy` | 데이터베이스 이름 |
| `DB_USER` | `postgres` | DB 사용자 |
| `DB_PASSWORD` | `postgres` | DB 비밀번호 |
| `DB_PORT` | `5432` | DB 포트 |
| `SERVER_TYPE` | `gunicorn` | 서버 타입 (gunicorn/uvicorn) |
| `WORKERS` | `4` | Worker 프로세스 수 (동적 변경 가능) |
| `WORKER_CLASS` | `sync` | Gunicorn worker 클래스 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |

### 테스트 파라미터 (.env.test)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MAX_VU` | `200` | K6 Virtual Users |
| `DURATION` | `5m` | 테스트 지속 시간 |
| `RAMP_UP` | `30s` | 램프업 시간 |
| `RAMP_DOWN` | `30s` | 램프다운 시간 |

**사용 예시:**
```bash
# Makefile에서 동적 설정
make up-sync WORKERS=8
make test-mixed MAX_VU=300 DURATION=10m

# 환경변수로 직접 설정
WORKERS=16 docker compose --profile uvicorn up -d
```

## 성능 테스트 시나리오

### 1. WORKERS 비교 테스트
```bash
# 4 workers
make switch TO=sync WORKERS=4
make warmup
make test-mixed

# 8 workers
make switch TO=sync WORKERS=8
make warmup
make test-mixed

# 결과 비교
make compare-results
```

### 2. 서버별 성능 비교
```bash
# 모든 서버 시작
make up-all WORKERS=8

# 순차 테스트
make test-gunicorn-sync
make reset
make test-gunicorn-gevent
make reset
make test-uvicorn

# 결과 확인
make compare-results
make show-history
```

### 3. VU 증가 테스트
```bash
make up-sync WORKERS=8

for VU in 100 200 300 400 500; do
  make test-read-only MAX_VU=$VU DURATION=3m
  sleep 30
done

make compare-results
```

더 많은 시나리오는 [TESTING.md](TESTING.md) 참고

## 문제 해결

### PostgreSQL 연결 오류
```bash
# DB 컨테이너 상태 확인
docker compose ps
docker compose logs db

# 수동 연결 테스트
psql -h localhost -U postgres -d exbuy
```

### 마이그레이션 오류
```bash
# 모델 변경사항 확인
docker compose run --rm web-gunicorn-sync python manage.py makemigrations --dry-run

# 마이그레이션 파일 생성
docker compose run --rm web-gunicorn-sync python manage.py makemigrations

# 마이그레이션 적용
docker compose run --rm web-gunicorn-sync python manage.py migrate

# 또는 실행 중인 컨테이너에서
docker compose exec web-gunicorn-sync python manage.py makemigrations
docker compose exec web-gunicorn-sync python manage.py migrate

# 마이그레이션 초기화 (필요한 경우)
docker compose run --rm web-gunicorn-sync python manage.py migrate --run-syncdb
```

**참고:** `docker compose run`을 사용하면 전달된 명령이 실행되고, `docker compose up`이나 `docker compose exec`를 사용하면 기본 entrypoint(migrate + 서버 시작)가 실행됩니다.

## 라이선스

MIT License

## 기여

이슈와 PR을 환영합니다!
