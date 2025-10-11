.PHONY: help build up down migrate seed test-* warmup reset clean

# 기본 설정
SERVER ?= gunicorn-sync
PORT_8000 = http://localhost:8000
PORT_8001 = http://localhost:8001
PORT_8002 = http://localhost:8002
PORT_8003 = http://localhost:8003

help: ## 도움말 표시
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# 🏗️ 환경 구성
build: ## Docker 이미지 빌드
	docker compose build

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
	@echo "워밍업 중..."
	@./warmup.sh || (echo "warmup.sh 실행 실패" && exit 1)
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
	BASE_URL=$(PORT_8000) k6 run \
		--out json=results/$(SERVER)-read-heavy.json \
		--out influxdb=http://localhost:8089/exbuy \
		--log-output=file=../monitoring/k6/logs/$(SERVER)-read-heavy.log \
		k6-scripts/read-heavy.js

test-write-heavy: ## 쓰기 중심 테스트
	@mkdir -p results
	@mkdir -p ../monitoring/k6/logs
	BASE_URL=$(PORT_8000) k6 run \
		--out json=results/$(SERVER)-write-heavy.json \
		--out influxdb=http://localhost:8089/exbuy \
		--log-output=file=../monitoring/k6/logs/$(SERVER)-write-heavy.log \
		k6-scripts/write-heavy.js

test-mixed: ## 혼합 테스트
	@mkdir -p results
	@mkdir -p ../monitoring/k6/logs
	BASE_URL=$(PORT_8000) k6 run \
		--out json=results/$(SERVER)-mixed.json \
		--out influxdb=http://localhost:8089/exbuy \
		--log-output=file=../monitoring/k6/logs/$(SERVER)-mixed.log \
		k6-scripts/mixed.js

# 서버별 전체 테스트
test-gunicorn-sync: ## Gunicorn sync 전체 테스트
	@echo "=== Gunicorn sync 테스트 ==="
	@make warmup
	@make test-read-heavy SERVER=gunicorn-sync PORT_8000=http://localhost:8000
	@sleep 10
	@make test-write-heavy SERVER=gunicorn-sync PORT_8000=http://localhost:8000
	@sleep 10
	@make test-mixed SERVER=gunicorn-sync PORT_8000=http://localhost:8000

test-gunicorn-gevent: ## Gunicorn gevent 전체 테스트
	@echo "=== Gunicorn gevent 테스트 ==="
	@make warmup
	@make test-read-heavy SERVER=gunicorn-gevent PORT_8000=http://localhost:8001
	@sleep 10
	@make test-write-heavy SERVER=gunicorn-gevent PORT_8000=http://localhost:8001
	@sleep 10
	@make test-mixed SERVER=gunicorn-gevent PORT_8000=http://localhost:8001

test-gunicorn-gthread: ## Gunicorn gthread 전체 테스트
	@echo "=== Gunicorn gthread 테스트 ==="
	@make warmup
	@make test-read-heavy SERVER=gunicorn-gthread PORT_8000=http://localhost:8002
	@sleep 10
	@make test-write-heavy SERVER=gunicorn-gthread PORT_8000=http://localhost:8002
	@sleep 10
	@make test-mixed SERVER=gunicorn-gthread PORT_8000=http://localhost:8002

test-uvicorn: ## Uvicorn 전체 테스트
	@echo "=== Uvicorn 테스트 ==="
	@make warmup
	@make test-read-heavy SERVER=uvicorn PORT_8000=http://localhost:8003
	@sleep 10
	@make test-write-heavy SERVER=uvicorn PORT_8000=http://localhost:8003
	@sleep 10
	@make test-mixed SERVER=uvicorn PORT_8000=http://localhost:8003

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
	@curl -s http://localhost:8000/api/health 2>/dev/null && echo "✓ Gunicorn sync (8000)" || echo "✗ Gunicorn sync (8000)"
	@curl -s http://localhost:8001/api/health 2>/dev/null && echo "✓ Gunicorn gevent (8001)" || echo "✗ Gunicorn gevent (8001)"
	@curl -s http://localhost:8002/api/health 2>/dev/null && echo "✓ Gunicorn gthread (8002)" || echo "✗ Gunicorn gthread (8002)"
	@curl -s http://localhost:8003/api/health 2>/dev/null && echo "✓ Uvicorn (8003)" || echo "✗ Uvicorn (8003)"

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
