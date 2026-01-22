#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR=${1:-allure-report}
MODE=${2:-serve}

if [ ! -f "${REPORT_DIR}/index.html" ]; then
  echo "Allure report not found at ${REPORT_DIR}/index.html. Run 'make allure' first." >&2
  exit 1
fi

PORT=$(PREFERRED_PORT=8000 python3 - <<'PY'
import os
import socket

preferred = int(os.environ.get("PREFERRED_PORT", "8000"))

def is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False

if is_free(preferred):
    print(preferred)
else:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        print(sock.getsockname()[1])
PY
)

URL="http://localhost:${PORT}/"

if [ "${MODE}" = "open" ]; then
  (cd "${REPORT_DIR}" && nohup python3 -m http.server "${PORT}" --bind 127.0.0.1 >/tmp/allure-server.log 2>&1 &)
  echo "Allure report server started at: ${URL}"
  if command -v explorer.exe >/dev/null 2>&1; then
    explorer.exe "${URL}" >/dev/null 2>&1 || true
  fi
else
  echo "Serving Allure report at: ${URL}"
  cd "${REPORT_DIR}"
  exec python3 -m http.server "${PORT}" --bind 127.0.0.1
fi
