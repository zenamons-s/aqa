# AQA — Saucedemo Login (Selenium + Pytest + Allure + Docker, Python 3.10)

Проект для автоматизации авторизации на https://www.saucedemo.com/

Сделано как небольшой “прикладной” тестовый каркас:
- без `sleep` — только явные ожидания `WebDriverWait`;
- Page Object (локаторы и действия в одном месте);
- Allure шаги в стиле `Given / When / Then`;
- при падениях в Allure прикладываю `screenshot / page_html / page_url`;
- запуск воспроизводим локально, в Docker и в CI.

---

##  Сценарии (5 тестов)

1) Успешный логин: `standard_user / secret_sauce`
2) Неверный пароль
3) Заблокированный пользователь: `locked_out_user`
4) Пустые поля
5) `performance_glitch_user` — проверяю корректный переход и что inventory реально загрузилась
   (увеличенный timeout только для этого теста)

**Проверки:**
- корректность URL (остаёмся на `/` или переходим на `/inventory.html`)
- наличие ключевых элементов страницы (логин-форма / inventory контейнер + заголовок “Products”)

---

##  Структура

- `src/pages/` — Page Object (`LoginPage`, `InventoryPage`)
- `src/tests/` — тесты и фикстуры (драйвер + Allure attachments)

---

##  Запуск через Docker (рекомендуется)

```bash
make test
make allure
make open
```

> `make test` запускает тесты в Docker (если Docker доступен).  
> `make allure` использует Allure CLI из WSL или из Docker-образа.  
> `make open` поднимает локальный HTTP-сервер для отчета и печатает ссылку вида `http://localhost:<port>/`.
> `make serve-report` запускает HTTP-сервер в foreground и печатает URL.

---

##  Локальный запуск в WSL2 без Docker

### 1) Установка зависимостей
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Установка браузера и драйвера

**Вариант A (рекомендуется): apt-пакеты вместо snap**
```bash
sudo snap remove chromium || true
sudo apt update
sudo apt install -y chromium-browser chromium-chromedriver
```

**Вариант B: если Chromium через snap**
```bash
export CHROME_BIN=/snap/bin/chromium
export CHROMEDRIVER_BIN=/snap/chromium/current/usr/lib/chromium-browser/chromedriver
```

Проверьте версии и пути:
```bash
make debug-driver
```

### 3) Запуск тестов + сбор Allure results
```bash
pytest src/tests --alluredir=allure-results
```

Быстрые команды:
```bash
make debug-driver
make test-local
make test-local-wsl
```

---

##  Просмотр Allure отчета в WSL2

- **Через Allure CLI и Windows браузер:**
  ```bash
  allure serve allure-results
  ```
  Откройте в Windows браузере URL вида `http://localhost:<port>/`.

- **Или через генерацию отчета:**
  ```bash
  allure generate allure-results -o allure-report --clean
  explorer.exe "$(wslpath -w allure-report/index.html)"
  ```

---

##  Allure отчёт

**Важно:** Allure HTML использует `fetch`/XHR и подгружает `data/*.json`, поэтому не работает при открытии через `file://...`  
(браузеры блокируют `file://` по CORS/Origin). Отчет нужно открывать через HTTP.

Быстрый путь через Makefile:
```bash
make allure
make open
```

Скрипт предпочитает `allure serve allure-results` (если установлен Allure CLI), иначе использует `python -m http.server`.

---

##  Артефакты при падении теста

В Allure автоматически прикладываются:
- screenshot
- page_html
- page_url

---

##  Запуск “flaky” сценария

Тест с `performance_glitch_user` помечен как `@pytest.mark.flaky`.

Запуск только flaky с автоповтором:
```bash
pytest src/tests -m flaky --reruns 2 --reruns-delay 1 --alluredir=allure-results
```

---

##  Docker (образ: `aqa`)

### Сборка
```bash
docker build -t aqa .
```

### Запуск (с сохранением `allure-results` на хост)

**WSL / Linux:**
```bash
docker run --rm --user $(id -u):$(id -g) \
  -v $(pwd)/allure-results:/app/allure-results aqa
```

**Windows PowerShell:**
```powershell
docker run --rm -v ${PWD}\allure-results:/app/allure-results aqa
```

### Генерация Allure отчета через Docker (если нет Allure CLI в WSL)
```bash
docker run --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd)/allure-results:/app/allure-results \
  -v $(pwd)/allure-report:/app/allure-report \
  aqa allure generate allure-results -o allure-report --clean
```

### WSL2 примечание (если `docker: command not found` внутри WSL)
Для использования Docker в WSL2 нужен Docker Desktop на Windows и включенная интеграция:
- Docker Desktop → Settings → Resources → **WSL integration** → включить для `Ubuntu-24.04`
- затем в PowerShell: `wsl --shutdown`

---

##  CI (GitHub Actions)

Workflow:
- собирает Docker-образ
- запускает тесты в контейнере
- сохраняет `allure-results` как artifact

Файл: `.github/workflows/ci.yml`

---

##  Переменные окружения

- `BASE_URL` (default: `https://www.saucedemo.com`)
- `HEADLESS` (default: `true`)
- `HEADLESS_MODE` (default: `new`, можно указать `old` для классического `--headless`)
- `CHROME_BIN`, `CHROMEDRIVER_BIN` (полезно для локального запуска в WSL без Docker)

Пример:
```bash
HEADLESS=false pytest src/tests --alluredir=allure-results
```

Пример `.env`:
```bash
cp .env.example .env
```

---

##  Troubleshooting

### Ошибки и расшифровки

- `Status code 46` у chromedriver — несовместимый драйвер/сборка/путь (часто snap + драйвер от apt).
- `PermissionError` в `allure-results` — права на каталоги после `docker run`.

Команда для исправления прав:
```bash
sudo chown -R $USER:$USER allure-results allure-report .pytest_cache artifacts || true
```

---

##  Design notes (коротко)
- Explicit waits вместо `sleep` → меньше флака и предсказуемое поведение.
- Проверки “URL + ключевые элементы” → минимально достаточные критерии для устойчивости.
- Allure attachments → быстрая диагностика падений в CI/Docker.
