IMAGE=aqa
RESULTS=allure-results
REPORT=allure-report

.PHONY: docker-build test allure open clean

docker-build:
	docker build -t $(IMAGE) .

test: docker-build
	mkdir -p $(RESULTS)
	docker run --rm -v "$$PWD/$(RESULTS):/app/$(RESULTS)" $(IMAGE)

allure:
	allure generate $(RESULTS) -o $(REPORT) --clean

open:
	@explorer.exe "$$(wslpath -w "$$(pwd)/allure-report/index.html")"
	
clean:
	rm -rf $(RESULTS) $(REPORT)

