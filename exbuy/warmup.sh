#!/bin/bash

# ExBuy 캐시 워밍업 스크립트
# DB 및 애플리케이션 캐시를 워밍업하여 성능 테스트 정확도 향상

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 기본 URL
BASE_URL=${BASE_URL:-http://localhost:8000}

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}  ExBuy Cache Warmup${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# 1. 헬스 체크
echo -e "${YELLOW}1. Checking server health...${NC}"
if curl -sf "$BASE_URL/api/health" > /dev/null; then
    echo -e "${GREEN}✓ Server is healthy${NC}"
else
    echo -e "${RED}✗ Server is not responding${NC}"
    exit 1
fi
echo ""

# 2. Product 캐시 워밍업
echo -e "${YELLOW}2. Warming up product cache (100 products)...${NC}"
for i in {1..100}; do
    curl -sf "$BASE_URL/api/products/$i" > /dev/null || true
    if [ $((i % 20)) -eq 0 ]; then
        echo -e "  → $i/100 completed"
    fi
done
echo -e "${GREEN}✓ Product cache warmed up${NC}"
echo ""

# 3. Product list 페이지 워밍업
echo -e "${YELLOW}3. Warming up product list pages (10 pages)...${NC}"
for i in {1..10}; do
    curl -sf "$BASE_URL/api/products?page=$i" > /dev/null || true
done
echo -e "${GREEN}✓ Product list cache warmed up${NC}"
echo ""

# 4. Category 필터 워밍업
echo -e "${YELLOW}4. Warming up category filters...${NC}"
categories=("electronics" "clothing" "food" "books" "home")
for category in "${categories[@]}"; do
    curl -sf "$BASE_URL/api/products?category=$category" > /dev/null || true
    echo -e "  → $category"
done
echo -e "${GREEN}✓ Category filters warmed up${NC}"
echo ""

# 5. Order 캐시 워밍업
echo -e "${YELLOW}5. Warming up order cache (50 orders)...${NC}"
for i in {1..50}; do
    curl -sf "$BASE_URL/api/orders/$i" > /dev/null || true
done
echo -e "${GREEN}✓ Order cache warmed up${NC}"
echo ""

# 6. Review 캐시 워밍업
echo -e "${YELLOW}6. Warming up review cache...${NC}"
for i in {1..20}; do
    curl -sf "$BASE_URL/api/reviews?product_id=$i" > /dev/null || true
done
echo -e "${GREEN}✓ Review cache warmed up${NC}"
echo ""

# 7. 통계 API 워밍업
echo -e "${YELLOW}7. Warming up stats API...${NC}"
curl -sf "$BASE_URL/api/stats/top-products?limit=10" > /dev/null || true
curl -sf "$BASE_URL/api/stats/top-products?limit=20" > /dev/null || true
echo -e "${GREEN}✓ Stats cache warmed up${NC}"
echo ""

# 8. 검색 API 워밍업
echo -e "${YELLOW}8. Warming up search API...${NC}"
search_terms=("book" "phone" "laptop" "shirt" "food")
for term in "${search_terms[@]}"; do
    curl -sf "$BASE_URL/api/search/products?q=$term" > /dev/null || true
done
echo -e "${GREEN}✓ Search cache warmed up${NC}"
echo ""

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  Warmup completed successfully!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "You can now run performance tests with accurate results."
echo ""
