# Linux 성능 테스트 환경 설정 가이드

리눅스 서버에서 ExBuy 성능 테스트를 실행하기 위한 설정 가이드입니다.

## 사전 준비

### 1. 스크립트 실행 권한 설정
```bash
chmod +x warmup.sh reset-test.sh run-tests.sh
```

### 2. 모니터링 네트워크 생성
```bash
# monitoring 스택과 연동하려면
docker network create monitoring-network

# 또는 기존 모니터링 스택의 네트워크 확인
docker network ls | grep monitoring
```

### 3. 환경 변수 설정
```bash
# .env.linux 파일 복사
cp .env.linux .env

# 필요시 수정
vi .env
```

## 빠른 시작

### Makefile 사용 (권장)
```bash
# 1. 전체 환경 구성
make quickstart

# 2. 테스트 실행
make test-read-heavy
make test-mixed

# 3. 모든 서버 비교
make test-all
```

### 수동 실행
```bash
# 1. 빌드
docker compose build

# 2. DB 시작
docker compose up -d db

# 3. 마이그레이션
docker compose run --rm web-gunicorn-sync python manage.py migrate

# 4. 데이터 시딩
docker compose run --rm web-gunicorn-sync python manage.py seed_data

# 5. 서버 시작 (원하는 타입 선택)
docker compose --profile gunicorn-sync up -d     # 포트 9000
docker compose --profile gunicorn-gevent up -d   # 포트 9001
docker compose --profile gunicorn-gthread up -d  # 포트 9002
docker compose --profile uvicorn up -d           # 포트 9003

# 6. 워밍업
./warmup.sh

# 7. K6 테스트
BASE_URL=http://localhost:9000 k6 run k6-scripts/read-heavy.js
```

## 서버 구성 비교

### 포트 매핑
| 서버 타입 | Worker 클래스 | 포트 | Profile |
|----------|--------------|------|---------|
| Gunicorn | sync | 9000 | `gunicorn-sync` |
| Gunicorn | gevent | 9001 | `gunicorn-gevent` |
| Gunicorn | gthread | 9002 | `gunicorn-gthread` |
| Uvicorn | ASGI | 9003 | `uvicorn` |

### 리소스 제한
각 서비스는 다음과 같이 리소스가 제한됩니다:
- CPU: 2 cores (limit), 1 core (reservation)
- Memory: 2GB (limit), 1GB (reservation)
- DB: 2 cores, 1GB

### 네트워크 분리
- `app-network` (172.20.0.0/16): DB ↔ Web 통신
- `monitoring-network` (external): Prometheus/Grafana 메트릭 수집

## 테스트 시나리오

### 1. 서버 타입별 성능 비교
```bash
# 모든 서버 시작
make up-all

# 각 서버 테스트
make test-gunicorn-sync
make test-gunicorn-gevent
make test-gunicorn-gthread
make test-uvicorn

# 결과 비교
make compare
```

### 2. 최적화 효과 측정
```bash
# 최적화 없음
curl http://localhost:9000/api/products/1

# 최적화 적용
curl http://localhost:9000/api/products/1?optimize=true

# K6로 비교 테스트
BASE_URL=http://localhost:9000 k6 run k6-scripts/read-heavy.js
```

### 3. 동시성 제어 비교
```bash
# 낙관적 락
curl -X POST http://localhost:9000/api/inventory/reserve?lock_type=optimistic \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}'

# 비관적 락
curl -X POST http://localhost:9000/api/inventory/reserve?lock_type=pessimistic \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}'
```

## 모니터링

### Prometheus 메트릭
```bash
# 메트릭 확인
curl http://localhost:9000/metrics

# 주요 메트릭
# - django_http_requests_latency_seconds
# - django_db_query_duration_seconds
# - django_http_requests_total_by_method
```

### Grafana 대시보드 임포트
```bash
# 1. Grafana 접속 (http://localhost:3000)
# 2. Configuration > Data Sources > VictoriaMetrics 설정 확인
# 3. Dashboards > Import
# 4. grafana-dashboards/exbuy-performance.json 업로드
```

### 로그 분석
```bash
# 에러 로그
docker compose logs web-gunicorn-sync | grep ERROR

# SQL 쿼리 로그 (DB_LOG_LEVEL=DEBUG 필요)
docker compose logs web-gunicorn-sync | grep "SELECT\|INSERT\|UPDATE"

# 슬로우 쿼리 찾기
docker compose logs web-gunicorn-sync | grep -A 5 "slow"
```

## 트러블슈팅

### 1. 네트워크 연결 실패
```bash
# 네트워크 확인
docker network inspect monitoring-network

# 네트워크가 없다면 생성
docker network create monitoring-network

# 서비스 재시작
docker compose down
docker compose --profile gunicorn-sync up -d
```

### 2. 포트 충돌
```bash
# 사용 중인 포트 확인
sudo netstat -tlnp | grep :9000

# docker-compose.yml에서 포트 변경
# ports:
#   - "9010:8000"  # 9010으로 변경
```

### 3. 메모리 부족
```bash
# 리소스 사용량 확인
docker stats

# 데이터 규모 줄이기
make seed-small  # 1K products instead of 10K

# 또는 리소스 제한 조정 (docker-compose.yml)
```

### 4. K6 실행 실패
```bash
# K6 버전 확인
k6 version

# 최신 버전 설치
sudo apt-get update && sudo apt-get install k6

# 타임아웃 증가
k6 run --http-debug k6-scripts/mixed.js
```

## 성능 최적화 체크리스트

### 배포 전
- [ ] `DEBUG=False` 설정
- [ ] `CONN_MAX_AGE=600` 설정
- [ ] PostgreSQL 튜닝 적용 (docker-compose.yml)
- [ ] 모든 인덱스 생성됨 (migrations)
- [ ] select_related/prefetch_related 적용
- [ ] 로그 레벨 WARNING 이상

### 테스트 전
- [ ] DB 및 서버 재시작
- [ ] warmup.sh 실행
- [ ] 리소스 모니터링 활성화
- [ ] 결과 저장 디렉터리 생성 (`mkdir results`)

### 테스트 후
- [ ] 결과 파일 백업
- [ ] 다음 테스트 전 reset-test.sh 실행
- [ ] Grafana 스크린샷 저장
- [ ] 로그 파일 분석

## 문서 참고

- **TESTING.md**: 상세 테스트 실행 가이드
- **BENCHMARKS.md**: 시나리오별 기대값 및 비교 방법
- **PERFORMANCE.md**: 최적화 기법 및 설정
- **README.md**: 프로젝트 개요 및 API 문서

## 유용한 명령어

```bash
# 헬스 체크
make check-health

# 리소스 모니터링
make stats

# Django shell
make shell

# DB shell
make dbshell

# 로그 실시간 확인
make logs

# 전체 정리
make clean
```

## 다음 단계

1. **기본 성능 측정**: `make test-read-heavy`
2. **서버 비교**: `make test-all`
3. **최적화 적용**: `?optimize=true` 파라미터 추가
4. **결과 분석**: Grafana 대시보드 및 K6 리포트 확인
5. **튜닝**: PERFORMANCE.md 참고하여 개선

## 지원

문제 발생 시:
1. `docker compose logs` 확인
2. `make check-health` 실행
3. TESTING.md의 문제 해결 섹션 참고
