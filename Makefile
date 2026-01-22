IMAGE=aqa
RESULTS=allure-results
REPORT=allure-report
ARTIFACTS=artifacts
DOCKER_BIN=$(shell command -v docker 2>/dev/null)
HOST_UID=$(shell id -u)
HOST_GID=$(shell id -g)
DOCKER_USER=$(HOST_UID):$(HOST_GID)

.PHONY: docker-build test allure doctor serve-report serve open clean debug-driver test-local test-local-wsl

docker-build:
	@if [ -z "$(DOCKER_BIN)" ]; then \
		echo "Docker not found. Install Docker Desktop and enable WSL integration."; \
		exit 1; \
	fi
	@docker info >/dev/null 2>&1 || { \
		echo "Docker daemon is not running. Start Docker Desktop."; \
		exit 1; \
	}
	docker build -t $(IMAGE) .

test: docker-build
	mkdir -p $(RESULTS) $(ARTIFACTS)
	docker run --rm --user $(DOCKER_USER) \
		-v "$$PWD:/app" \
		-w /app \
		-e ALLURE_RESULTS_DIR=/app/$(RESULTS) \
		$(IMAGE) pytest src/tests --alluredir=$(RESULTS)

allure: test
	@if [ -d "$(REPORT)" ]; then rm -rf $(REPORT); fi
	mkdir -p $(REPORT)
	docker run --rm \
		--user $(DOCKER_USER) \
		-v "$$PWD:/app" \
		-w /app \
		$(IMAGE) allure generate $(RESULTS) -o $(REPORT) --clean

doctor:
	@echo "== Versions =="
	@python -V
	@python -m pip -V
	@command -v chromium >/dev/null 2>&1 && chromium --version || echo "chromium: not found"
	@command -v chromedriver >/dev/null 2>&1 && chromedriver --version || echo "chromedriver: not found"
	@command -v java >/dev/null 2>&1 && java -version || echo "java: not found"
	@if [ -n "$(DOCKER_BIN)" ]; then docker --version; else echo "docker: not found"; fi
	@echo "== Required files =="
	@test -f requirements.txt
	@test -f Dockerfile
	@test -f README.md
	@test -f pytest.ini
	@test -d src/pages
	@test -d src/tests
	@echo "== Quick checks =="
	@python -m compileall -q .
	@python -m pytest -q --collect-only
	@if [ -n "$(DOCKER_BIN)" ]; then \
		echo "== Docker smoke =="; \
		docker info >/dev/null 2>&1 || { echo "Docker daemon not running"; exit 1; }; \
		docker build -t $(IMAGE) .; \
		docker run --rm --user $(DOCKER_USER) -v "$$PWD:/app" -w /app $(IMAGE) pytest -q --collect-only; \
	else \
		echo "Docker smoke skipped (docker not available)."; \
	fi

serve-report:
	@./scripts/allure_report_server.sh "$(REPORT)" serve-report "$(RESULTS)"

serve: serve-report

open:
	@./scripts/allure_report_server.sh "$(REPORT)" open "$(RESULTS)"

debug-driver:
	@echo "CHROME_BIN=$$CHROME_BIN"
	@echo "CHROMEDRIVER_BIN=$$CHROMEDRIVER_BIN"
	@echo "HEADLESS=$$HEADLESS"
	@echo "HEADLESS_MODE=$$HEADLESS_MODE"
	@echo "which chromium: $$(command -v chromium 2>/dev/null || true)"
	@echo "which google-chrome: $$(command -v google-chrome 2>/dev/null || true)"
	@echo "which chromedriver: $$(command -v chromedriver 2>/dev/null || true)"
	@chromium --version 2>/dev/null || true
	@google-chrome --version 2>/dev/null || true
	@chromedriver --version 2>/dev/null || true

test-local:
	@bash -c 'set -e; \
	if [ -z "$$VIRTUAL_ENV" ]; then \
		python -m venv .venv; \
		. .venv/bin/activate; \
	fi; \
	python -m pip install -r requirements.txt; \
	HEADLESS=true python -m pytest -q'

test-local-wsl:
	@bash -c 'set -e; \
	if [ -x /snap/bin/chromium ]; then \
		driver=""; \
		for candidate in /snap/bin/chromedriver \
			/snap/chromium/current/usr/lib/chromium-browser/chromedriver \
			/snap/chromium/current/usr/lib/chromium/chromedriver \
			/var/lib/snapd/snap/chromium/current/usr/lib/chromium-browser/chromedriver; do \
			if [ -x "$$candidate" ]; then driver="$$candidate"; break; fi; \
		done; \
		if [ -z "$$driver" ]; then \
			echo "Snap Chromium detected but chromedriver not found."; \
			echo "Install apt chromium-chromedriver or set CHROMEDRIVER_BIN manually."; \
			exit 1; \
		fi; \
		echo "Using CHROME_BIN=/snap/bin/chromium"; \
		echo "Using CHROMEDRIVER_BIN=$$driver"; \
		CHROME_BIN=/snap/bin/chromium CHROMEDRIVER_BIN=$$driver $(MAKE) test-local; \
	else \
		$(MAKE) test-local; \
	fi'

clean:
	rm -rf $(RESULTS) $(REPORT)
