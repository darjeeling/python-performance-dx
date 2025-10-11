#!/bin/bash

# ExBuy 성능 테스트 실행 스크립트

echo "==================================="
echo "ExBuy Performance Testing Suite"
echo "==================================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 서비스 상태 확인
check_service() {
    local url=$1
    local name=$2

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
        echo -e "${GREEN}✓${NC} $name is running"
        return 0
    else
        echo -e "${YELLOW}✗${NC} $name is not responding"
        return 1
    fi
}

# 1. 서비스 시작
echo -e "${BLUE}1. Starting services...${NC}"
docker compose up -d
echo ""

# 2. 서비스 대기
echo -e "${BLUE}2. Waiting for services to be ready...${NC}"
sleep 5

# 3. 서비스 상태 확인
echo -e "${BLUE}3. Checking services...${NC}"
check_service "http://localhost:8000/api/health" "ExBuy API"
echo ""

# 4. 데이터 시딩 여부 확인
echo -e "${BLUE}4. Do you want to seed data? (y/n)${NC}"
read -r seed_response

if [[ "$seed_response" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Seeding data...${NC}"
    docker compose exec web python manage.py seed_data \
        --products 1000 \
        --orders 5000 \
        --reviews 10000
    echo ""
fi

# 5. 테스트 시나리오 선택
echo -e "${BLUE}5. Select load test scenario:${NC}"
echo "1) Read-heavy (80% reads, 20% writes)"
echo "2) Write-heavy (30% reads, 70% writes)"
echo "3) Mixed (60% reads, 40% writes)"
echo "4) All scenarios"
echo "5) Skip load test"
echo ""
read -p "Enter choice (1-5): " choice

mkdir -p ../monitoring/k6/logs

case $choice in
    1)
        echo -e "${BLUE}Running read-heavy scenario...${NC}"
        k6 run \
            --out influxdb=http://localhost:8089/exbuy \
            --log-output=file=../monitoring/k6/logs/read-heavy.log \
            k6-scripts/read-heavy.js
        ;;
    2)
        echo -e "${BLUE}Running write-heavy scenario...${NC}"
        k6 run \
            --out influxdb=http://localhost:8089/exbuy \
            --log-output=file=../monitoring/k6/logs/write-heavy.log \
            k6-scripts/write-heavy.js
        ;;
    3)
        echo -e "${BLUE}Running mixed scenario...${NC}"
        k6 run \
            --out influxdb=http://localhost:8089/exbuy \
            --log-output=file=../monitoring/k6/logs/mixed.log \
            k6-scripts/mixed.js
        ;;
    4)
        echo -e "${BLUE}Running all scenarios...${NC}"
        echo -e "\n${YELLOW}=== Read-Heavy ===${NC}"
        k6 run \
            --out influxdb=http://localhost:8089/exbuy \
            --log-output=file=../monitoring/k6/logs/all-read-heavy.log \
            k6-scripts/read-heavy.js
        echo -e "\n${YELLOW}=== Write-Heavy ===${NC}"
        k6 run \
            --out influxdb=http://localhost:8089/exbuy \
            --log-output=file=../monitoring/k6/logs/all-write-heavy.log \
            k6-scripts/write-heavy.js
        echo -e "\n${YELLOW}=== Mixed ===${NC}"
        k6 run \
            --out influxdb=http://localhost:8089/exbuy \
            --log-output=file=../monitoring/k6/logs/all-mixed.log \
            k6-scripts/mixed.js
        ;;
    5)
        echo -e "${YELLOW}Skipping load test${NC}"
        ;;
    *)
        echo -e "${YELLOW}Invalid choice. Skipping load test.${NC}"
        ;;
esac

echo ""
echo -e "${GREEN}==================================="
echo "Testing complete!"
echo "===================================${NC}"
echo ""
echo "Useful commands:"
echo "  - View logs: docker compose logs -f web"
echo "  - Stop services: docker compose down"
echo "  - View metrics: curl http://localhost:8000/metrics"
echo "  - Django admin: http://localhost:8000/admin"
echo ""
