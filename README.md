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

##  Быстрый запуск через Makefile (рекомендуется)

```bash
make test
make allure
make open
```

> `make test` запускает тесты в Docker (если Docker доступен).  
> `make allure` использует Allure CLI из WSL или из Docker-образа.  
> `make open` поднимает локальный HTTP-сервер для отчета и открывает ссылку в Windows (WSL2) на `http://localhost:<port>/`.
> `make serve-report` запускает HTTP-сервер в foreground и печатает URL.

---

##  Рекомендуемые команды (Docker + WSL)

- **Тесты в Docker (рекомендуется):**
  ```bash
  make test
  ```
- **Просмотр Allure отчёта через HTTP (WSL + Windows):**
  ```bash
  make open
  ```
  Сервер поднимается на `http://localhost:<port>/` (не `file://`).
- **Локальный запуск в WSL:**
  ```bash
  CHROME_BIN=/snap/bin/chromium \
  CHROMEDRIVER_BIN=/usr/bin/chromedriver \
  HEADLESS=true \
  HEADLESS_MODE=new \
  pytest src/tests --alluredir=allure-results
  ```

---

##  Локальный запуск (WSL без Docker)

### 1) Установка зависимостей
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Установка браузера и драйвера

Вариант с apt (предпочтительно для стабильности):
```bash
sudo apt update && sudo apt install -y chromium chromium-driver
```

Если chromium установлен через snap, бинарь обычно лежит в `/snap/bin/chromium`.
В этом случае задайте `CHROME_BIN` вручную (см. ниже).

### 3) Запуск тестов + сбор Allure results
```bash
pytest src/tests --alluredir=allure-results
```

---

##  Allure отчёт

**Важно:** Allure HTML использует `fetch`/XHR и подгружает `data/*.json`, поэтому не работает при открытии через `file://...`  
(браузеры блокируют `file://` по CORS/Origin). Отчет нужно открывать через HTTP.

### WSL + Windows (рекомендуется)
```bash
make test
make allure
make open
```

или запуск сервера в foreground:
```bash
make serve-report
```

Команда выведет URL вида `http://localhost:<port>/`. В WSL2 Windows открывает этот URL через `explorer.exe`.
Скрипт предпочитает `allure serve allure-results` (если установлен Allure CLI), иначе использует `python -m http.server`.

Если установлен Allure CLI:
```bash
allure serve allure-results
```

> В WSL Allure не всегда может открыть браузер автоматически — это нормально.  
> Открывай ссылку вручную (обычно `http://localhost:<port>`).

Чтобы сгенерировать HTML отчет:
```bash
allure generate allure-results -o allure-report --clean
```

### Просмотр отчета через HTTP (WSL2 + Windows)

Из Makefile (рекомендуется):
```bash
make open
```

или запустить сервер в foreground:
```bash
make serve-report
```

Команда выведет URL вида `http://localhost:<port>/`. В WSL2 Windows открывает этот URL через `explorer.exe`.

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
docker run --rm -v $(pwd)/allure-results:/app/allure-results aqa
```

**Windows PowerShell:**
```powershell
docker run --rm -v ${PWD}\allure-results:/app/allure-results aqa
```

### Генерация Allure отчета через Docker (если нет Allure CLI в WSL)
```bash
docker run --rm \
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

Файл: `github/workflows/ci.yml`

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

##  WSL заметка (локальный запуск без Docker)

Если запускаешь тесты в WSL локально, установи браузер и драйвер:
```bash
sudo apt update && sudo apt install -y chromium chromium-driver
```

И задай пути (в текущем терминале):
```bash
export CHROME_BIN="$(which chromium-browser 2>/dev/null || which chromium)"
export CHROMEDRIVER_BIN="$(which chromedriver)"
export HEADLESS=true
export HEADLESS_MODE=new
```

После этого:
```bash
pytest src/tests --alluredir=allure-results
```

Если Chromium установлен через snap, попробуй:
```bash
export CHROME_BIN="/snap/bin/chromium"
```

---

##  Открытие отчета в Windows из WSL

Открывать `allure-report/index.html` как `file://...` нельзя: браузер блокирует `fetch`/XHR.  
Используйте HTTP-сервер:

```bash
make open
```

Команда выведет URL вида `http://localhost:<port>/` и попробует открыть его через `explorer.exe`.
Если `explorer.exe` возвращает ошибку, откройте ссылку, которую выведет команда `make open`, вручную.

---

##  Design notes (коротко)
- Explicit waits вместо `sleep` → меньше флака и предсказуемое поведение.
- Проверки “URL + ключевые элементы” → минимально достаточные критерии для устойчивости.
- Allure attachments → быстрая диагностика падений в CI/Docker.
