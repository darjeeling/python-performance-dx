# Python Performance DX (Developer Experience)

Django/DRF 웹 애플리케이션의 성능 테스트와 모니터링을 위한 통합 환경입니다. 다양한 WSGI/ASGI 서버 구성을 비교하고, 실시간 메트릭과 로그를 수집하여 성능 최적화를 지원합니다.

## 📋 목차
- [프로젝트 개요](#프로젝트-개요)
- [아키텍처](#아키텍처)
- [주요 기능](#주요-기능)
- [빠른 시작](#빠른-시작)
- [모니터링 셋업](#모니터링-셋업)
- [사용 시나리오](#사용-시나리오)
- [디렉터리 구조](#디렉터리-구조)

---

## 프로젝트 개요

### 🎯 프로젝트 의도

이 프로젝트는 다음 목표를 위해 만들어졌습니다:

1. **성능 비교 실험장**
   - Gunicorn (sync/gevent/gthread) vs Uvicorn 성능 비교
   - Worker 수, VU(Virtual Users) 변화에 따른 성능 측정
   - 쿼리 최적화(select_related, prefetch_related) 효과 검증

2. **모니터링 Best Practices**
   - 메트릭(VictoriaMetrics) + 로그(Loki) 통합 모니터링
   - K6 부하 테스트 결과를 Grafana 타임라인에 자동 표시
   - 테스트 실행 이력 추적 및 결과 비교

3. **개발자 경험(DX) 향상**
   - Makefile 기반 명령어로 복잡한 설정을 단순화
   - 파라미터 기반 동적 설정 (WORKERS, MAX_VU 등)
   - 일관된 테스트 환경과 재현 가능한 결과

### 🏗️ 구성 요소

```
python-performance-dx/
├── exbuy/              # Django/DRF 커머스 API (성능 테스트 대상)
├── monitoring/         # VictoriaMetrics + Loki + Grafana 모니터링 스택
└── README.md           # 이 파일
```

---

## 아키텍처

### 전체 시스템 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Performance DX                    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   ExBuy API   │    │  Monitoring   │    │  K6 Load Test │
│               │    │               │    │               │
│ • Django/DRF  │───▶│ • Victoria    │◀───│ • Scenarios   │
│ • 4 Servers:  │    │   Metrics     │    │ • Test        │
│   - sync      │    │ • Loki        │    │   History     │
│   - gevent    │    │ • Grafana     │    │ • Markers     │
│   - gthread   │    │ • cAdvisor    │    │               │
│   - uvicorn   │    │               │    │               │
│               │    │               │    │               │
│ • PostgreSQL  │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 데이터 플로우

1. **메트릭 수집**
   ```
   Django/DRF (django-prometheus)
      └─▶ VictoriaMetrics (port 8428)
             └─▶ Grafana Dashboard

   K6 (Prometheus Remote Write)
      └─▶ VictoriaMetrics
             └─▶ Grafana Timeline (with annotations)

   cAdvisor (Container metrics)
      └─▶ VictoriaMetrics
   ```

2. **로그 수집**
   ```
   Docker Containers
      └─▶ Promtail
             └─▶ Loki (port 3100)
                    └─▶ Grafana Logs Explorer

   K6 Logs (file output)
      └─▶ Promtail
             └─▶ Loki
   ```

3. **테스트 이력**
   ```
   Makefile (test commands)
      └─▶ results/test-history.jsonl
             └─▶ Human-readable format

   K6 (setup/teardown markers)
      └─▶ VictoriaMetrics
             └─▶ Grafana Annotations
   ```

---

## 주요 기능

### 🚀 ExBuy 애플리케이션

- **15개 API 엔드포인트**: 헬스체크부터 복잡한 트랜잭션까지
- **4가지 서버 구성**: Gunicorn (sync/gevent/gthread), Uvicorn
- **동적 WORKERS 설정**: 환경변수로 Worker 수 변경 가능
- **쿼리 최적화 옵션**: `?optimize=true` 파라미터로 N+1 문제 해결
- **Profile 기반 관리**: Docker Compose profile로 서버별 독립 실행

### 📊 모니터링 스택

- **VictoriaMetrics**: PromQL 호환 메트릭 저장소 (Prometheus 대비 효율적)
- **Loki**: 로그 집계 및 검색 (LogQL 쿼리)
- **Grafana**: 통합 대시보드 (메트릭 + 로그)
- **cAdvisor**: 컨테이너 리소스 모니터링
- **K6 통합**: 테스트 시작/종료 이벤트를 타임라인에 자동 표시

### 🧪 테스트 시스템

- **Makefile 기반 명령어**: 50+ 명령어로 복잡한 작업 단순화
- **파라미터 커스터마이징**: `WORKERS`, `MAX_VU`, `DURATION` 등 동적 설정
- **테스트 이력 추적**: JSONL 형식으로 모든 테스트 메타데이터 기록
- **결과 비교 도구**: `compare-results.sh`로 서버별 성능 비교
- **서버 전환**: `make switch TO=gevent WORKERS=8` 한 줄로 전환

---

## 빠른 시작

### 1. 모니터링 스택 시작

```bash
cd monitoring

# 초기 설정 (최초 1회)
./setup.sh

# 모니터링 스택 시작
docker compose up -d

# 상태 확인
docker compose ps
```

**접속 URL:**
- Grafana: http://localhost:3000 (admin/admin)
- VictoriaMetrics: http://localhost:8428
- Loki: http://localhost:3100

### 2. ExBuy 애플리케이션 시작

```bash
cd exbuy

# 전체 자동 설정 (빌드 → DB → 마이그레이션 → 시딩 → 서버 시작)
make quickstart

# 또는 개별 실행
make build
make up
make migrate
make seed-medium        # 10K products, 50K orders, 100K reviews
make up-sync WORKERS=8  # Gunicorn sync 서버 (8 workers)

# 상태 확인
make status
make check-health
```

### 3. 부하 테스트 실행

```bash
# 기본 테스트
make test-mixed

# 파라미터 커스터마이징
make test-mixed MAX_VU=300 DURATION=10m

# 서버 전환 후 테스트
make switch TO=gevent WORKERS=8
make warmup
make test-mixed
```

### 4. Grafana에서 결과 확인

1. http://localhost:3000 접속
2. Dashboard → "ExBuy Performance" 선택
3. 타임라인에서 테스트 시작/종료 마커 확인
4. 메트릭 (RPS, 지연시간, 에러율) 확인
5. Logs 탭에서 상세 로그 조회

---

## 모니터링 셋업

### 초기 설정

```bash
cd monitoring

# 1. 환경 변수 설정
cp .env.example .env

# 2. 데이터 디렉터리 및 권한 설정
./setup.sh

# 3. 모니터링 스택 시작
docker compose up -d

# 4. 네트워크 생성 (exbuy와 연동용)
docker network create monitoring_python-performance-dx
```

### Grafana 설정

모니터링 스택이 시작되면 Grafana는 자동으로 다음을 구성합니다:

1. **데이터소스**
   - VictoriaMetrics (default)
   - Loki

2. **대시보드** (자동 프로비저닝)
   - VictoriaMetrics 상태
   - Loki Ingestion
   - cAdvisor 컨테이너 리소스
   - Promtail 로그 수집
   - **ExBuy Performance** (커스텀 대시보드)

### ExBuy와 모니터링 연동

ExBuy의 `docker-compose.yml`은 이미 모니터링 네트워크에 연결되도록 설정되어 있습니다:

```yaml
networks:
  monitoring-network:
    name: monitoring_python-performance-dx
    external: true
```

메트릭은 다음 경로로 노출됩니다:
- Django Prometheus: `http://localhost:9000/metrics`
- K6 Prometheus RW: `http://localhost:8428/api/v1/write`

### 테스트 마커 (Grafana Annotations)

K6 테스트는 자동으로 시작/종료 이벤트를 전송합니다:

```javascript
// k6-scripts/*.js
const testMarker = new Counter('test_execution_marker');

export function setup() {
  testMarker.add(1, { event: 'start', server: SERVER_TYPE, scenario: SCENARIO_NAME });
}

export function teardown() {
  testMarker.add(1, { event: 'end', server: SERVER_TYPE, scenario: SCENARIO_NAME });
}
```

Grafana에서 `test_execution_marker` 메트릭을 쿼리하면 타임라인에 표시됩니다.

---

## 사용 시나리오

### 시나리오 1: WORKERS 수 최적화

```bash
# 다양한 Worker 설정으로 테스트
for WORKERS in 4 8 16; do
  make switch TO=sync WORKERS=$WORKERS
  make warmup
  make test-mixed SERVER=gunicorn-sync MAX_VU=200 DURATION=5m
  sleep 30
done

# 결과 비교
make compare-results
make show-history
```

**Grafana에서 확인:**
- CPU 사용률 vs Workers
- RPS vs Workers
- 메모리 사용량 vs Workers

### 시나리오 2: 서버별 성능 비교

```bash
# 모든 서버 시작
make up-all WORKERS=8

# 순차 테스트
make test-gunicorn-sync
make reset
make test-gunicorn-gevent
make reset
make test-gunicorn-gthread
make reset
make test-uvicorn

# 결과 분석
make compare-results
```

**Grafana에서 비교:**
- `server_type` 라벨로 필터링
- 각 서버의 p95, p99 latency
- 에러율 비교

### 시나리오 3: 쿼리 최적화 효과 검증

```bash
# 최적화 전/후 비교
# read-only.js는 optimize=true와 false를 랜덤으로 호출

make up-sync WORKERS=8
make test-read-only MAX_VU=300 DURATION=10m

# Grafana에서 확인
# - django_db_query_duration_seconds (쿼리 수)
# - 응답 시간 차이
```

### 시나리오 4: 장시간 안정성 테스트

```bash
# 1시간 지속 테스트
make up-sync WORKERS=8
make warmup
make test-mixed MAX_VU=300 DURATION=1h RAMP_UP=2m

# Grafana에서 모니터링
# - 메모리 누수 확인
# - CPU 사용률 추이
# - 에러율 변화
```

---

## 디렉터리 구조

```
python-performance-dx/
├── exbuy/                          # Django/DRF 애플리케이션
│   ├── shop/                       # 메인 앱 (models, views, serializers)
│   ├── config/                     # Django 설정
│   ├── k6-scripts/                 # K6 부하 테스트 스크립트
│   │   ├── read-heavy.js          # 읽기 중심 (80% 읽기)
│   │   ├── write-heavy.js         # 쓰기 중심 (70% 쓰기)
│   │   ├── mixed.js               # 혼합 (60% 읽기, 40% 쓰기)
│   │   └── read-only.js           # 순수 읽기 (100% 읽기)
│   ├── results/                    # 테스트 결과
│   │   ├── *.json                 # K6 JSON 출력
│   │   └── test-history.jsonl     # 테스트 이력
│   ├── Makefile                    # 50+ 명령어
│   ├── docker-compose.yml          # Profile 기반 서버 구성
│   ├── .env.test                   # 테스트 기본 설정
│   ├── compare-results.sh          # 결과 비교 스크립트
│   ├── TESTING.md                  # 테스트 가이드
│   └── README.md                   # ExBuy 문서
│
├── monitoring/                     # 모니터링 스택
│   ├── docker-compose.yml          # VictoriaMetrics, Loki, Grafana
│   ├── setup.sh                    # 초기 설정 스크립트
│   ├── grafana/                    # Grafana 설정
│   │   ├── provisioning/
│   │   │   ├── datasources/       # VictoriaMetrics, Loki
│   │   │   └── dashboards/        # 대시보드 프로비저닝
│   │   └── dashboards/            # JSON 대시보드 파일
│   ├── loki/                       # Loki 설정
│   ├── promtail/                   # Promtail 설정
│   ├── vmagent/                    # VictoriaMetrics Agent 설정
│   ├── k6/logs/                    # K6 로그 (Promtail 수집)
│   └── README.md                   # 모니터링 문서
│
├── .gitignore
└── README.md                       # 이 파일
```

---

## 주요 명령어 참고

### ExBuy 관리

```bash
# 서버 시작/종료
make up-sync WORKERS=8        # 시작
make down-sync                # 종료
make restart-sync WORKERS=16  # 재시작
make switch TO=gevent WORKERS=8  # 전환

# 상태 확인
make status                   # 전체 상태
make ps-running              # 실행 중인 서버
make check-health            # 헬스체크
make stats-all               # 리소스 사용량
```

### 테스트 실행

```bash
# 기본 테스트
make test-mixed              # 혼합 테스트
make test-read-heavy         # 읽기 중심
make test-write-heavy        # 쓰기 중심
make test-read-only          # 순수 읽기

# 파라미터 지정
make test-mixed MAX_VU=300 DURATION=10m
make test-read-only SERVER=uvicorn MAX_VU=500

# 빠른 벤치마크
make benchmark SERVER=sync MAX_VU=200
```

### 결과 분석

```bash
make compare-results         # 결과 비교
make show-history           # 테스트 이력
```

### 데이터 관리

```bash
make seed-small             # 1K/5K/10K
make seed-medium            # 10K/50K/100K
make seed-large             # 100K/500K/1M
make reset                  # 데이터 초기화
make warmup                 # 캐시 워밍업
```

---

## 참고 문서

- [exbuy/README.md](exbuy/README.md) - ExBuy 애플리케이션 상세 가이드
- [exbuy/TESTING.md](exbuy/TESTING.md) - 성능 테스트 실행 가이드
- [monitoring/README.md](monitoring/README.md) - 모니터링 스택 설정 가이드
- [exbuy/BENCHMARKS.md](exbuy/BENCHMARKS.md) - 벤치마크 결과
- [exbuy/PERFORMANCE.md](exbuy/PERFORMANCE.md) - 최적화 가이드

---

## 기술 스택

### ExBuy
- **Framework**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL 16
- **Servers**: Gunicorn (sync/gevent/gthread), Uvicorn
- **Metrics**: django-prometheus
- **Load Test**: K6

### Monitoring
- **Metrics**: VictoriaMetrics (PromQL)
- **Logs**: Loki (LogQL), Promtail
- **Visualization**: Grafana
- **Container**: cAdvisor

### Infrastructure
- **Orchestration**: Docker Compose
- **Automation**: Makefile, Shell scripts
- **Networking**: Docker networks

---

## 라이선스

MIT License

## 기여

이슈와 PR을 환영합니다!
