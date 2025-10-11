#!/bin/bash

# ExBuy 테스트 데이터 리셋 스크립트
# 테스트 간 일관성을 위해 재고 및 주문 상태 초기화

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}  ExBuy Test Data Reset${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# 리셋 방법 선택
echo -e "${YELLOW}Select reset method:${NC}"
echo "1) Quick reset (재고 복구, 빠름)"
echo "2) Full reset (데이터 재생성, 느림)"
echo ""
read -p "Enter choice (1-2): " choice

case $choice in
    1)
        echo -e "${BLUE}Quick reset: 재고 복구 중...${NC}"

        # PostgreSQL 명령어로 재고 초기화
        docker compose exec -T db psql -U postgres -d exbuy << EOF
        -- 모든 상품 재고를 랜덤 값으로 리셋
        UPDATE shop_product SET stock = floor(random() * 1000)::int WHERE id > 0;

        -- 통계 출력
        SELECT
            '✓ Products' as item,
            count(*) as total,
            avg(stock)::int as avg_stock
        FROM shop_product
        UNION ALL
        SELECT
            '✓ Orders' as item,
            count(*) as total,
            0 as avg_stock
        FROM shop_order
        UNION ALL
        SELECT
            '✓ Reviews' as item,
            count(*) as total,
            0 as avg_stock
        FROM shop_review;
EOF

        echo -e "${GREEN}✓ Quick reset completed${NC}"
        ;;

    2)
        echo -e "${BLUE}Full reset: 데이터 재생성 중...${NC}"
        echo -e "${YELLOW}기존 데이터를 삭제하고 새로 생성합니다${NC}"
        echo ""

        # 데이터 규모 선택
        echo "Select data size:"
        echo "1) Small (1K/5K/10K)"
        echo "2) Medium (10K/50K/100K)"
        echo "3) Large (100K/500K/1M)"
        echo ""
        read -p "Enter choice (1-3): " size_choice

        case $size_choice in
            1)
                PRODUCTS=1000
                ORDERS=5000
                REVIEWS=10000
                ;;
            2)
                PRODUCTS=10000
                ORDERS=50000
                REVIEWS=100000
                ;;
            3)
                PRODUCTS=100000
                ORDERS=500000
                REVIEWS=1000000
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                exit 1
                ;;
        esac

        echo -e "${YELLOW}Generating data: $PRODUCTS products, $ORDERS orders, $REVIEWS reviews${NC}"

        # 데이터 재생성
        docker compose run --rm web-gunicorn-sync python manage.py seed_data \
            --products $PRODUCTS \
            --orders $ORDERS \
            --reviews $REVIEWS \
            --batch-size 1000

        echo -e "${GREEN}✓ Full reset completed${NC}"
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  Reset completed successfully!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "Next steps:"
echo "  1. make warmup    # 캐시 워밍업"
echo "  2. make test-*    # 성능 테스트 실행"
echo ""
