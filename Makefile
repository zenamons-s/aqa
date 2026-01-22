IMAGE=aqa
RESULTS=allure-results
REPORT=allure-report
DOCKER_BIN=$(shell command -v docker 2>/dev/null)
ALLURE_BIN=$(shell command -v allure 2>/dev/null)

.PHONY: docker-build test allure open clean

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
	docker run --rm -v "$$PWD/$(RESULTS):/app/$(RESULTS)" $(IMAGE)

allure: docker-build
	@if [ -d "$(REPORT)" ]; then rm -rf $(REPORT); fi
	@if [ -n "$(ALLURE_BIN)" ]; then \
		allure generate $(RESULTS) -o $(REPORT) --clean; \
	else \
		mkdir -p $(REPORT); \
		docker run --rm \
			-v "$$PWD/$(RESULTS):/app/$(RESULTS)" \
			-v "$$PWD/$(REPORT):/app/$(REPORT)" \
			$(IMAGE) allure generate $(RESULTS) -o $(REPORT) --clean; \
	fi

open:
	@if [ ! -f "$(REPORT)/index.html" ]; then \
		echo "Allure report not found. Run 'make allure' first."; \
		exit 1; \
	fi
	@explorer.exe "$$(wslpath -w "$$(pwd)/$(REPORT)/index.html")"
	
clean:
	rm -rf $(RESULTS) $(REPORT)
