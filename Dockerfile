FROM python:3.10-slim

# Базовые утилиты
RUN apt-get update -o Acquire::Retries=3 \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg unzip \
 && rm -rf /var/lib/apt/lists/*

# На некоторых сетях http к deb.debian.org "падает", переключаем на https
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    fi \
 && apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends --fix-missing \
      chromium chromium-driver default-jre-headless \
 && rm -rf /var/lib/apt/lists/*

# Allure CLI (опционально, но теперь есть в образе)
# Версию можно менять при необходимости
ARG ALLURE_VERSION=2.27.0
RUN curl -fsSL -o /tmp/allure.tgz \
      "https://github.com/allure-framework/allure2/releases/download/${ALLURE_VERSION}/allure-${ALLURE_VERSION}.tgz" \
 && tar -xzf /tmp/allure.tgz -C /opt \
 && ln -s "/opt/allure-${ALLURE_VERSION}/bin/allure" /usr/local/bin/allure \
 && rm -f /tmp/allure.tgz

# Пути для Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN mkdir -p /app/allure-results

# По умолчанию контейнер просто запускает тесты и пишет в /app/allure-results
CMD ["pytest", "src/tests", "--alluredir=allure-results"]
