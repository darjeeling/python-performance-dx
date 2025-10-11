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

### 1. Docker Compose로 실행

```bash
cd exbuy

# 빌드 및 실행
docker compose up -d

# 로그 확인
docker compose logs -f web

# 마이그레이션 (자동 실행됨)
docker compose exec web python manage.py migrate

# 데이터 시딩
docker compose exec web python manage.py seed_data --products 10000 --orders 50000 --reviews 100000

# 서비스 중지
docker compose down
```

### 2. 로컬 개발 환경

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

### 3. Gunicorn/Uvicorn으로 실행

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

### K6 스크립트 실행

```bash
cd exbuy

# 읽기 중심 테스트 (80% 읽기, 20% 쓰기)
k6 run k6-scripts/read-heavy.js

# 쓰기 중심 테스트 (30% 읽기, 70% 쓰기)
k6 run k6-scripts/write-heavy.js

# 혼합 테스트 (60% 읽기, 40% 쓰기)
k6 run k6-scripts/mixed.js

# BASE_URL 지정
BASE_URL=http://localhost:8001 k6 run k6-scripts/mixed.js
```

### 시나리오 커스터마이징

`k6-scripts/*.js` 파일에서 다음을 수정할 수 있습니다:
- `options.stages`: 부하 증가 패턴
- `options.thresholds`: 성능 임계값
- 엔드포인트 호출 비율

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

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DEBUG` | `True` | 디버그 모드 |
| `DB_HOST` | `localhost` | PostgreSQL 호스트 |
| `DB_NAME` | `exbuy` | 데이터베이스 이름 |
| `DB_USER` | `postgres` | DB 사용자 |
| `DB_PASSWORD` | `postgres` | DB 비밀번호 |
| `DB_PORT` | `5432` | DB 포트 |
| `SERVER_TYPE` | `gunicorn` | 서버 타입 (gunicorn/uvicorn) |
| `WORKERS` | `4` | Worker 프로세스 수 |
| `WORKER_CLASS` | `sync` | Gunicorn worker 클래스 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |

## 성능 테스트 시나리오

### 1. 읽기 성능 비교
```bash
# 최적화 전
ab -n 1000 -c 10 http://localhost:8000/api/products/1

# 최적화 후
ab -n 1000 -c 10 http://localhost:8000/api/products/1?optimize=true
```

### 2. 동시성 테스트
```bash
# 동시 주문 생성
k6 run --vus 50 --duration 30s k6-scripts/write-heavy.js
```

### 3. 서버 비교
```bash
# Gunicorn vs Uvicorn
k6 run -e BASE_URL=http://localhost:8000 k6-scripts/mixed.js  # Gunicorn
k6 run -e BASE_URL=http://localhost:8001 k6-scripts/mixed.js  # Uvicorn
```

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
# 마이그레이션 초기화
docker compose exec web python manage.py migrate --run-syncdb

# 마이그레이션 재생성
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

## 라이선스

MIT License

## 기여

이슈와 PR을 환영합니다!
