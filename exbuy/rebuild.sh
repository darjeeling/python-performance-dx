#!/bin/bash

# ExBuy Docker 이미지 완전 재빌드 스크립트
# --no-cache 옵션으로 모든 캐시를 무시하고 처음부터 다시 빌드

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}  ExBuy Docker Image Rebuild${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# 경고 메시지
echo -e "${RED}⚠️  WARNING: This will rebuild all Docker images from scratch${NC}"
echo -e "${RED}   - All running containers will be stopped${NC}"
echo -e "${RED}   - Existing images will be removed${NC}"
echo -e "${RED}   - Build cache will be cleared${NC}"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi
echo ""

# 1. 컨테이너 중지
echo -e "${YELLOW}1. Stopping all ExBuy containers...${NC}"
docker compose down || true
echo -e "${GREEN}✓ Containers stopped${NC}"
echo ""

# 2. 기존 이미지 삭제
echo -e "${YELLOW}2. Removing existing ExBuy images...${NC}"
# exbuy로 시작하는 이미지와 현재 디렉토리 이름으로 생성된 이미지 삭제
docker images | grep "exbuy" | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
echo -e "${GREEN}✓ Old images removed${NC}"
echo ""

# 3. 빌드 캐시 정리
echo -e "${YELLOW}3. Clearing build cache...${NC}"
docker builder prune -f
echo -e "${GREEN}✓ Build cache cleared${NC}"
echo ""

# 4. 새로 빌드 (--no-cache)
echo -e "${YELLOW}4. Building images from scratch (this may take a while)...${NC}"
docker compose build --no-cache --progress=plain
echo -e "${GREEN}✓ Images rebuilt successfully${NC}"
echo ""

# 5. Dangling 이미지 정리
echo -e "${YELLOW}5. Cleaning up dangling images...${NC}"
docker image prune -f
echo -e "${GREEN}✓ Cleanup completed${NC}"
echo ""

# 6. 이미지 목록 확인
echo -e "${YELLOW}6. Verifying built images...${NC}"
docker images | grep -E "REPOSITORY|exbuy"
echo ""

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  Rebuild completed successfully!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "You can now start services with:"
echo "  make up-sync      # Start Gunicorn sync (port 9000)"
echo "  make up-gevent    # Start Gunicorn gevent (port 9001)"
echo "  make up-gthread   # Start Gunicorn gthread (port 9002)"
echo "  make up-uvicorn   # Start Uvicorn (port 9003)"
echo "  make up-all       # Start all servers"
echo ""
