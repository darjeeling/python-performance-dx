# 성능 테스트 실행 가이드

ExBuy 성능 테스트를 위한 완전한 가이드입니다. 모든 명령은 Makefile을 통해 실행됩니다.

## 목차
- [빠른 시작](#빠른-시작)
- [서버 관리](#서버-관리)
- [부하 테스트](#부하-테스트)
- [결과 분석](#결과-분석)
- [고급 사용법](#고급-사용법)
- [문제 해결](#문제-해결)

## 빠른 시작

### 전체 자동 설정 (추천)
```bash
make quickstart
```
이 명령은 다음을 자동으로 수행합니다:
1. Docker 이미지 빌드
2. DB 시작
3. 마이그레이션 실행
4. 소규모 데이터 시딩
5. Gunicorn sync 서버 시작
6. 헬스체크

### 수동 단계별 설정
```bash
# 1. 이미지 빌드
make build

# 2. DB 시작
make up

# 3. 마이그레이션
make migrate

# 4. 데이터 시딩
make seed-medium    # 10K products, 50K orders, 100K reviews

# 5. 서버 시작
make up-sync        # Gunicorn sync 서버
```

## 서버 관리

### 서버 시작

```bash
# 단일 서버 시작
make up-sync        # Gunicorn sync (기본 WORKERS=4)
make up-gevent      # Gunicorn gevent
make up-gthread     # Gunicorn gthread
make up-uvicorn     # Uvicorn

# WORKERS 지정
make up-sync WORKERS=8
make up-gevent WORKERS=16

# 모든 서버 시작 (비교 테스트용)
make up-all WORKERS=4
```

### 서버 종료

```bash
# 특정 서버만 종료
make down-sync
make down-gevent
make down-gthread
make down-uvicorn

# 모든 앱 서버 종료 (DB는 유지)
make down-all-servers

# 전체 종료 (DB 포함)
make down
```

### 서버 재시작

```bash
make restart-sync WORKERS=8
make restart-gevent WORKERS=16
```

### 서버 전환 (추천)

```bash
# 현재 서버를 종료하고 새 서버로 전환
make switch TO=gevent WORKERS=8
make switch TO=uvicorn WORKERS=4

# 사용 가능한 서버: sync, gevent, gthread, uvicorn
```

### 서버 상태 확인

```bash
# 전체 상태 확인 (컨테이너 + 헬스체크)
make status

# 실행 중인 앱 서버 목록만
make ps-running

# 헬스체크만
make check-health

# 리소스 사용량 확인
make stats          # 모든 컨테이너
make stats-all      # 앱 서버만
```

### 로그 확인

```bash
# 전체 로그
make logs

# 특정 서버 로그
make logs-sync
make logs-gevent
make logs-gthread
make logs-uvicorn
```

## 부하 테스트

### 기본 테스트 시나리오

모든 테스트는 파라미터로 커스터마이징 가능합니다:

```bash
# 읽기 중심 테스트 (80% 읽기, 20% 쓰기)
make test-read-heavy

# 쓰기 중심 테스트 (30% 읽기, 70% 쓰기)
make test-write-heavy

# 혼합 테스트 (60% 읽기, 40% 쓰기)
make test-mixed

# 순수 읽기 테스트 (100% 읽기, 매분 30초 시작)
make test-read-only
```

### 파라미터 커스터마이징

```bash
# VU(Virtual Users) 변경
make test-mixed MAX_VU=300

# 지속 시간 변경
make test-read-heavy DURATION=10m

# 서버 및 포트 지정
make test-mixed SERVER=gunicorn-gevent PORT_9000=http://localhost:9001

# 모든 파라미터 조합
make test-read-only \
  SERVER=uvicorn \
  PORT_9000=http://localhost:9003 \
  MAX_VU=500 \
  DURATION=15m \
  RAMP_UP=1m
```

**사용 가능한 파라미터:**
- `SERVER`: gunicorn-sync, gunicorn-gevent, gunicorn-gthread, uvicorn (기본: gunicorn-sync)
- `WORKERS`: Worker 프로세스 수 (기본: 4)
- `MAX_VU`: 최대 Virtual Users (기본: 200)
- `DURATION`: 테스트 지속 시간 (기본: 5m)
- `RAMP_UP`: 램프업 시간 (기본: 30s)
- `RAMP_DOWN`: 램프다운 시간 (기본: 30s)

### 빠른 벤치마크 (1분)

```bash
# 빠른 성능 확인 (1분 테스트)
make benchmark SERVER=sync MAX_VU=100

# 여러 서버 빠르게 비교
make benchmark SERVER=sync MAX_VU=200
make switch TO=gevent
make benchmark SERVER=gevent MAX_VU=200
```

### 서버별 전체 테스트

워밍업 + 3개 시나리오 자동 실행:

```bash
make test-gunicorn-sync
make test-gunicorn-gevent
make test-gunicorn-gthread
make test-uvicorn
```

### 서버별 Read-Only 테스트

```bash
make test-read-only-gunicorn-sync MAX_VU=300
make test-read-only-gunicorn-gevent MAX_VU=300
make test-read-only-gunicorn-gthread MAX_VU=300
make test-read-only-uvicorn MAX_VU=300
```

### 전체 서버 비교 테스트

모든 서버에 대해 3개 시나리오를 순차 실행 (자동 리셋 포함):

```bash
make test-all
```

## 데이터 관리

### 데이터 시딩

```bash
make seed-small     # 1K/5K/10K (빠른 테스트)
make seed-medium    # 10K/50K/100K (기본)
make seed-large     # 100K/500K/1M (대규모 부하 테스트)
```

### 워밍업

테스트 전 캐시 워밍업 (권장):

```bash
make warmup                             # 기본 (port 9000)
make warmup BASE_URL=http://localhost:9001   # 다른 포트
```

### 데이터 초기화

```bash
make reset    # 대화형 리셋 (quick/full 선택)
```

## 결과 분석

### 테스트 결과 확인

```bash
# 간단한 비교
make compare

# 상세 비교 (테이블 형식)
make compare-results

# 테스트 실행 이력 조회
make show-history
```

### 결과 파일 위치

- **JSON 결과**: `results/*.json`
- **K6 로그**: `../monitoring/k6/logs/*.log`
- **테스트 이력**: `results/test-history.jsonl`

### Grafana 대시보드

```
http://localhost:3000
```
- Dashboard: "ExBuy Performance"
- 실시간 RPS, 지연시간, 에러율 확인
- 테스트 시작/종료 마커 표시

### Prometheus 메트릭

```bash
# Django 메트릭 직접 확인
curl http://localhost:9000/metrics
curl http://localhost:9001/metrics  # gevent
curl http://localhost:9002/metrics  # gthread
curl http://localhost:9003/metrics  # uvicorn
```

## 고급 사용법

### 시나리오 1: 다양한 WORKERS 설정 비교

```bash
# 4 workers
make switch TO=sync WORKERS=4
make warmup
make test-mixed SERVER=gunicorn-sync MAX_VU=200

# 8 workers
make switch TO=sync WORKERS=8
make warmup
make test-mixed SERVER=gunicorn-sync MAX_VU=200

# 16 workers
make switch TO=sync WORKERS=16
make warmup
make test-mixed SERVER=gunicorn-sync MAX_VU=200

# 결과 비교
make compare-results
```

### 시나리오 2: VU 증가 테스트

```bash
make up-sync WORKERS=8

for VU in 100 200 300 400 500; do
  echo "Testing with VU=$VU"
  make test-read-only MAX_VU=$VU DURATION=3m
  sleep 30
done

make compare-results
```

### 시나리오 3: 모든 서버 동시 비교

```bash
# 1. 모든 서버 시작
make up-all WORKERS=8

# 2. 각 서버에 동시 테스트 실행
make test-read-heavy SERVER=gunicorn-sync PORT_9000=http://localhost:9000 &
make test-read-heavy SERVER=gunicorn-gevent PORT_9000=http://localhost:9001 &
make test-read-heavy SERVER=gunicorn-gthread PORT_9000=http://localhost:9002 &
make test-read-heavy SERVER=uvicorn PORT_9000=http://localhost:9003 &
wait

# 3. 결과 비교
make compare-results
```

### 시나리오 4: 장시간 안정성 테스트

```bash
make up-sync WORKERS=8
make warmup

# 1시간 테스트
make test-mixed MAX_VU=300 DURATION=1h RAMP_UP=2m
```

### 환경별 테스트 설정

`.env.test` 파일을 수정하여 기본값 변경:

```bash
# .env.test 편집
WORKERS=8
MAX_VU=300
DURATION=10m

# 이후 테스트는 새 기본값 사용
make test-mixed
```

## 문제 해결

### DB 연결 오류

```bash
# DB 상태 확인
docker compose ps db

# DB 재시작
docker compose restart db

# DB 로그 확인
docker compose logs db
```

### 컨테이너가 시작하지 않음

```bash
# 상태 확인
make status

# 로그 확인
make logs-sync

# 완전 재빌드
make rebuild
make up-sync
```

### 포트 충돌

```bash
# 포트 사용 확인
sudo lsof -i :9000
sudo lsof -i :9001

# 기존 컨테이너 정리
make down
docker ps -a
```

### 테스트 결과가 이상함

```bash
# 1. 데이터 초기화
make reset

# 2. 워밍업
make warmup

# 3. 재테스트
make test-mixed
```

### 메모리 부족

```bash
# 리소스 사용량 확인
make stats-all

# 불필요한 컨테이너 정리
make down
docker system prune -a
```

### K6 타임아웃

k6-scripts/*.js 파일에서 타임아웃 증가:

```javascript
export const options = {
  ...
  timeout: '5m',  // 타임아웃 증가
}
```

## 정리

```bash
# 결과 파일만 삭제
rm -rf results/

# 컨테이너 정리 (데이터 유지)
make down

# 완전 정리 (데이터 삭제)
make clean-data
```

## 유용한 명령어 참고

### 전체 명령어 목록

```bash
make help
```

### 일반적인 워크플로우

```bash
# 1. 초기 설정
make quickstart

# 2. 서버 전환하며 테스트
make switch TO=gevent WORKERS=8
make warmup
make test-mixed SERVER=gunicorn-gevent PORT_9000=http://localhost:9001

# 3. 결과 확인
make compare-results
make show-history

# 4. Grafana에서 상세 분석
open http://localhost:3000
```

## 참고 문서

- [README.md](README.md): 프로젝트 개요
- [BENCHMARKS.md](BENCHMARKS.md): 벤치마크 결과
- [PERFORMANCE.md](PERFORMANCE.md): 최적화 가이드
- [K6_METRICS_QUERIES.md](K6_METRICS_QUERIES.md): Prometheus 쿼리

## 문의 및 피드백

문제가 발생하면 다음을 확인하세요:
1. `make status` - 서버 상태
2. `make logs-sync` - 로그
3. `make check-health` - 헬스체크
4. `results/test-history.jsonl` - 테스트 이력
