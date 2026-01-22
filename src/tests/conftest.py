import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

import allure
import pytest
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

load_dotenv()

_DIAG_PRINTED = False


def _env_bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y")


def _resolve_from_candidates(candidates: list[str], label: str) -> str:
    for candidate in candidates:
        candidate_path = pathlib.Path(candidate)
        if candidate_path.is_absolute():
            if candidate_path.exists():
                return str(candidate_path)
            continue

        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    raise RuntimeError(
        f"{label} not found. Checked: {', '.join(candidates)}. "
        f"Install {label.lower()} or set CHROME_BIN/CHROMEDRIVER_BIN."
    )


def detect_wsl() -> bool:
    for path in ("/proc/version", "/proc/sys/kernel/osrelease"):
        try:
            version_info = pathlib.Path(path).read_text(encoding="utf-8").lower()
        except OSError:
            continue
        if "microsoft" in version_info:
            return True
    return False


def detect_docker() -> bool:
    cgroup_paths = ("/proc/1/cgroup", "/proc/self/cgroup")
    for path in cgroup_paths:
        try:
            content = pathlib.Path(path).read_text(encoding="utf-8").lower()
        except OSError:
            continue
        if any(token in content for token in ("docker", "kubepods", "containerd")):
            return True
    return pathlib.Path("/.dockerenv").exists()


def resolve_chrome_binary() -> str:
    env_value = os.getenv("CHROME_BIN")
    if env_value:
        env_path = pathlib.Path(env_value)
        if env_path.exists():
            return str(env_path)
        raise RuntimeError(f"CHROME_BIN set but not found at {env_value}.")

    candidates = [
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "/snap/bin/chromium",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/opt/google/chrome/chrome",
    ]
    return _resolve_from_candidates(candidates, "Chrome/Chromium")


def resolve_chromedriver_binary(chrome_bin: str) -> str:
    env_value = os.getenv("CHROMEDRIVER_BIN")
    if env_value:
        env_path = pathlib.Path(env_value)
        if env_path.exists():
            return str(env_path)
        raise RuntimeError(f"CHROMEDRIVER_BIN set but not found at {env_value}.")

    is_snap = "/snap/" in chrome_bin or chrome_bin == "/snap/bin/chromium"
    if is_snap:
        candidates = [
            "/snap/bin/chromedriver",
            "/snap/chromium/current/usr/lib/chromium-browser/chromedriver",
            "/snap/chromium/current/usr/lib/chromium/chromedriver",
            "/var/lib/snapd/snap/chromium/current/usr/lib/chromium-browser/chromedriver",
        ]
        for candidate in candidates:
            if pathlib.Path(candidate).exists():
                return candidate
        raise RuntimeError(
            "Snap Chromium detected but chromedriver not found. "
            "Install chromium-chromedriver (apt) or set CHROMEDRIVER_BIN manually."
        )

    candidates = [
        "chromedriver",
        "/usr/bin/chromedriver",
        "/usr/lib/chromium/chromedriver",
        "/usr/lib/chromium-browser/chromedriver",
    ]
    return _resolve_from_candidates(candidates, "Chromedriver")


def _command_output(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "not found"
    except OSError as exc:
        return f"error: {exc}"

    output = (result.stdout or "") + (result.stderr or "")
    return output.strip() or "no output"


def print_debug_banner(chrome_bin: str, driver_bin: str) -> None:
    print("\n====== Selenium debug info ======")
    print(f"uname -a: {_command_output(['uname', '-a'])}")
    print(f"python -V: {_command_output([sys.executable, '-V'])}")
    print(f"which chromium: {shutil.which('chromium') or 'not found'}")
    print(f"which google-chrome: {shutil.which('google-chrome') or 'not found'}")
    print(f"which chromedriver: {shutil.which('chromedriver') or 'not found'}")
    if chrome_bin:
        print(f"chromium --version: {_command_output([chrome_bin, '--version'])}")
    if driver_bin:
        print(f"chromedriver --version: {_command_output([driver_bin, '--version'])}")
    print(f"env CHROME_BIN={os.getenv('CHROME_BIN', '')}")
    print(f"env CHROMEDRIVER_BIN={os.getenv('CHROMEDRIVER_BIN', '')}")
    print(f"env HEADLESS={os.getenv('HEADLESS', '')}")
    print(f"env HEADLESS_MODE={os.getenv('HEADLESS_MODE', '')}")
    print(f"env CHROME_DEBUG_PIPE={os.getenv('CHROME_DEBUG_PIPE', '')}")
    print("=================================\n")


def tail_file(path: pathlib.Path, n: int = 80) -> str:
    if not path or not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n:])


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_") or "session"


def _ensure_writable_dir(path: pathlib.Path, fallback_name: str) -> pathlib.Path:
    fallback_dir = pathlib.Path(tempfile.gettempdir()) / fallback_name
    for candidate in (path, fallback_dir):
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
    fallback_dir.mkdir(parents=True, exist_ok=True)
    return fallback_dir


def _prepare_log_dir() -> pathlib.Path:
    desired = pathlib.Path(os.getenv("SELENIUM_LOG_DIR", "/app/tmp/aqa-logs"))
    return _ensure_writable_dir(desired, "aqa-logs")


def _ensure_log_file(path: pathlib.Path) -> pathlib.Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        return path
    except PermissionError:
        fallback_dir = _ensure_writable_dir(pathlib.Path(tempfile.gettempdir()) / "aqa-logs", "aqa-logs")
        fallback_path = fallback_dir / path.name
        fallback_path.touch(exist_ok=True)
        return fallback_path


def _ensure_allure_results_dir() -> pathlib.Path:
    results_dir = pathlib.Path(os.getenv("ALLURE_RESULTS_DIR", "allure-results"))
    ensured_dir = _ensure_writable_dir(results_dir, "aqa-allure-results")
    if ensured_dir != results_dir:
        print(
            f"[allure] Results dir {results_dir} not writable. "
            f"Using fallback {ensured_dir}."
        )
    return ensured_dir


def _is_writable_dir(path: pathlib.Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _prepare_chrome_session_dirs(node_id: str) -> dict[str, pathlib.Path]:
    base_dir = _ensure_writable_dir(pathlib.Path("/app/tmp/aqa-chrome"), "aqa-chrome")
    session_dir = pathlib.Path(
        tempfile.mkdtemp(prefix=f"chrome-{node_id}-{uuid.uuid4().hex[:8]}-", dir=base_dir)
    )
    profile_dir = session_dir / "profile"
    cache_dir = session_dir / "cache"
    crash_dir = session_dir / "crash"
    runtime_dir = session_dir / "run"
    for candidate in (profile_dir, cache_dir, crash_dir, runtime_dir):
        candidate.mkdir(parents=True, exist_ok=True)
    return {
        "base_dir": base_dir,
        "session_dir": session_dir,
        "profile_dir": profile_dir,
        "cache_dir": cache_dir,
        "crash_dir": crash_dir,
        "runtime_dir": runtime_dir,
    }


def _print_startup_summary(
    *,
    chrome_bin: str,
    driver_bin: str,
    headless: bool,
    headless_mode: str,
    use_debug_pipe: bool,
    dirs: dict[str, pathlib.Path],
    log_dir: pathlib.Path,
) -> None:
    global _DIAG_PRINTED
    if _DIAG_PRINTED:
        return
    _DIAG_PRINTED = True
    print(
        "[selenium] chromium init | "
        f"headless={headless}({headless_mode}) "
        f"debug_pipe={use_debug_pipe} "
        f"docker={detect_docker()} wsl={detect_wsl()}"
    )
    print(
        "[selenium] paths | "
        f"chrome={chrome_bin} driver={driver_bin} "
        f"profile={dirs['profile_dir']} cache={dirs['cache_dir']} "
        f"crash={dirs['crash_dir']} logs={log_dir}"
    )


def _should_fallback_to_port(exc: Exception) -> bool:
    message = str(exc).lower()
    return "remote-debugging-pipe" in message and ("unknown" in message or "unrecognized" in message)


def _build_chrome_options(
    *,
    chrome_bin: str,
    headless: bool,
    headless_mode: str,
    use_debug_pipe: bool,
    profile_dir: str,
    cache_dir: str,
    crash_dir: str,
    chrome_log: pathlib.Path,
    is_wsl_snap: bool,
) -> Options:
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

    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-breakpad")
    options.add_argument("--disable-crashpad")
    options.add_argument("--no-crashpad")
    options.add_argument("--disable-features=Crashpad")

    if headless:
        if headless_mode == "old":
            options.add_argument("--headless")
        else:
            options.add_argument("--headless=new")

    if is_wsl_snap:
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--no-zygote")
        options.add_argument("--disable-software-rasterizer")

    if use_debug_pipe:
        options.add_argument("--remote-debugging-pipe")
    else:
        options.add_argument("--remote-debugging-port=0")

    # уникальный профиль (часто лечит "Chrome instance exited", особенно snap)
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument(f"--disk-cache-dir={cache_dir}")
    options.add_argument(f"--crash-dumps-dir={crash_dir}")

    options.add_argument("--enable-logging=stderr")
    options.add_argument("--v=1")
    options.add_argument(f"--log-file={chrome_log}")
    return options


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("BASE_URL", "https://www.saucedemo.com").rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def _allure_environment(base_url):
    results_dir = _ensure_allure_results_dir()
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
    use_debug_pipe = _env_bool("CHROME_DEBUG_PIPE", "true")

    chrome_bin = resolve_chrome_binary()
    driver_bin = resolve_chromedriver_binary(chrome_bin)
    is_wsl_snap = detect_wsl() and "/snap/" in chrome_bin

    node_id = _sanitize_filename(request.node.nodeid)
    session_dirs = _prepare_chrome_session_dirs(node_id)
    profile_dir = str(session_dirs["profile_dir"])
    cache_dir = str(session_dirs["cache_dir"])
    crash_dir = str(session_dirs["crash_dir"])

    log_dir = _prepare_log_dir()
    chrome_log = _ensure_log_file(log_dir / f"chrome-{node_id}.log")
    chromedriver_log = _ensure_log_file(log_dir / f"chromedriver-{node_id}.log")

    runtime_dir = session_dirs["runtime_dir"]
    existing_runtime = os.getenv("XDG_RUNTIME_DIR", "").strip()
    if not existing_runtime or not _is_writable_dir(pathlib.Path(existing_runtime)):
        os.environ["XDG_RUNTIME_DIR"] = str(runtime_dir)

    _print_startup_summary(
        chrome_bin=chrome_bin,
        driver_bin=driver_bin,
        headless=headless,
        headless_mode=headless_mode,
        use_debug_pipe=use_debug_pipe,
        dirs=session_dirs,
        log_dir=log_dir,
    )

    service = Service(
        executable_path=driver_bin,
        service_args=["--verbose", f"--log-path={chromedriver_log}"],
    )

    try:
        options = _build_chrome_options(
            chrome_bin=chrome_bin,
            headless=headless,
            headless_mode=headless_mode,
            use_debug_pipe=use_debug_pipe,
            profile_dir=profile_dir,
            cache_dir=cache_dir,
            crash_dir=crash_dir,
            chrome_log=chrome_log,
            is_wsl_snap=is_wsl_snap,
        )
        drv = webdriver.Chrome(service=service, options=options)
        drv.implicitly_wait(0)
    except Exception as exc:
        if use_debug_pipe and _should_fallback_to_port(exc):
            print("[selenium] remote-debugging-pipe unsupported, falling back to --remote-debugging-port=0")
            try:
                options = _build_chrome_options(
                    chrome_bin=chrome_bin,
                    headless=headless,
                    headless_mode=headless_mode,
                    use_debug_pipe=False,
                    profile_dir=profile_dir,
                    cache_dir=cache_dir,
                    crash_dir=crash_dir,
                    chrome_log=chrome_log,
                    is_wsl_snap=is_wsl_snap,
                )
                drv = webdriver.Chrome(service=service, options=options)
                drv.implicitly_wait(0)
            except Exception:
                print_debug_banner(chrome_bin, driver_bin)
                if chromedriver_log:
                    print("---- chromedriver log tail ----")
                    print(tail_file(chromedriver_log, n=80))
                if chrome_log:
                    print("---- chrome log tail ----")
                    print(tail_file(chrome_log, n=80))
                print(
                    "Advice: set CHROME_BIN and CHROMEDRIVER_BIN manually if needed. "
                    "For WSL, prefer apt chromium + chromium-chromedriver or run via Docker."
                )
                shutil.rmtree(session_dirs["session_dir"], ignore_errors=True)
                raise
        else:
            print_debug_banner(chrome_bin, driver_bin)
            if chromedriver_log:
                print("---- chromedriver log tail ----")
                print(tail_file(chromedriver_log, n=80))
            if chrome_log:
                print("---- chrome log tail ----")
                print(tail_file(chrome_log, n=80))
            print(
                "Advice: set CHROME_BIN and CHROMEDRIVER_BIN manually if needed. "
                "For WSL, prefer apt chromium + chromium-chromedriver or run via Docker."
            )
            shutil.rmtree(session_dirs["session_dir"], ignore_errors=True)
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
            shutil.rmtree(session_dirs["session_dir"], ignore_errors=True)
