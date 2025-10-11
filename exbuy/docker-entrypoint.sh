#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done

echo "PostgreSQL is ready!"

# 전달된 명령이 있으면 그것을 실행
if [ $# -gt 0 ]; then
    exec "$@"
fi

# 명령이 없으면 기본 동작: 마이그레이션 + 서버 시작
python manage.py migrate --noinput

# 서버 타입에 따라 실행 (기본: gunicorn)
SERVER_TYPE=${SERVER_TYPE:-gunicorn}

if [ "$SERVER_TYPE" = "uvicorn" ]; then
    echo "Starting with Gunicorn + UvicornWorker (ASGI)..."
    exec gunicorn config.asgi:application \
        --bind 0.0.0.0:8000 \
        --workers ${WORKERS:-4} \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout ${TIMEOUT:-120} \
        --access-logfile - \
        --error-logfile - \
        --log-level ${LOG_LEVEL:-info}
else
    echo "Starting with Gunicorn (WSGI)..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers ${WORKERS:-4} \
        --worker-class ${WORKER_CLASS:-sync} \
        --timeout ${TIMEOUT:-120} \
        --access-logfile - \
        --error-logfile - \
        --log-level ${LOG_LEVEL:-info}
fi
