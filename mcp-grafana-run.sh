#!/usr/bin/env bash

source .env
docker run --rm -p 8000:8000 \
        -e GRAFANA_URL=$GRAFANA_URL \
        -e GRAFANA_SERVICE_ACCOUNT_TOKEN=$SERVICE_ACCOUNT_TOKEN \
        mcp/grafana
