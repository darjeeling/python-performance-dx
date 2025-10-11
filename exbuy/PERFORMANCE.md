# 성능 최적화 가이드

ExBuy API의 성능 최적화 기법 및 설정 가이드입니다.

## 목차
- [Django ORM 최적화](#django-orm-최적화)
- [데이터베이스 최적화](#데이터베이스-최적화)
- [서버 설정 최적화](#서버-설정-최적화)
- [캐싱 전략](#캐싱-전략)
- [모니터링 및 프로파일링](#모니터링-및-프로파일링)

## Django ORM 최적화

### 1. N+1 쿼리 해결

**문제:**
```python
# ❌ N+1 쿼리 발생
products = Product.objects.all()
for product in products:
    reviews = product.reviews.all()  # 각 상품마다 추가 쿼리
```

**해결:**
```python
# ✅ prefetch_related 사용
products = Product.objects.prefetch_related('reviews').all()

# ✅ select_related (ForeignKey)
order_items = OrderItem.objects.select_related('product', 'order').all()
```

### 2. 필요한 필드만 조회

```python
# ❌ 모든 필드 조회
products = Product.objects.all()

# ✅ 필요한 필드만
products = Product.objects.values('id', 'name', 'price')

# ✅ 또는 only() 사용
products = Product.objects.only('id', 'name', 'price')
```

### 3. 집계 쿼리 최적화

```python
# ❌ Python에서 집계
orders = Order.objects.all()
total = sum(o.total_price for o in orders)

# ✅ DB에서 집계
from django.db.models import Sum
total = Order.objects.aggregate(total=Sum('total_price'))['total']
```

### 4. Bulk 연산

```python
# ❌ 반복문에서 save()
for item in items_data:
    OrderItem.objects.create(...)

# ✅ bulk_create 사용
order_items = [OrderItem(...) for item in items_data]
OrderItem.objects.bulk_create(order_items)
```

### 5. 조건부 업데이트 (F 객체)

```python
# ❌ 레이스 컨디션 가능
product = Product.objects.get(id=1)
product.stock -= quantity
product.save()

# ✅ 원자적 업데이트
Product.objects.filter(id=1).update(stock=F('stock') - quantity)
```

## 데이터베이스 최적화

### 1. 인덱스 전략

**복합 인덱스:**
```python
class Product(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['category', 'price']),  # 카테고리별 가격 필터링
            models.Index(fields=['updated_at', 'stock']),  # 최근 업데이트 + 재고
        ]
```

**인덱스 확인:**
```sql
-- PostgreSQL에서 인덱스 확인
\d+ shop_product

-- 인덱스 사용 여부 확인
EXPLAIN ANALYZE
SELECT * FROM shop_product WHERE category='electronics' AND price < 1000;
```

### 2. 연결 풀링 (CONN_MAX_AGE)

```python
# settings.py
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 600,  # 10분간 연결 재사용
    }
}
```

**효과:**
- 연결 생성 오버헤드 감소
- 높은 동시성 환경에서 성능 향상

### 3. PostgreSQL 튜닝

**docker-compose.yml:**
```yaml
db:
  command: >
    postgres
    -c shared_buffers=256MB        # 전체 메모리의 25%
    -c effective_cache_size=1GB    # 전체 메모리의 50-75%
    -c work_mem=16MB               # 정렬/조인 작업용
    -c maintenance_work_mem=64MB   # 인덱스 생성용
    -c checkpoint_completion_target=0.9
```

**효과:**
- 쿼리 플래닝 개선
- 캐시 히트율 증가
- 체크포인트 오버헤드 감소

### 4. 쿼리 분석

```bash
# Django 디버그 툴바 사용
pip install django-debug-toolbar

# 또는 로깅
# settings.py
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',  # SQL 쿼리 로깅
        },
    },
}
```

## 서버 설정 최적화

### 1. Worker 타입 선택

| 워크로드 | 추천 Worker | 이유 |
|---------|------------|------|
| 읽기 중심 (DB 쿼리 많음) | gevent | I/O 동시성 우수 |
| 쓰기 중심 (트랜잭션) | gthread | 안정적인 DB 처리 |
| CPU 집약적 | sync | 예측 가능한 성능 |
| 혼합 워크로드 | gthread | 균형잡힌 성능 |

**설정:**
```bash
# Gunicorn - gevent
gunicorn --workers 4 --worker-class gevent config.wsgi:application

# Gunicorn - gthread (threads)
gunicorn --workers 4 --worker-class gthread --threads 2 config.wsgi:application
```

### 2. Worker 수 최적화

**공식:** `workers = (2 x CPU cores) + 1`

```bash
# 4 코어 시스템
--workers 9

# 하지만 실제로는 4-8 사이로 조정
--workers 4  # 시작
--workers 8  # 부하 테스트 후 조정
```

### 3. 타임아웃 설정

```bash
# Gunicorn
--timeout 120  # 긴 쿼리 대응

# Uvicorn
--timeout-keep-alive 5  # Keep-alive 타임아웃
```

### 4. 리소스 제한

**docker-compose.yml:**
```yaml
web:
  deploy:
    resources:
      limits:
        cpus: '2'      # CPU 제한
        memory: 2G     # 메모리 제한
      reservations:
        cpus: '1'
        memory: 1G
```

## 캐싱 전략

### 1. Django 캐시 프레임워크

**Redis 캐시 설정:**
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 2. 뷰 레벨 캐싱

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15분 캐싱
@api_view(['GET'])
def product_list(request):
    ...
```

### 3. ORM 캐싱

```python
from django.core.cache import cache

def get_top_products():
    cache_key = 'top_products'
    products = cache.get(cache_key)

    if products is None:
        products = Product.objects.annotate(
            total_sales=Sum('order_items__quantity')
        ).order_by('-total_sales')[:10]
        cache.set(cache_key, products, 300)  # 5분

    return products
```

### 4. HTTP 캐싱

```python
from django.views.decorators.http import condition

@condition(etag_func=my_etag, last_modified_func=my_last_modified)
def product_detail(request, pk):
    ...
```

## 모니터링 및 프로파일링

### 1. Django Debug Toolbar

```python
# settings.py
INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

INTERNAL_IPS = ['127.0.0.1']
```

**확인 사항:**
- SQL 쿼리 수
- 쿼리 실행 시간
- 캐시 히트/미스
- 템플릿 렌더링 시간

### 2. Django Silk (프로파일링)

```bash
pip install django-silk

# settings.py
INSTALLED_APPS += ['silk']
MIDDLEWARE += ['silk.middleware.SilkyMiddleware']
```

**기능:**
- API 요청 프로파일링
- SQL 쿼리 분석
- 요청별 상세 타임라인

### 3. Prometheus 메트릭

```python
# django-prometheus가 자동 수집하는 메트릭
# - django_http_requests_total_by_method
# - django_http_requests_latency_seconds
# - django_db_query_duration_seconds
```

**Grafana 쿼리:**
```promql
# 평균 응답 시간
rate(django_http_requests_latency_seconds_sum[5m])
/
rate(django_http_requests_latency_seconds_count[5m])

# RPS
sum(rate(django_http_requests_total_by_method[1m])) by (method)
```

### 4. 슬로우 쿼리 로깅

```python
# settings.py
LOGGING = {
    'handlers': {
        'slow_queries': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'slow_queries.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['slow_queries'],
            'level': 'DEBUG',
            'filters': ['slow_query'],
        },
    },
    'filters': {
        'slow_query': {
            '()': 'path.to.SlowQueryFilter',
        },
    },
}
```

## 체크리스트

### 배포 전 확인사항

- [ ] DEBUG = False
- [ ] CONN_MAX_AGE 설정됨
- [ ] 인덱스 적용됨
- [ ] N+1 쿼리 해결
- [ ] select_related/prefetch_related 사용
- [ ] bulk_create 사용
- [ ] 적절한 worker 타입 선택
- [ ] 리소스 제한 설정
- [ ] 로깅 레벨 조정 (WARNING 이상)
- [ ] 모니터링 대시보드 설정

### 성능 테스트 체크리스트

- [ ] Warmup 실행
- [ ] 동일 환경에서 반복 테스트
- [ ] 리소스 모니터링 활성화
- [ ] 다양한 worker 타입 비교
- [ ] 최적화 on/off 비교
- [ ] 결과 저장 및 비교

## 추가 최적화

### 1. Read Replica
```python
DATABASES = {
    'default': {
        ...
    },
    'replica': {
        ...
        'OPTIONS': {'read_only': True}
    }
}

# 라우터 설정
DATABASE_ROUTERS = ['path.to.ReplicaRouter']
```

### 2. Connection Pooling (외부)
```bash
# pgBouncer 사용 (선택)
docker run -d pgbouncer/pgbouncer
```

### 3. CDN 및 정적 파일
```python
# settings.py
STATIC_URL = 'https://cdn.example.com/static/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

## 참고 자료

- [Django Performance Tips](https://docs.djangoproject.com/en/stable/topics/performance/)
- [PostgreSQL Performance](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Gunicorn Design](https://docs.gunicorn.org/en/stable/design.html)
