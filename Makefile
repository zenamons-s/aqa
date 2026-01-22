IMAGE=aqa
RESULTS=allure-results
REPORT=allure-report
DOCKER_BIN=$(shell command -v docker 2>/dev/null)
ALLURE_BIN=$(shell command -v allure 2>/dev/null)
HOST_UID=$(shell id -u)
HOST_GID=$(shell id -g)
DOCKER_USER=$(HOST_UID):$(HOST_GID)

.PHONY: docker-build test allure serve-report serve open clean debug-driver test-local test-local-wsl

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
	mkdir -p $(RESULTS)
	docker run --rm --user $(DOCKER_USER) \
		-v "$$PWD/$(RESULTS):/app/$(RESULTS)" \
		$(IMAGE)

allure: docker-build
	@if [ -d "$(REPORT)" ]; then rm -rf $(REPORT); fi
	@if [ -n "$(ALLURE_BIN)" ]; then \
		allure generate $(RESULTS) -o $(REPORT) --clean; \
	else \
		mkdir -p $(REPORT); \
		docker run --rm \
			--user $(DOCKER_USER) \
			-v "$$PWD/$(RESULTS):/app/$(RESULTS)" \
			-v "$$PWD/$(REPORT):/app/$(REPORT)" \
			$(IMAGE) allure generate $(RESULTS) -o $(REPORT) --clean; \
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
