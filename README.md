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
> `make open` открывает отчет в Windows через `explorer.exe` (WSL).

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

Если установлен Allure CLI:
```bash
allure serve allure-results
```

> В WSL Allure не всегда может открыть браузер автоматически — это нормально.  
> Открывай ссылку вручную (обычно `http://localhost:<port>` или `http://127.0.0.1:<port>`).

Чтобы сгенерировать HTML отчет:
```bash
allure generate allure-results -o allure-report --clean
```

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

Если отчет сгенерирован в WSL, открой его так:
```bash
explorer.exe "$(wslpath -w "$(pwd)/allure-report/index.html")"
```

Если `explorer.exe` возвращает ошибку, проверь:
- что файл `allure-report/index.html` действительно существует;
- что путь корректно преобразуется `wslpath -w`.

---

##  Design notes (коротко)
- Explicit waits вместо `sleep` → меньше флака и предсказуемое поведение.
- Проверки “URL + ключевые элементы” → минимально достаточные критерии для устойчивости.
- Allure attachments → быстрая диагностика падений в CI/Docker.
