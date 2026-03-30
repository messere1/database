from __future__ import annotations

import argparse
import importlib.metadata as metadata
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"


def maybe_relaunch_with_py311() -> None:
    if sys.version_info >= (3, 10):
        return

    candidates = [
        Path(os.environ.get("PYTHON311_PATH", "")),
        Path(r"C:\Users\73110\AppData\Local\Microsoft\WindowsApps\python3.11.exe"),
        Path(r"C:\Program Files\Python311\python.exe"),
    ]

    for candidate in candidates:
        if candidate and candidate.exists():
            print(f"[bootstrap] Python {sys.version.split()[0]} detected, relaunching with {candidate}")
            os.execv(str(candidate), [str(candidate), str(PROJECT_ROOT / "start_server.py"), *sys.argv[1:]])

    raise RuntimeError(
        "Python 3.10+ is required. Please install Python 3.11 and rerun start_server.py, "
        "or set PYTHON311_PATH to your python3.11 executable."
    )


def parse_requirements(req_path: Path) -> list[tuple[str, str, str | None]]:
    requirement_entries: list[tuple[str, str, str | None]] = []
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)")

    for raw_line in req_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        line = line.split("#", 1)[0].strip()
        line = line.split(";", 1)[0].strip()
        if not line:
            continue

        match = pattern.match(line)
        if not match:
            continue

        package_name = match.group(1)
        pinned_version = None
        if "==" in line:
            pinned_version = line.split("==", 1)[1].strip()

        requirement_entries.append((line, package_name, pinned_version))

    return requirement_entries


def find_missing_or_mismatch(requirements: list[tuple[str, str, str | None]]) -> list[str]:
    to_install: list[str] = []

    for requirement_spec, package_name, pinned_version in requirements:
        try:
            installed_version = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            to_install.append(requirement_spec)
            continue

        if pinned_version and installed_version != pinned_version:
            to_install.append(requirement_spec)

    return to_install


def ensure_dependencies(auto_install: bool = True) -> None:
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"requirements.txt not found at {REQUIREMENTS_FILE}")

    requirements = parse_requirements(REQUIREMENTS_FILE)
    to_install = find_missing_or_mismatch(requirements)

    if not to_install:
        print("[bootstrap] Dependencies are ready.")
        return

    print("[bootstrap] Missing or mismatched dependencies detected:")
    for pkg in to_install:
        print(f"  - {pkg}")

    if not auto_install:
        raise RuntimeError("Dependency check failed and auto install is disabled.")

    print("[bootstrap] Installing dependencies from requirements.txt ...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
        cwd=str(PROJECT_ROOT),
    )
    print("[bootstrap] Dependency installation completed.")


def _browser_host(host: str) -> str:
    if host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return host


def _open_dashboard_when_ready(host: str, port: int, path: str = "/dashboard", timeout_seconds: int = 45) -> None:
    browser_host = _browser_host(host)
    base_url = f"http://{browser_host}:{port}"
    target_url = f"{base_url}{path}"
    health_url = f"{base_url}/api/v1/system/health"

    deadline = time.time() + max(5, timeout_seconds)
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=3) as response:
                if response.status == 200:
                    break
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(1)

    webbrowser.open(target_url)


def run_uvicorn(host: str, port: int, reload_mode: bool, open_browser: bool) -> int:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        str(PROJECT_ROOT),
        "--host",
        host,
        "--port",
        str(port),
    ]

    if reload_mode:
        command.append("--reload")

    print("[bootstrap] Starting server:")
    print("[bootstrap] " + " ".join(command))

    if open_browser:
        url = f"http://{_browser_host(host)}:{port}/dashboard"
        print(f"[bootstrap] Auto-open dashboard: {url}")
        threading.Thread(
            target=_open_dashboard_when_ready,
            args=(host, port),
            daemon=True,
        ).start()

    try:
        return subprocess.call(command, cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        print("\n[bootstrap] Server stopped by user.")
        return 130


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap launcher for Crime Analytics backend. "
            "It checks Python version and dependencies, installs missing packages, then starts uvicorn."
        )
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host, default 0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="Server port, default 8000")
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn auto-reload")
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="Only check dependencies; do not auto install if missing",
    )
    parser.add_argument(
        "--no-open-browser",
        action="store_true",
        help="Do not auto open /dashboard after service is ready",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    maybe_relaunch_with_py311()
    ensure_dependencies(auto_install=not args.no_auto_install)

    return run_uvicorn(
        host=args.host,
        port=args.port,
        reload_mode=not args.no_reload,
        open_browser=not args.no_open_browser,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"[bootstrap] Command failed: {exc}")
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"[bootstrap] Startup failed: {exc}")
        raise SystemExit(1)
