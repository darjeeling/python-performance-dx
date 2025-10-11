#!/bin/bash

set -e

echo "=== Monitoring Stack Setup ==="
echo ""

# 1. .env 파일 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다."
    echo ""
    echo "다음 명령으로 .env 파일을 생성해주세요:"
    echo "  cp .env.example .env"
    echo ""
    echo "그 다음 .env 파일을 편집하여 DATA_DIR과 CFG_DIR을 설정하세요."
    exit 1
fi

echo "✓ .env 파일 발견"

# 2. 현재 사용자의 UID/GID 가져오기
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

echo "✓ 현재 사용자 UID=$CURRENT_UID, GID=$CURRENT_GID"

# 3. .env 파일에 UID/GID 업데이트
echo "→ .env 파일에 UID/GID 업데이트 중..."

# macOS와 Linux 모두 호환되는 sed 사용
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^UID=.*/UID=$CURRENT_UID/" .env
    sed -i '' "s/^GID=.*/GID=$CURRENT_GID/" .env
else
    # Linux
    sed -i "s/^UID=.*/UID=$CURRENT_UID/" .env
    sed -i "s/^GID=.*/GID=$CURRENT_GID/" .env
fi

echo "✓ UID/GID 업데이트 완료"

# 4. .env 파일에서 환경 변수 읽기
source .env

if [ -z "$DATA_DIR" ] || [ -z "$CFG_DIR" ]; then
    echo "❌ .env 파일에 DATA_DIR 또는 CFG_DIR이 설정되지 않았습니다."
    exit 1
fi

echo "✓ 설정 읽기 완료:"
echo "  DATA_DIR=$DATA_DIR"
echo "  CFG_DIR=$CFG_DIR"
echo ""

# 5. DATA_DIR 및 하위 디렉토리 생성
echo "→ DATA_DIR 디렉토리 생성 중..."
mkdir -p "$DATA_DIR"/{victoria-metrics,vmagent,grafana,loki}
echo "✓ DATA_DIR 디렉토리 생성 완료"

# 6. CFG_DIR 생성
echo "→ CFG_DIR 디렉토리 생성 중..."
mkdir -p "$CFG_DIR"
echo "✓ CFG_DIR 디렉토리 생성 완료"

# 7. 설정 파일들을 CFG_DIR로 rsync
echo "→ 설정 파일 복사 중..."

for dir in grafana loki promtail vmagent k6; do
    if [ -d "$dir" ]; then
        echo "  - $dir -> $CFG_DIR/$dir"
        rsync -av --delete "$dir/" "$CFG_DIR/$dir/"
    else
        echo "  ⚠ 경고: $dir 디렉토리를 찾을 수 없습니다."
    fi
done

echo "✓ 설정 파일 복사 완료"

# 8. 권한 설정
echo "→ 디렉토리 권한 설정 중..."
chown -R $CURRENT_UID:$CURRENT_GID "$DATA_DIR" 2>/dev/null || \
    echo "  ⚠ 권한 설정 실패 (sudo 필요할 수 있음): $DATA_DIR"

chown -R $CURRENT_UID:$CURRENT_GID "$CFG_DIR" 2>/dev/null || \
    echo "  ⚠ 권한 설정 실패 (sudo 필요할 수 있음): $CFG_DIR"

echo "✓ 권한 설정 완료 (또는 스킵)"

echo ""
echo "=== 설정 완료! ==="
echo ""
echo "이제 다음 명령으로 Docker Compose를 실행할 수 있습니다:"
echo "  docker-compose up -d"
echo ""
