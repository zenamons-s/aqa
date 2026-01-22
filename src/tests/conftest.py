import os
import pathlib
import tempfile
import shutil
import allure
import pytest
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

load_dotenv()


def _env_bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y")


def _resolve_binary(env_var: str, candidates: list[str], label: str) -> str:
    env_value = os.getenv(env_var)
    if env_value:
        env_path = pathlib.Path(env_value)
        if env_path.exists():
            return str(env_path)
        pytest.fail(
            f"{label} not found at {env_value}. "
            f"Update {env_var} or install {label.lower()}."
        )

    for candidate in candidates:
        candidate_path = pathlib.Path(candidate)
        if candidate_path.is_absolute():
            if candidate_path.exists():
                return str(candidate_path)
            continue

        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    pytest.fail(
        f"{label} not found. Checked: {', '.join(candidates)}. "
        f"Install {label.lower()} or set {env_var}."
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("BASE_URL", "https://www.saucedemo.com").rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def _allure_environment(base_url):
    results_dir = pathlib.Path("allure-results")
    results_dir.mkdir(exist_ok=True)
    props = [
        f"BASE_URL={base_url}",
        f"HEADLESS={os.getenv('HEADLESS', 'true')}",
        "IMPL=selenium",
    ]
    (results_dir / "environment.properties").write_text("\n".join(props), encoding="utf-8")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture
def driver(request):
    headless = _env_bool("HEADLESS", "true")

    chrome_bin = _resolve_binary(
        "CHROME_BIN",
        [
            "chromium",
            "chromium-browser",
            "google-chrome",
            "/snap/bin/chromium",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ],
        "Chrome/Chromium",
    )
    driver_bin = _resolve_binary(
        "CHROMEDRIVER_BIN",
        [
            "chromedriver",
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
        ],
        "Chromedriver",
    )

    options = Options()
    options.binary_location = chrome_bin

    # стабильность в WSL/Docker/CI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")

    if headless:
        options.add_argument("--headless=new")

    # уникальный профиль (часто лечит "Chrome instance exited", особенно snap)
    profile_dir = tempfile.mkdtemp(prefix="chrome-profile-")
    options.add_argument(f"--user-data-dir={profile_dir}")

    results_dir = pathlib.Path("allure-results")
    results_dir.mkdir(exist_ok=True)
    chromedriver_log = results_dir / "chromedriver.log"
    log_handle = open(chromedriver_log, "w", encoding="utf-8")
    service = Service(executable_path=driver_bin, log_output=log_handle)

    try:
        drv = webdriver.Chrome(service=service, options=options)
        drv.implicitly_wait(0)
    except Exception:
        log_handle.close()
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise

    try:
        yield drv
    finally:
        failed = getattr(request.node, "rep_call", None) and request.node.rep_call.failed
        if failed:
            try:
                allure.attach(drv.current_url, name="page_url", attachment_type=allure.attachment_type.TEXT)
            except Exception:
                pass
            try:
                allure.attach(drv.get_screenshot_as_png(), name="screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
            try:
                allure.attach(drv.page_source, name="page_html", attachment_type=allure.attachment_type.HTML)
            except Exception:
                pass

        try:
            drv.quit()
        finally:
            log_handle.close()
            shutil.rmtree(profile_dir, ignore_errors=True)
