#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR=${1:-allure-report}
MODE=${2:-serve}
RESULTS_DIR=${3:-allure-results}

ALLURE_BIN=$(command -v allure || true)

if [ ! -d "${RESULTS_DIR}" ] && [ ! -d "${REPORT_DIR}" ]; then
  echo "Allure results not found at ${RESULTS_DIR} and report not found at ${REPORT_DIR}." >&2
  echo "Run 'make test' and 'make allure' first." >&2
  exit 1
fi

PORT=$(PREFERRED_PORT=8000 python3 - <<'PY'
import os
import socket

preferred = int(os.environ.get("PREFERRED_PORT", "8000"))


def is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


if is_free(preferred):
    print(preferred)
else:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("0.0.0.0", 0))
        print(sock.getsockname()[1])
PY
)

URL="http://localhost:${PORT}/"

open_url() {
  if command -v explorer.exe >/dev/null 2>&1; then
    explorer.exe "${URL}" >/dev/null 2>&1 || true
  fi
}

serve_allure_results() {
  if [ -z "${ALLURE_BIN}" ]; then
    return 1
  fi
  if [ ! -d "${RESULTS_DIR}" ]; then
    return 1
  fi

  if [ "${MODE}" = "open" ]; then
    nohup "${ALLURE_BIN}" serve "${RESULTS_DIR}" --host localhost --port "${PORT}" \
      >/tmp/allure-serve.log 2>&1 &
    echo "Allure report server started at: ${URL}"
    open_url
    return 0
  fi

  echo "Serving Allure results at: ${URL}"
  exec "${ALLURE_BIN}" serve "${RESULTS_DIR}" --host localhost --port "${PORT}"
}

serve_report_dir() {
  if [ ! -f "${REPORT_DIR}/index.html" ]; then
    echo "Allure report not found at ${REPORT_DIR}/index.html. Run 'make allure' first." >&2
    exit 1
  fi

  if [ "${MODE}" = "open" ] || [ "${MODE}" = "open-report" ]; then
    nohup python3 -m http.server "${PORT}" --directory "${REPORT_DIR}" --bind 0.0.0.0 \
      >/tmp/allure-server.log 2>&1 &
    echo "Allure report server started at: ${URL}"
    open_url
    return 0
  fi

  echo "Serving Allure report at: ${URL}"
  exec python3 -m http.server "${PORT}" --directory "${REPORT_DIR}" --bind 0.0.0.0
}

case "${MODE}" in
  serve-report|open-report)
    serve_report_dir
    ;;
  serve|open)
    if ! serve_allure_results; then
      serve_report_dir
    fi
    ;;
  *)
    echo "Unknown mode: ${MODE}. Use serve, open, serve-report, or open-report." >&2
    exit 1
    ;;
esac
