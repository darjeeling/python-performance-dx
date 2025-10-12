

docker pull mcp/grafana

SERVICE_ACCOUNT_TOKEN=YOURS
GRAFANA_URL=http://127.0.0.1:3000/
docker run --rm -p 8000:8000 \
        -e GRAFANA_URL=$GRAFANA_URL \
        -e GRAFANA_SERVICE_ACCOUNT_TOKEN=$SERVICE_ACCOUNT_TOKEN \
        mcp/grafana


claude mcp add --transport sse grafana http://127.0.0.1:8000/sse

