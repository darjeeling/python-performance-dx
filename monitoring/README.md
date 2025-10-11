# 📊 Docker 기반 모니터링 스택 (VictoriaMetrics + Loki + Promtail + cAdvisor + Grafana)

이 스택은 Django/DRF 및 성능 테스트(k6 등) 환경을 위한 통합 모니터링
시스템으로,\
**메트릭과 로그를 수집해 Grafana에서 시각화**합니다.

------------------------------------------------------------------------

## 🧩 구성 요소

  서비스            포트     설명
  ----------------- -------- -----------------------------
  Grafana           `3000`   시각화 UI
  Loki              `3100`   로그 저장소
  VictoriaMetrics   `8428`   메트릭 저장소 (PromQL 호환)
  vmagent           `8429`   메트릭 수집기
  cAdvisor          `8080`   컨테이너 리소스 수집기

------------------------------------------------------------------------

## ⚙️ 환경 변수 (`.env`)

``` bash
# 모든 데이터(영속 스토리지)가 저장될 경로
DATA_DIR=/opt/monitoring-data

# 설정 파일 루트 경로
CFG_DIR=.
```

------------------------------------------------------------------------

## 📁 디렉터리 구조

    monitoring/
    ├─ docker-compose.yml
    ├─ .env
    ├─ loki/
    │   └─ loki-config.yaml
    ├─ promtail/
    │   └─ promtail-config.yaml
    ├─ vmagent/
    │   └─ prometheus-vm-single.yml
    ├─ grafana/
    │   ├─ provisioning/
    │   │   ├─ datasources/single.yml
    │   │   └─ dashboards/dashboard.yml
    │   └─ dashboards/
    │       ├─ victoriametrics/
    │       ├─ loki/
    │       ├─ cadvisor/
    │       └─ promtail/
    └─ k6/
        └─ logs/

------------------------------------------------------------------------

## 🚀 실행 및 종료

``` bash
# 실행
docker compose up -d

# 로그 보기
docker compose logs -f

# 중지
docker compose down
```

------------------------------------------------------------------------

## 🔍 주요 포트 요약

  서비스            포트   설명
  ----------------- ------ ------------------------
  Grafana           3000   대시보드 UI
  Loki              3100   로그 API
  VictoriaMetrics   8428   메트릭 API
  vmagent           8429   메트릭 수집기
  cAdvisor          8080   컨테이너 리소스 수집기

------------------------------------------------------------------------

## 📊 Grafana 대시보드 구성

`grafana/provisioning/dashboards/dashboard.yml` 에 정의된 폴더 구조에
따라\
아래 대시보드들이 자동 등록됩니다.

  폴더                 내용
  -------------------- ---------------------------------------
  `victoriametrics/`   VictoriaMetrics / vmagent 상태
  `loki/`              Loki 로그 ingestion 및 요청량
  `cadvisor/`          컨테이너 리소스 (CPU, 메모리, I/O 등)
  `promtail/`          로그 수집량 / 드롭 / 타겟 상태

------------------------------------------------------------------------

## 🧾 vmagent 메트릭 수집 대상

``` yaml
scrape_configs:
  - job_name: cadvisor
    static_configs:
      - targets: ["cadvisor:8080"]
  - job_name: victoriametrics-self
    static_configs:
      - targets: ["victoriametrics:8428"]
  - job_name: vmagent-self
    static_configs:
      - targets: ["vmagent:8429"]
  - job_name: loki
    static_configs:
      - targets: ["loki:3100"]
  - job_name: promtail
    static_configs:
      - targets: ["promtail:9080"]
```

------------------------------------------------------------------------

## 🪵 Promtail 로그 수집 경로

  소스                   경로                           설명
  ---------------------- ------------------------------ ------------------
  Docker 컨테이너 로그   `/var/lib/docker/containers`   stdout/stderr
  시스템 로그            `/var/log`                     OS 로그
  k6 로그                `${CFG_DIR}/k6/logs/*.log`     부하 테스트 로그

Promtail → Loki(`http://loki:3100`) 로 전송합니다.

------------------------------------------------------------------------

## 🧠 운영 팁

-   **데이터 백업:** `${DATA_DIR}` 경로를 주기적으로 백업하세요.
-   **CPU 핀닝:** 성능 테스트 시 모니터링/테스트/DB를 분리하면 정확도
    향상.
-   **보안:** Grafana 기본 비밀번호(`admin/admin`)는 변경 필수.
-   **로그 회전:** Promtail은 오래된 로그를 자동 삭제하지 않으므로
    logrotate 병행 권장.

------------------------------------------------------------------------

## 📘 Grafana Explore 테스트용 쿼리

### 🔹 PromQL 예시 (메트릭 조회)

  ----------------------------------------------------------------------------------------------------------------
  설명                                쿼리
  ----------------------------------- ----------------------------------------------------------------------------
  컨테이너 CPU Top5                   `topk(5, sum(rate(container_cpu_usage_seconds_total[1m])) by (container))`

  컨테이너 메모리 Top5                `topk(5, max(container_memory_usage_bytes) by (container))`

  VictoriaMetrics Ingest 속도         `sum(rate(victoria_metrics_ingested_samples_total[1m]))`

  vmagent Remote Write 전송률         `sum(rate(vmagent_remotewrite_rows_sent_total[1m])) by (url)`

  Loki 로그 처리량                    `sum(rate(loki_ingester_ingested_lines_total[1m]))`

  Promtail 로그 전송 속도             `sum(rate(loki_promtail_entries_total[1m]))`

  Promtail Dropped 로그               `sum(rate(loki_promtail_dropped_entries_total[1m]))`

  cAdvisor 네트워크 송수신            `sum(rate(container_network_receive_bytes_total[1m])) by (container)`
  ----------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

### 🔹 LogQL 예시 (로그 조회)

  설명                 쿼리
  -------------------- -------------------------------
  전체 로그            `{job="docker"}`
  특정 컨테이너 로그   `{container="webapp"}`
  에러 로그            `{job="docker"} |= "ERROR"`
  k6 로그              `{job="k6"} |~ "rps|latency"`

------------------------------------------------------------------------

## 🧩 서비스 요약

  서비스              역할                내부 주소
  ------------------- ------------------- ------------------------
  `victoriametrics`   메트릭 저장소       `victoriametrics:8428`
  `vmagent`           메트릭 수집기       `vmagent:8429`
  `grafana`           시각화 UI           `grafana:3000`
  `loki`              로그 저장소         `loki:3100`
  `promtail`          로그 수집기         `promtail:9080`
  `cadvisor`          컨테이너 모니터링   `cadvisor:8080`

------------------------------------------------------------------------

## 🧪 초기 점검 절차

1.  `docker compose up -d`

2.  `docker compose ps` 로 컨테이너 상태 확인

3.  Grafana 접속 → 데이터소스 "VictoriaMetrics" 선택

4.  Explore 에서 PromQL 실행:

    ``` promql
    up
    ```

5.  로그 탐색:

    ``` logql
    {job="docker"}
    ```

------------------------------------------------------------------------

## 📦 데이터 초기화 (주의!)

``` bash
docker compose down
sudo rm -rf $DATA_DIR/*
```

⚠️ 모든 메트릭 / 로그 데이터가 삭제됩니다.

------------------------------------------------------------------------

## 📚 참고 문서

-   [VictoriaMetrics Docs](https://docs.victoriametrics.com/)
-   [Grafana Loki Docs](https://grafana.com/docs/loki/latest/)
-   [Promtail
    Docs](https://grafana.com/docs/loki/latest/clients/promtail/)
-   [cAdvisor Docs](https://github.com/google/cadvisor)
