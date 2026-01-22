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

    chrome_bin = (
        os.getenv("CHROME_BIN")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
        or "/usr/bin/chromium"
    )
    driver_bin = os.getenv("CHROMEDRIVER_BIN") or shutil.which("chromedriver") or "/usr/bin/chromedriver"

    options = Options()
    options.binary_location = chrome_bin

    # стабильность в WSL/Docker/CI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    if headless:
        options.add_argument("--headless=new")

    # уникальный профиль (часто лечит "Chrome instance exited", особенно snap)
    profile_dir = tempfile.mkdtemp(prefix="chrome-profile-")
    options.add_argument(f"--user-data-dir={profile_dir}")

    service = Service(executable_path=driver_bin)

    drv = webdriver.Chrome(service=service, options=options)
    drv.implicitly_wait(0)

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
            shutil.rmtree(profile_dir, ignore_errors=True)
