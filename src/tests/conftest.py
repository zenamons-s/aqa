import os
import pathlib
import re
import shutil
import tempfile

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


def _is_wsl() -> bool:
    try:
        version_info = pathlib.Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "microsoft" in version_info


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_") or "session"


def _prepare_log_dir() -> pathlib.Path:
    results_dir = pathlib.Path("allure-results")
    temp_dir = pathlib.Path(tempfile.gettempdir()) / "aqa-logs"

    for candidate in (results_dir, temp_dir):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return candidate
        except PermissionError:
            continue
        except OSError:
            continue

    return temp_dir


def _ensure_log_file(path: pathlib.Path) -> pathlib.Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        return path
    except PermissionError:
        fallback_dir = pathlib.Path(tempfile.gettempdir()) / "aqa-logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / path.name
        fallback_path.touch(exist_ok=True)
        return fallback_path


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
        f"HEADLESS_MODE={os.getenv('HEADLESS_MODE', 'new')}",
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
    headless_mode = os.getenv("HEADLESS_MODE", "new").strip().lower()

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
        if headless_mode == "old":
            options.add_argument("--headless")
        else:
            options.add_argument("--headless=new")

    if _is_wsl() and "/snap/" in chrome_bin:
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--remote-debugging-port=0")
        options.add_argument("--no-zygote")
        options.add_argument("--disable-software-rasterizer")

    # уникальный профиль (часто лечит "Chrome instance exited", особенно snap)
    profile_dir = tempfile.mkdtemp(prefix="chrome-profile-")
    options.add_argument(f"--user-data-dir={profile_dir}")

    log_dir = _prepare_log_dir()
    node_id = _sanitize_filename(request.node.nodeid)
    chrome_log = _ensure_log_file(log_dir / f"chrome-{node_id}.log")
    chromedriver_log = _ensure_log_file(log_dir / f"chromedriver-{node_id}.log")

    options.add_argument("--enable-logging=stderr")
    options.add_argument("--v=1")
    options.add_argument(f"--log-file={chrome_log}")

    service = Service(
        executable_path=driver_bin,
        service_args=["--verbose", f"--log-path={chromedriver_log}"],
    )

    try:
        drv = webdriver.Chrome(service=service, options=options)
        drv.implicitly_wait(0)
    except Exception:
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
            for log_path, label in ((chrome_log, "chrome.log"), (chromedriver_log, "chromedriver.log")):
                if log_path.exists():
                    try:
                        allure.attach.file(
                            str(log_path),
                            name=label,
                            attachment_type=allure.attachment_type.TEXT,
                        )
                    except Exception:
                        pass

        try:
            drv.quit()
        finally:
            shutil.rmtree(profile_dir, ignore_errors=True)
