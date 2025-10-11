# K6 메트릭 쿼리 가이드

이 문서는 K6 부하 테스트에서 VictoriaMetrics/Prometheus로 전송된 메트릭을 조회하는 PromQL 쿼리 모음입니다.

## 목차
- [수집된 메트릭 목록](#수집된-메트릭-목록)
- [기본 쿼리](#기본-쿼리)
- [성능 분석 쿼리](#성능-분석-쿼리)
- [Grafana 대시보드 쿼리](#grafana-대시보드-쿼리)
- [고급 쿼리](#고급-쿼리)

## 수집된 메트릭 목록

K6는 `experimental-prometheus-rw` output을 통해 다음 메트릭을 전송합니다:

| 메트릭 | 설명 | 타입 |
|--------|------|------|
| `k6_http_reqs_total` | HTTP 요청 총 수 | Counter |
| `k6_http_req_duration_p99` | P99 응답 시간 (초) | Gauge |
| `k6_http_req_failed_rate` | HTTP 요청 실패율 | Gauge |
| `k6_errors_rate` | 에러율 (전체) | Gauge |
| `k6_checks_rate` | Check 성공률 | Gauge |
| `k6_vus` | 현재 활성 가상 사용자 수 | Gauge |
| `k6_vus_max` | 최대 가상 사용자 수 | Gauge |
| `k6_iterations_total` | 반복 실행 총 횟수 | Counter |
| `k6_iteration_duration_p99` | P99 반복 실행 시간 | Gauge |
| `k6_data_sent_total` | 전송된 데이터 (bytes) | Counter |
| `k6_data_received_total` | 수신된 데이터 (bytes) | Counter |
| `k6_http_req_blocked_p99` | P99 차단 시간 | Gauge |
| `k6_http_req_connecting_p99` | P99 연결 시간 | Gauge |
| `k6_http_req_tls_handshaking_p99` | P99 TLS 핸드셰이크 시간 | Gauge |
| `k6_http_req_sending_p99` | P99 전송 시간 | Gauge |
| `k6_http_req_waiting_p99` | P99 대기 시간 | Gauge |
| `k6_http_req_receiving_p99` | P99 수신 시간 | Gauge |

### 주요 레이블
- `name`: 엔드포인트 이름 (예: `product-list`, `product-detail`)
- `method`: HTTP 메서드 (예: `GET`, `POST`)
- `status`: HTTP 상태 코드 (예: `200`, `404`)
- `expected_response`: 예상된 응답 여부 (`true`/`false`)
- `scenario`: K6 시나리오 이름
- `url`: 요청 URL
- **`server_type`**: 서버 종류 (예: `gunicorn-sync`, `gunicorn-gevent`, `uvicorn`) - Makefile에서 자동 설정
- **`scenario`**: 테스트 시나리오 (예: `read-heavy`, `write-heavy`, `mixed`) - Makefile에서 자동 설정

## 기본 쿼리

### 1. 총 HTTP 요청 수
```promql
# 전체 요청 수
k6_http_reqs_total

# 엔드포인트별 요청 수
k6_http_reqs_total{name="product-list"}

# 상태코드별 요청 수
k6_http_reqs_total{status="200"}
```

### 2. P99 응답 시간
```promql
# 전체 P99 응답 시간 (초 단위)
k6_http_req_duration_p99

# 밀리초로 변환
k6_http_req_duration_p99 * 1000

# 엔드포인트별 P99
k6_http_req_duration_p99{name="product-detail"}
```

### 3. 실패율
```promql
# HTTP 요청 실패율 (0-1)
k6_http_req_failed_rate

# 백분율로 변환
k6_http_req_failed_rate * 100
```

### 4. 현재 VU (Virtual Users)
```promql
# 현재 활성 VU
k6_vus

# 최대 VU
k6_vus_max
```

## 성능 분석 쿼리

### RPS (Requests Per Second)

```promql
# 전체 RPS (1분 평균)
rate(k6_http_reqs_total[1m])

# 5분 평균 RPS
rate(k6_http_reqs_total[5m])

# 엔드포인트별 RPS
rate(k6_http_reqs_total[1m]) by (name)

# 상태코드별 RPS
rate(k6_http_reqs_total[1m]) by (status)

# 성공한 요청만의 RPS (status 200)
rate(k6_http_reqs_total{status="200"}[1m])
```

### 평균 응답 시간

```promql
# P99 응답 시간 평균 (ms)
avg(k6_http_req_duration_p99) * 1000

# 엔드포인트별 P99 평균
avg(k6_http_req_duration_p99) by (name) * 1000

# 최대 P99 응답 시간
max(k6_http_req_duration_p99) * 1000

# 최소 P99 응답 시간
min(k6_http_req_duration_p99) * 1000
```

### 에러율 분석

```promql
# 전체 에러율 (백분율)
avg(k6_errors_rate) * 100

# HTTP 실패율 (백분율)
avg(k6_http_req_failed_rate) * 100

# 시간별 에러율 추이 (5분 평균)
avg_over_time(k6_errors_rate[5m]) * 100

# 404 에러 비율
sum(rate(k6_http_reqs_total{status="404"}[1m]))
  /
sum(rate(k6_http_reqs_total[1m])) * 100
```

### 엔드포인트 성능 비교

```promql
# 엔드포인트별 P99 응답 시간 비교 (ms, 상위 10개)
topk(10,
  avg(k6_http_req_duration_p99) by (name) * 1000
)

# 엔드포인트별 총 요청 수 (상위 10개)
topk(10,
  sum(k6_http_reqs_total) by (name)
)

# 가장 느린 엔드포인트
topk(5,
  max(k6_http_req_duration_p99) by (name) * 1000
)

# 가장 많이 호출된 엔드포인트
topk(5,
  sum(rate(k6_http_reqs_total[5m])) by (name)
)
```

### 처리량 (Throughput)

```promql
# 초당 전송 데이터 (bytes/s)
rate(k6_data_sent_total[1m])

# 초당 수신 데이터 (bytes/s)
rate(k6_data_received_total[1m])

# MB/s로 변환
rate(k6_data_received_total[1m]) / 1024 / 1024

# 총 데이터 처리량 (송수신 합계, MB/s)
(rate(k6_data_sent_total[1m]) + rate(k6_data_received_total[1m])) / 1024 / 1024
```

### Iteration 분석

```promql
# 초당 Iteration 수
rate(k6_iterations_total[1m])

# 평균 Iteration 시간 (초)
avg(k6_iteration_duration_p99)

# 전체 완료된 Iteration 수
sum(k6_iterations_total)
```

### 서버 및 시나리오 비교

#### 서버별 성능 비교

```promql
# 서버별 RPS
rate(k6_http_reqs_total[1m]) by (server_type)

# 서버별 평균 P99 응답 시간 (ms)
avg(k6_http_req_duration_p99) by (server_type) * 1000

# 서버별 에러율 (%)
avg(k6_http_req_failed_rate) by (server_type) * 100

# 특정 서버의 RPS
rate(k6_http_reqs_total{server_type="gunicorn-sync"}[1m])

# Uvicorn vs Gunicorn sync 성능 비교
avg(k6_http_req_duration_p99{server_type="uvicorn"}) * 1000
  /
avg(k6_http_req_duration_p99{server_type="gunicorn-sync"}) * 1000

# 가장 빠른 서버 (P99 기준)
topk(1,
  avg(k6_http_req_duration_p99) by (server_type)
) * 1000

# 서버별 총 처리 요청 수
sum(k6_http_reqs_total) by (server_type)
```

#### 시나리오별 성능 비교

```promql
# 시나리오별 RPS
rate(k6_http_reqs_total[1m]) by (scenario)

# 시나리오별 평균 P99 (ms)
avg(k6_http_req_duration_p99) by (scenario) * 1000

# Read-heavy vs Write-heavy 성능 차이
avg(k6_http_req_duration_p99{scenario="write-heavy"})
  -
avg(k6_http_req_duration_p99{scenario="read-heavy"})

# 시나리오별 에러율
avg(k6_errors_rate) by (scenario) * 100

# Mixed 시나리오의 특정 서버 성능
rate(k6_http_reqs_total{scenario="mixed", server_type="uvicorn"}[1m])
```

#### 서버 + 시나리오 조합 분석

```promql
# 모든 조합의 RPS (히트맵에 유용)
rate(k6_http_reqs_total[1m]) by (server_type, scenario)

# 모든 조합의 P99 응답 시간
avg(k6_http_req_duration_p99) by (server_type, scenario) * 1000

# Gunicorn-sync + read-heavy 조합
rate(k6_http_reqs_total{server_type="gunicorn-sync", scenario="read-heavy"}[1m])

# 서버별로 가장 성능이 좋은 시나리오
topk(1,
  avg(k6_http_req_duration_p99) by (server_type, scenario)
) by (server_type) * 1000

# 특정 엔드포인트의 서버별 성능
avg(k6_http_req_duration_p99{name="product-list"}) by (server_type) * 1000
```

#### 서버 성능 순위

```promql
# RPS 기준 서버 순위 (높을수록 좋음)
topk(4,
  sum(rate(k6_http_reqs_total[5m])) by (server_type)
)

# 응답 시간 기준 서버 순위 (낮을수록 좋음)
bottomk(4,
  avg(k6_http_req_duration_p99) by (server_type) * 1000
)

# 에러율 기준 서버 순위 (낮을수록 좋음)
bottomk(4,
  avg(k6_http_req_failed_rate) by (server_type) * 100
)

# 처리량(throughput) 기준 순위
topk(4,
  sum(rate(k6_data_received_total[1m])) by (server_type) / 1024 / 1024
)
```

## Grafana 대시보드 쿼리

### 시계열 차트용 Range 쿼리

#### 1. RPS 추이 (시간별)
```promql
# 쿼리 타입: Range
# Start: now-1h
# Step: 30s

rate(k6_http_reqs_total[1m])
```

#### 2. P99 응답 시간 추이 (ms)
```promql
# 쿼리 타입: Range
# Legend: {{name}}

k6_http_req_duration_p99{name=~"product-.*"} * 1000
```

#### 3. 활성 VU 추이
```promql
# 쿼리 타입: Range

k6_vus
```

#### 4. 에러율 추이 (%)
```promql
# 쿼리 타입: Range

avg(k6_errors_rate) * 100
```

#### 5. 엔드포인트별 RPS 스택 차트
```promql
# 쿼리 타입: Range
# Legend: {{name}}

sum(rate(k6_http_reqs_total[1m])) by (name)
```

#### 6. 서버별 RPS 비교
```promql
# 쿼리 타입: Range
# Legend: {{server_type}}

rate(k6_http_reqs_total[1m]) by (server_type)
```

#### 7. 서버별 P99 응답 시간 비교 (ms)
```promql
# 쿼리 타입: Range
# Legend: {{server_type}}

avg(k6_http_req_duration_p99) by (server_type) * 1000
```

#### 8. 시나리오별 성능 추이
```promql
# 쿼리 타입: Range
# Legend: {{scenario}}

avg(k6_http_req_duration_p99) by (scenario) * 1000
```

### Stat 패널용 쿼리

#### 총 요청 수
```promql
sum(k6_http_reqs_total)
```

#### 평균 RPS
```promql
avg(rate(k6_http_reqs_total[5m]))
```

#### 최대 VU
```promql
max(k6_vus_max)
```

#### 전체 평균 P99 (ms)
```promql
avg(k6_http_req_duration_p99) * 1000
```

#### 성공률 (%)
```promql
(1 - avg(k6_http_req_failed_rate)) * 100
```

### Table 패널용 쿼리

#### 엔드포인트별 성능 요약
```promql
# Instant 쿼리, Format: Table

# Total Requests
sum(k6_http_reqs_total) by (name)

# RPS
sum(rate(k6_http_reqs_total[5m])) by (name)

# P99 Latency (ms)
avg(k6_http_req_duration_p99) by (name) * 1000

# Error Rate (%)
avg(k6_http_req_failed_rate) by (name) * 100
```

#### 서버별 성능 비교 테이블
```promql
# Instant 쿼리, Format: Table

# Total Requests
sum(k6_http_reqs_total) by (server_type)

# Avg RPS
avg(rate(k6_http_reqs_total[5m])) by (server_type)

# P99 Latency (ms)
avg(k6_http_req_duration_p99) by (server_type) * 1000

# Error Rate (%)
avg(k6_http_req_failed_rate) by (server_type) * 100

# Data Received (MB)
sum(k6_data_received_total) by (server_type) / 1024 / 1024
```

### Grafana 변수 (Variables) 활용

대시보드에 변수를 추가하면 동적으로 필터링할 수 있습니다:

```
# Variable: server_type
# Query: label_values(k6_http_reqs_total, server_type)
# Multi-value: true

# Variable: scenario
# Query: label_values(k6_http_reqs_total, scenario)

# Variable: endpoint
# Query: label_values(k6_http_reqs_total{server_type="$server_type"}, name)
```

**변수를 사용한 쿼리:**
```promql
# 선택한 서버의 RPS
rate(k6_http_reqs_total{server_type="$server_type"}[1m])

# 선택한 서버와 시나리오의 P99
avg(k6_http_req_duration_p99{server_type="$server_type", scenario="$scenario"}) * 1000

# 선택한 엔드포인트의 서버별 비교
avg(k6_http_req_duration_p99{name="$endpoint"}) by (server_type) * 1000
```

## 고급 쿼리

### 1. SLO 달성률 체크

```promql
# P99 < 500ms 달성률
(
  count(k6_http_req_duration_p99 < 0.5)
  /
  count(k6_http_req_duration_p99)
) * 100

# 에러율 < 1% 달성률
(
  count(k6_errors_rate < 0.01)
  /
  count(k6_errors_rate)
) * 100
```

### 2. 응답 시간 분포 분석

```promql
# 2ms 이하 응답 비율
count(k6_http_req_duration_p99 < 0.002)
  /
count(k6_http_req_duration_p99) * 100

# 5ms 이상 응답 비율
count(k6_http_req_duration_p99 >= 0.005)
  /
count(k6_http_req_duration_p99) * 100
```

### 3. 상위/하위 N개 엔드포인트

```promql
# 가장 느린 5개 엔드포인트
bottomk(5,
  avg(k6_http_req_duration_p99) by (name)
) * 1000

# 에러율이 가장 높은 3개 엔드포인트
topk(3,
  avg(k6_http_req_failed_rate) by (name) * 100
)

# 트래픽이 가장 적은 5개 엔드포인트
bottomk(5,
  sum(rate(k6_http_reqs_total[5m])) by (name)
)
```

### 4. 시간대별 비교

```promql
# 현재 RPS vs 5분 전 RPS
rate(k6_http_reqs_total[1m])
  -
rate(k6_http_reqs_total[1m] offset 5m)

# 응답 시간 증가율 (%)
(
  avg(k6_http_req_duration_p99)
  -
  avg(k6_http_req_duration_p99 offset 5m)
) / avg(k6_http_req_duration_p99 offset 5m) * 100
```

### 5. HTTP 상태코드 분석

```promql
# 상태코드별 요청 비율
sum(rate(k6_http_reqs_total[1m])) by (status)
  /
sum(rate(k6_http_reqs_total[1m]))

# 2xx 성공 비율
sum(rate(k6_http_reqs_total{status=~"2.."}[1m]))
  /
sum(rate(k6_http_reqs_total[1m])) * 100

# 4xx 클라이언트 에러 비율
sum(rate(k6_http_reqs_total{status=~"4.."}[1m]))
  /
sum(rate(k6_http_reqs_total[1m])) * 100

# 5xx 서버 에러 비율
sum(rate(k6_http_reqs_total{status=~"5.."}[1m]))
  /
sum(rate(k6_http_reqs_total[1m])) * 100
```

### 6. 부하 테스트 단계별 분석

```promql
# Ramp-up 단계: VU 증가율
rate(k6_vus[30s])

# Steady-state: 평균 성능
avg_over_time(k6_http_req_duration_p99[5m]) * 1000

# Peak 시점의 RPS
max_over_time(rate(k6_http_reqs_total[1m])[10m:])
```

### 7. 네트워크 연결 분석

```promql
# P99 연결 시간 (ms)
avg(k6_http_req_connecting_p99) * 1000

# P99 TLS 핸드셰이크 시간 (ms)
avg(k6_http_req_tls_handshaking_p99) * 1000

# P99 대기 시간 (첫 바이트까지, ms)
avg(k6_http_req_waiting_p99) * 1000

# 전체 요청 시간 분해
sum(k6_http_req_blocked_p99 +
    k6_http_req_connecting_p99 +
    k6_http_req_sending_p99 +
    k6_http_req_waiting_p99 +
    k6_http_req_receiving_p99) * 1000
```

### 8. 성능 저하 감지

```promql
# P99가 임계값(500ms)을 초과하는 엔드포인트
count(k6_http_req_duration_p99 > 0.5) by (name)

# 에러율이 임계값(5%)을 초과하는 시점
k6_errors_rate > 0.05

# RPS가 급격히 감소한 시점 (50% 이상 감소)
(
  rate(k6_http_reqs_total[1m])
  <
  rate(k6_http_reqs_total[1m] offset 1m) * 0.5
)
```

## 실전 예제

### 예제 1: 종합 성능 대시보드

```promql
# Row 1: 전체 개요
- Total Requests: sum(k6_http_reqs_total)
- Avg RPS: avg(rate(k6_http_reqs_total[5m]))
- Avg P99 (ms): avg(k6_http_req_duration_p99) * 1000
- Success Rate (%): (1 - avg(k6_http_req_failed_rate)) * 100

# Row 2: 시계열 차트
- RPS Over Time: rate(k6_http_reqs_total[1m])
- P99 Over Time: k6_http_req_duration_p99 * 1000
- Active VUs: k6_vus
- Error Rate (%): avg(k6_errors_rate) * 100

# Row 3: 엔드포인트 비교
- Top 10 Endpoints by RPS: topk(10, sum(rate(k6_http_reqs_total[1m])) by (name))
- Top 5 Slowest Endpoints: topk(5, avg(k6_http_req_duration_p99) by (name) * 1000)
```

### 예제 2: 에러 모니터링 대시보드

```promql
# 전체 에러율
avg(k6_errors_rate) * 100

# HTTP 실패율
avg(k6_http_req_failed_rate) * 100

# 404 에러 발생 추이
sum(rate(k6_http_reqs_total{status="404"}[1m])) by (name)

# 에러가 발생한 엔드포인트
k6_http_reqs_total{expected_response="false"}

# 에러율이 높은 상위 5개
topk(5, avg(k6_http_req_failed_rate) by (name) * 100)
```

### 예제 3: 용량 계획 대시보드

```promql
# 최대 처리 RPS
max_over_time(rate(k6_http_reqs_total[1m])[30m:])

# VU당 RPS
rate(k6_http_reqs_total[1m]) / k6_vus

# 최대 VU에서의 성능
k6_http_req_duration_p99{} * 1000 and on() k6_vus == k6_vus_max

# 데이터 전송률 (MB/s)
rate(k6_data_sent_total[1m]) / 1024 / 1024
```

### 예제 4: 서버 비교 대시보드

```promql
# Row 1: 서버별 핵심 지표 (Stat 패널)
- Gunicorn Sync RPS: sum(rate(k6_http_reqs_total{server_type="gunicorn-sync"}[5m]))
- Gunicorn Gevent RPS: sum(rate(k6_http_reqs_total{server_type="gunicorn-gevent"}[5m]))
- Uvicorn RPS: sum(rate(k6_http_reqs_total{server_type="uvicorn"}[5m]))

# Row 2: 서버별 RPS 시계열 비교
rate(k6_http_reqs_total[1m]) by (server_type)

# Row 3: 서버별 P99 응답 시간 비교
avg(k6_http_req_duration_p99) by (server_type) * 1000

# Row 4: 서버 성능 순위 (Bar Gauge)
- RPS: topk(4, sum(rate(k6_http_reqs_total[5m])) by (server_type))
- P99: bottomk(4, avg(k6_http_req_duration_p99) by (server_type) * 1000)

# Row 5: 서버별 성능 테이블
- Server | Total Reqs | RPS | P99 (ms) | Error Rate (%)
```

### 예제 5: 시나리오별 비교 대시보드

```promql
# Row 1: 시나리오 개요
- Read-heavy P99: avg(k6_http_req_duration_p99{scenario="read-heavy"}) * 1000
- Write-heavy P99: avg(k6_http_req_duration_p99{scenario="write-heavy"}) * 1000
- Mixed P99: avg(k6_http_req_duration_p99{scenario="mixed"}) * 1000

# Row 2: 시나리오별 RPS 추이
rate(k6_http_reqs_total[1m]) by (scenario)

# Row 3: 시나리오 + 서버 히트맵
avg(k6_http_req_duration_p99) by (server_type, scenario) * 1000

# Row 4: 시나리오별 에러율
avg(k6_errors_rate) by (scenario) * 100
```

### 예제 6: 서버 + 엔드포인트 상세 분석

```promql
# Variables
- server_type: label_values(k6_http_reqs_total, server_type)
- endpoint: label_values(k6_http_reqs_total{server_type="$server_type"}, name)

# Row 1: 선택한 서버의 전체 성능
- Total RPS: sum(rate(k6_http_reqs_total{server_type="$server_type"}[5m]))
- Avg P99: avg(k6_http_req_duration_p99{server_type="$server_type"}) * 1000
- Error Rate: avg(k6_http_req_failed_rate{server_type="$server_type"}) * 100

# Row 2: 엔드포인트별 성능 (선택한 서버)
- P99 by endpoint: avg(k6_http_req_duration_p99{server_type="$server_type"}) by (name) * 1000
- RPS by endpoint: sum(rate(k6_http_reqs_total{server_type="$server_type"}[1m])) by (name)

# Row 3: 특정 엔드포인트의 서버별 비교
avg(k6_http_req_duration_p99{name="$endpoint"}) by (server_type) * 1000
```

## 알림 규칙 예제

### Prometheus/Alertmanager 알림 규칙

```yaml
groups:
  - name: k6_alerts
    interval: 30s
    rules:
      # P99 응답 시간 초과
      - alert: HighLatency
        expr: avg(k6_http_req_duration_p99) * 1000 > 500
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High P99 latency detected"
          description: "P99 latency is {{ $value }}ms (threshold: 500ms)"

      # 에러율 초과
      - alert: HighErrorRate
        expr: avg(k6_errors_rate) * 100 > 5
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% (threshold: 5%)"

      # HTTP 실패율 초과
      - alert: HighHTTPFailureRate
        expr: avg(k6_http_req_failed_rate) * 100 > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High HTTP failure rate"
          description: "HTTP failure rate is {{ $value }}%"

      # RPS 급감
      - alert: RPSDropped
        expr: |
          rate(k6_http_reqs_total[1m])
          <
          rate(k6_http_reqs_total[1m] offset 5m) * 0.5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "RPS dropped significantly"
          description: "Current RPS is less than 50% of 5 minutes ago"

      # 특정 서버 성능 저하
      - alert: ServerPerformanceDegraded
        expr: avg(k6_http_req_duration_p99{server_type="uvicorn"}) * 1000 > 1000
        for: 3m
        labels:
          severity: warning
          server: "{{ $labels.server_type }}"
        annotations:
          summary: "Server {{ $labels.server_type }} performance degraded"
          description: "P99 latency for {{ $labels.server_type }} is {{ $value }}ms"

      # 서버별 에러율 초과
      - alert: ServerHighErrorRate
        expr: avg(k6_http_req_failed_rate) by (server_type) * 100 > 5
        for: 2m
        labels:
          severity: critical
          server: "{{ $labels.server_type }}"
        annotations:
          summary: "High error rate on {{ $labels.server_type }}"
          description: "Error rate is {{ $value }}% on {{ $labels.server_type }}"

      # 시나리오별 성능 이상
      - alert: ScenarioPerformanceAnomaly
        expr: |
          avg(k6_http_req_duration_p99{scenario="read-heavy"}) * 1000 >
          avg(k6_http_req_duration_p99{scenario="read-heavy"} offset 10m) * 1000 * 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Performance anomaly in {{ $labels.scenario }} scenario"
          description: "P99 latency doubled compared to 10 minutes ago"
```

## 팁과 Best Practices

### 1. Rate 계산 시 시간 윈도우
- 짧은 버스트: `[30s]` - 빠른 반응
- 일반 모니터링: `[1m]` - 균형
- 장기 추세: `[5m]` - 안정적

### 2. 레이블 필터링
```promql
# 특정 엔드포인트만
{name="product-list"}

# 정규식 매칭
{name=~"product-.*"}

# 성공한 요청만
{expected_response="true"}

# 여러 조건
{name="reviews", status="200"}

# 특정 서버 필터링
{server_type="gunicorn-sync"}

# 여러 서버 선택
{server_type=~"gunicorn-sync|uvicorn"}

# 특정 시나리오
{scenario="read-heavy"}

# 서버 + 시나리오 조합
{server_type="uvicorn", scenario="mixed"}

# 특정 서버의 특정 엔드포인트
{server_type="gunicorn-gevent", name="product-list"}

# Gunicorn 계열 서버만
{server_type=~"gunicorn-.*"}
```

### 3. Aggregation 선택
- `sum()`: 총합 (RPS, 요청 수)
- `avg()`: 평균 (응답 시간, 에러율)
- `max()`/`min()`: 극값
- `count()`: 개수

### 4. 쿼리 최적화
```promql
# 비추천: 레이블이 너무 많음
k6_http_reqs_total

# 추천: 필요한 레이블만 선택
k6_http_reqs_total{name="product-list", status="200"}

# 추천: aggregation으로 차원 축소
sum(rate(k6_http_reqs_total[1m])) by (name)

# 서버 비교 시 불필요한 레이블 제거
sum(rate(k6_http_reqs_total[1m])) by (server_type)

# 특정 서버의 엔드포인트별 분석
sum(rate(k6_http_reqs_total{server_type="uvicorn"}[1m])) by (name)
```

### 5. 서버 비교 Best Practices

```promql
# 좋은 예: 명확한 비교
avg(k6_http_req_duration_p99) by (server_type) * 1000

# 나쁜 예: 모든 레이블 포함
k6_http_req_duration_p99

# 좋은 예: 특정 시나리오로 제한
avg(k6_http_req_duration_p99{scenario="read-heavy"}) by (server_type) * 1000

# 좋은 예: 비율로 비교 (Uvicorn이 Gunicorn보다 몇 배 빠른지)
avg(k6_http_req_duration_p99{server_type="gunicorn-sync"})
  /
avg(k6_http_req_duration_p99{server_type="uvicorn"})
```

## 문제 해결

### 메트릭이 보이지 않을 때
```bash
# VictoriaMetrics 확인
curl http://localhost:8428/api/v1/labels

# k6 실행 시 올바른 설정 사용 (Makefile 사용 권장)
cd exbuy
make test-read-heavy

# 또는 수동 실행 시
K6_PROMETHEUS_RW_SERVER_URL=http://localhost:8428/api/v1/write \
k6 run --out experimental-prometheus-rw \
  --tag server_type=gunicorn-sync \
  --tag scenario=read-heavy \
  script.js
```

### 태그가 제대로 붙지 않을 때
```bash
# 사용 가능한 레이블 확인
curl http://localhost:8428/api/v1/label/__name__/values | jq

# server_type 레이블 값 확인
curl 'http://localhost:8428/api/v1/label/server_type/values' | jq

# scenario 레이블 값 확인
curl 'http://localhost:8428/api/v1/label/scenario/values' | jq

# 특정 메트릭의 모든 레이블 확인
curl 'http://localhost:8428/api/v1/series?match[]=k6_http_reqs_total' | jq
```

### 서버별 데이터가 섞여 보일 때
```promql
# 문제: 모든 서버 데이터가 합쳐짐
rate(k6_http_reqs_total[1m])

# 해결: server_type으로 분리
rate(k6_http_reqs_total[1m]) by (server_type)

# 또는 특정 서버만
rate(k6_http_reqs_total{server_type="uvicorn"}[1m])
```

### 쿼리가 느릴 때
- 시간 범위 축소
- 레이블 필터 추가 (server_type, scenario 등)
- `rate()` 대신 `irate()` 사용 (최근 2개 샘플만)
- 불필요한 레이블은 aggregation으로 제거

## 참고 자료

- [K6 Metrics](https://k6.io/docs/using-k6/metrics/)
- [Prometheus PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [VictoriaMetrics Docs](https://docs.victoriametrics.com/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
