.PHONY: help build up down migrate seed test-* warmup reset clean

# 기본 설정
SERVER ?= gunicorn-sync
PORT_9000 = http://localhost:9000
PORT_9001 = http://localhost:9001
PORT_9002 = http://localhost:9002
PORT_9003 = http://localhost:9003

help: ## 도움말 표시
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# 🏗️ 환경 구성
build: ## Docker 이미지 빌드
	docker compose build

rebuild: ## Docker 이미지 완전 재빌드 (캐시 무시)
	@echo "이미지를 처음부터 다시 빌드합니다..."
	@./rebuild.sh || (echo "rebuild.sh 실행 실패" && exit 1)
	@echo "✓ 재빌드 완료"

up: ## 서비스 시작 (기본: db만)
	docker compose up -d db
	@echo "✓ DB 시작됨"

up-sync: ## Gunicorn sync 서버 시작
	docker compose --profile gunicorn-sync up -d

up-gevent: ## Gunicorn gevent 서버 시작
	docker compose --profile gunicorn-gevent up -d

up-gthread: ## Gunicorn gthread 서버 시작
	docker compose --profile gunicorn-gthread up -d

up-uvicorn: ## Uvicorn 서버 시작
	docker compose --profile uvicorn up -d

up-all: ## 모든 서버 시작
	docker compose --profile gunicorn-sync --profile gunicorn-gevent --profile gunicorn-gthread --profile uvicorn up -d

down: ## 모든 서비스 종료
	docker compose down

logs: ## 로그 확인
	docker compose logs -f

# 🗄️ 데이터베이스
migrate: ## 마이그레이션 실행
	docker compose run --rm web-gunicorn-sync python manage.py migrate

seed-small: ## 소규모 데이터 시딩 (1K/5K/10K)
	docker compose run --rm web-gunicorn-sync python manage.py seed_data --products 1000 --orders 5000 --reviews 10000

seed-medium: ## 중규모 데이터 시딩 (10K/50K/100K)
	docker compose run --rm web-gunicorn-sync python manage.py seed_data --products 10000 --orders 50000 --reviews 100000

seed-large: ## 대규모 데이터 시딩 (100K/500K/1M)
	docker compose run --rm web-gunicorn-sync python manage.py seed_data --products 100000 --orders 500000 --reviews 1000000 --batch-size 5000

seed: seed-medium ## 기본 데이터 시딩 (중규모)

# 🔥 워밍업
warmup: ## 캐시 워밍업
	@echo "워밍업 중... ($(BASE_URL))"
	@BASE_URL=$(or $(BASE_URL),$(PORT_9000)) ./warmup.sh || (echo "warmup.sh 실행 실패" && exit 1)
	@echo "✓ 워밍업 완료"

# 🧹 리셋
reset: ## 데이터 초기화
	@echo "데이터 초기화 중..."
	@./reset-test.sh || (echo "reset-test.sh 실행 실패" && exit 1)
	@echo "✓ 초기화 완료"

# 📊 부하 테스트
test-read-heavy: ## 읽기 중심 테스트
	@mkdir -p results
	@mkdir -p ../monitoring/k6/logs
	K6_PROMETHEUS_RW_SERVER_URL=http://localhost:8428/api/v1/write \
	BASE_URL=$(PORT_9000) k6 run \
		--tag server_type=$(SERVER) \
		--tag scenario=read-heavy \
		--out json=results/$(SERVER)-read-heavy.json \
		--out experimental-prometheus-rw \
		--log-output=file=../monitoring/k6/logs/$(SERVER)-read-heavy.log \
		k6-scripts/read-heavy.js

test-write-heavy: ## 쓰기 중심 테스트
	@mkdir -p results
	@mkdir -p ../monitoring/k6/logs
	K6_PROMETHEUS_RW_SERVER_URL=http://localhost:8428/api/v1/write \
	BASE_URL=$(PORT_9000) k6 run \
		--tag server_type=$(SERVER) \
		--tag scenario=write-heavy \
		--out json=results/$(SERVER)-write-heavy.json \
		--out experimental-prometheus-rw \
		--log-output=file=../monitoring/k6/logs/$(SERVER)-write-heavy.log \
		k6-scripts/write-heavy.js

test-mixed: ## 혼합 테스트
	@mkdir -p results
	@mkdir -p ../monitoring/k6/logs
	K6_PROMETHEUS_RW_SERVER_URL=http://localhost:8428/api/v1/write \
	BASE_URL=$(PORT_9000) k6 run \
		--tag server_type=$(SERVER) \
		--tag scenario=mixed \
		--out json=results/$(SERVER)-mixed.json \
		--out experimental-prometheus-rw \
		--log-output=file=../monitoring/k6/logs/$(SERVER)-mixed.log \
		k6-scripts/mixed.js

test-read-only: ## 순수 읽기 전용 테스트 (5분 30초, 매분 30초 시작)
	@echo "💡 VU 변경: make test-read-only SERVER=<server> PORT_9000=<url> MAX_VU=<number>"
	@echo "=== 테스트 시작 ==="
	@echo "서버 타입: $(SERVER)"
	@echo "시나리오: read-only"
	@START_TIME=$$(date '+%Y-%m-%d %H:%M:%S'); \
	echo "시작 예정: $$START_TIME"; \
	echo "VU 설정: $(or $(MAX_VU),200)"; \
	echo "==================================="; \
	echo "매분 30초에 시작하도록 대기 중..."; \
	current=$$(date +%s); \
	seconds=$$((current % 60)); \
	if [ $$seconds -lt 30 ]; then \
		sleep $$((30 - seconds)); \
	else \
		sleep $$((90 - seconds)); \
	fi; \
	START_TIME=$$(date '+%Y-%m-%d %H:%M:%S'); \
	echo "실제 시작: $$START_TIME"; \
	mkdir -p results; \
	mkdir -p ../monitoring/k6/logs; \
	K6_PROMETHEUS_RW_SERVER_URL=http://localhost:8428/api/v1/write \
	BASE_URL=$(PORT_9000) k6 run \
		--tag server_type=$(SERVER) \
		--tag scenario=read-only \
		--out json=results/$(SERVER)-read-only.json \
		--out experimental-prometheus-rw \
		--log-output=file=../monitoring/k6/logs/$(SERVER)-read-only.log \
		k6-scripts/read-only.js; \
	END_TIME=$$(date '+%Y-%m-%d %H:%M:%S'); \
	echo "==================================="; \
	echo "=== 테스트 완료 ==="; \
	echo "서버 타입: $(SERVER)"; \
	echo "시나리오: read-only"; \
	echo "시작 시간: $$START_TIME"; \
	echo "종료 시간: $$END_TIME"; \
	echo "==================================="

# 서버별 전체 테스트
test-gunicorn-sync: ## Gunicorn sync 전체 테스트
	@echo "=== Gunicorn sync 테스트 ==="
	-@make warmup
	-@make test-read-heavy SERVER=gunicorn-sync PORT_9000=http://localhost:9000
	@sleep 10
	-@make test-write-heavy SERVER=gunicorn-sync PORT_9000=http://localhost:9000
	@sleep 10
	-@make test-mixed SERVER=gunicorn-sync PORT_9000=http://localhost:9000

test-gunicorn-gevent: ## Gunicorn gevent 전체 테스트
	@echo "=== Gunicorn gevent 테스트 ==="
	-@make warmup BASE_URL=http://localhost:9001
	-@make test-read-heavy SERVER=gunicorn-gevent PORT_9000=http://localhost:9001
	@sleep 10
	-@make test-write-heavy SERVER=gunicorn-gevent PORT_9000=http://localhost:9001
	@sleep 10
	-@make test-mixed SERVER=gunicorn-gevent PORT_9000=http://localhost:9001

test-gunicorn-gthread: ## Gunicorn gthread 전체 테스트
	@echo "=== Gunicorn gthread 테스트 ==="
	-@make warmup BASE_URL=http://localhost:9002
	-@make test-read-heavy SERVER=gunicorn-gthread PORT_9000=http://localhost:9002
	@sleep 10
	-@make test-write-heavy SERVER=gunicorn-gthread PORT_9000=http://localhost:9002
	@sleep 10
	-@make test-mixed SERVER=gunicorn-gthread PORT_9000=http://localhost:9002

test-uvicorn: ## Uvicorn 전체 테스트
	@echo "=== Uvicorn 테스트 ==="
	-@make warmup BASE_URL=http://localhost:9003
	-@make test-read-heavy SERVER=uvicorn PORT_9000=http://localhost:9003
	@sleep 10
	-@make test-write-heavy SERVER=uvicorn PORT_9000=http://localhost:9003
	@sleep 10
	-@make test-mixed SERVER=uvicorn PORT_9000=http://localhost:9003

# 서버별 Read-Only 테스트
test-read-only-gunicorn-sync: ## Gunicorn sync Read-Only 테스트
	@echo "=== Gunicorn sync Read-Only 테스트 ==="
	@echo "💡 VU 변경: make test-read-only-gunicorn-sync MAX_VU=300"
	-@make warmup BASE_URL=http://localhost:9000
	-@make test-read-only SERVER=gunicorn-sync PORT_9000=http://localhost:9000

test-read-only-gunicorn-gevent: ## Gunicorn gevent Read-Only 테스트
	@echo "=== Gunicorn gevent Read-Only 테스트 ==="
	@echo "💡 VU 변경: make test-read-only-gunicorn-gevent MAX_VU=300"
	-@make warmup BASE_URL=http://localhost:9001
	-@make test-read-only SERVER=gunicorn-gevent PORT_9000=http://localhost:9001

test-read-only-gunicorn-gthread: ## Gunicorn gthread Read-Only 테스트
	@echo "=== Gunicorn gthread Read-Only 테스트 ==="
	@echo "💡 VU 변경: make test-read-only-gunicorn-gthread MAX_VU=300"
	-@make warmup BASE_URL=http://localhost:9002
	-@make test-read-only SERVER=gunicorn-gthread PORT_9000=http://localhost:9002

test-read-only-uvicorn: ## Uvicorn Read-Only 테스트
	@echo "=== Uvicorn Read-Only 테스트 ==="
	@echo "💡 VU 변경: make test-read-only-uvicorn MAX_VU=300"
	-@make warmup BASE_URL=http://localhost:9003
	-@make test-read-only SERVER=uvicorn PORT_9000=http://localhost:9003

test-all: ## 모든 서버 비교 테스트
	@echo "=== 전체 서버 비교 테스트 시작 ==="
	@make up-all
	@sleep 10
	@make test-gunicorn-sync
	@make reset
	@make test-gunicorn-gevent
	@make reset
	@make test-gunicorn-gthread
	@make reset
	@make test-uvicorn
	@echo "✓ 전체 테스트 완료. results/ 디렉터리 확인"

# 📈 결과 분석
compare: ## 테스트 결과 비교
	@echo "결과 비교 중..."
	@ls -lh results/
	@echo "\n주요 메트릭:"
	@grep -h "http_req_duration" results/*.json | head -10 || true

# 🧼 정리
clean: ## 결과 파일 및 임시 파일 정리
	rm -rf results/
	docker compose down -v
	docker system prune -f

clean-data: ## 데이터 및 볼륨 완전 삭제
	docker compose down -v
	@echo "⚠️ 모든 데이터가 삭제되었습니다"

# 🔍 디버깅
shell: ## Django shell 접속
	docker compose exec web-gunicorn-sync python manage.py shell

dbshell: ## DB shell 접속
	docker compose exec db psql -U postgres -d exbuy

check-health: ## 헬스 체크
	@echo "서버 상태 확인:"
	@curl -s http://localhost:9000/api/health 2>/dev/null && echo "✓ Gunicorn sync (9000)" || echo "✗ Gunicorn sync (9000)"
	@curl -s http://localhost:9001/api/health 2>/dev/null && echo "✓ Gunicorn gevent (9001)" || echo "✗ Gunicorn gevent (9001)"
	@curl -s http://localhost:9002/api/health 2>/dev/null && echo "✓ Gunicorn gthread (9002)" || echo "✗ Gunicorn gthread (9002)"
	@curl -s http://localhost:9003/api/health 2>/dev/null && echo "✓ Uvicorn (9003)" || echo "✗ Uvicorn (9003)"

stats: ## Docker 리소스 사용량
	docker stats --no-stream

# 🚀 빠른 시작
quickstart: ## 빠른 시작 (빌드 → 시작 → 마이그레이션 → 시딩 → 테스트)
	@echo "=== 빠른 시작 ==="
	@make build
	@make up
	@sleep 5
	@make migrate
	@make seed-small
	@make up-sync
	@sleep 5
	@make check-health
	@echo "\n✓ 준비 완료! 테스트 실행:"
	@echo "  make test-read-heavy"
	@echo "  make test-mixed"
