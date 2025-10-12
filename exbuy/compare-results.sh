#!/bin/bash

# ExBuy 테스트 결과 비교 스크립트
# results/*.json 파일을 분석하여 주요 메트릭 비교

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

RESULTS_DIR="results"

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}  ExBuy Test Results Comparison${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# 결과 파일 확인
if [ ! -d "$RESULTS_DIR" ] || [ -z "$(ls -A $RESULTS_DIR/*.json 2>/dev/null)" ]; then
    echo -e "${RED}결과 파일이 없습니다. 먼저 테스트를 실행하세요.${NC}"
    echo "예: make test-read-heavy SERVER=gunicorn-sync"
    exit 1
fi

# 임시 파일
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# JSON 파일에서 메트릭 추출 함수
extract_metrics() {
    local file=$1
    local filename=$(basename "$file" .json)

    # 파일에서 마지막 metrics 블록 추출
    if ! cat "$file" | jq -r 'select(.type == "Point" and .metric == "http_req_duration") | .data.value' 2>/dev/null | tail -1 > /dev/null; then
        return 1
    fi

    # 주요 메트릭 추출
    local p95=$(cat "$file" | jq -r 'select(.type == "Point" and .metric == "http_req_duration" and .data.tags.expected_response == "true") | .data.value' 2>/dev/null | awk '{sum+=$1; n++} END {if(n>0) print sum/n; else print "N/A"}')
    local p99=$(cat "$file" | jq -r 'select(.type == "Point" and .metric == "http_req_duration") | .data.value' 2>/dev/null | sort -n | tail -1)
    local rps=$(cat "$file" | jq -r 'select(.type == "Point" and .metric == "http_reqs") | .data.value' 2>/dev/null | awk '{sum+=$1} END {print sum}')
    local error_rate=$(cat "$file" | jq -r 'select(.type == "Point" and .metric == "http_req_failed") | .data.value' 2>/dev/null | awk '{sum+=$1; n++} END {if(n>0) print sum/n*100; else print "0"}')

    # 파일명에서 서버와 시나리오 파싱
    local server=$(echo "$filename" | cut -d'-' -f1-2)
    local scenario=$(echo "$filename" | cut -d'-' -f3-)

    echo "$server|$scenario|${p95:-N/A}|${p99:-N/A}|${rps:-N/A}|${error_rate:-N/A}" >> $TEMP_FILE
}

# 모든 JSON 파일 처리
echo -e "${YELLOW}결과 파일 분석 중...${NC}"
for file in $RESULTS_DIR/*.json; do
    extract_metrics "$file" || echo -e "${YELLOW}Warning: $file 파싱 실패${NC}"
done

# 결과가 있는지 확인
if [ ! -s "$TEMP_FILE" ]; then
    echo -e "${RED}분석 가능한 메트릭을 찾을 수 없습니다.${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}=== 서버별 성능 비교 ===${NC}"
echo ""

# 헤더 출력
printf "${CYAN}%-20s %-15s %15s %15s %15s %15s${NC}\n" \
    "Server" "Scenario" "Avg Latency(ms)" "Max Latency(ms)" "Total Reqs" "Error Rate(%)"
echo "--------------------------------------------------------------------------------------------------------"

# 결과 출력 (정렬)
sort -t'|' -k1,1 -k2,2 "$TEMP_FILE" | while IFS='|' read -r server scenario p95 p99 rps error_rate; do
    # 숫자 포맷팅
    if [ "$p95" != "N/A" ]; then
        p95=$(printf "%.2f" "$p95")
    fi
    if [ "$p99" != "N/A" ]; then
        p99=$(printf "%.2f" "$p99")
    fi
    if [ "$rps" != "N/A" ]; then
        rps=$(printf "%.0f" "$rps")
    fi
    if [ "$error_rate" != "N/A" ]; then
        error_rate=$(printf "%.2f" "$error_rate")
    fi

    # 색상 적용 (에러율에 따라)
    if [ "$error_rate" != "N/A" ] && (( $(echo "$error_rate > 5" | bc -l 2>/dev/null || echo 0) )); then
        COLOR=$RED
    elif [ "$error_rate" != "N/A" ] && (( $(echo "$error_rate > 1" | bc -l 2>/dev/null || echo 0) )); then
        COLOR=$YELLOW
    else
        COLOR=$GREEN
    fi

    printf "${COLOR}%-20s %-15s %15s %15s %15s %15s${NC}\n" \
        "$server" "$scenario" "$p95" "$p99" "$rps" "$error_rate"
done

echo ""

# 테스트 이력 표시
HISTORY_FILE="$RESULTS_DIR/test-history.jsonl"
if [ -f "$HISTORY_FILE" ]; then
    echo -e "${CYAN}=== 최근 테스트 실행 이력 (최근 10개) ===${NC}"
    echo ""
    tail -20 "$HISTORY_FILE" | \
        jq -r 'select(.event == "start") | [.timestamp, .server, .scenario, .max_vu, .duration, .workers] | @tsv' 2>/dev/null | \
        tail -10 | \
        awk 'BEGIN {printf "%-20s %-20s %-15s %10s %10s %10s\n", "Timestamp", "Server", "Scenario", "VU", "Duration", "Workers";
                    print "---------------------------------------------------------------------------------------------------"}
             {printf "%-20s %-20s %-15s %10s %10s %10s\n", $1, $2, $3, $4, $5, $6}'
    echo ""
fi

# 권장 사항
echo -e "${CYAN}=== 권장 사항 ===${NC}"
echo ""
echo "1. 에러율이 5% 이상인 테스트는 재실행을 권장합니다."
echo "2. 지연시간이 1000ms 이상인 경우 최적화가 필요합니다."
echo "3. Grafana 대시보드에서 상세 메트릭을 확인하세요: http://localhost:3000"
echo ""

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  분석 완료!${NC}"
echo -e "${GREEN}==================================${NC}"
