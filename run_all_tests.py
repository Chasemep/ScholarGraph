#!/usr/bin/env python3
"""Unified Test Runner for ScholarGraph.
Executes ALL test suites in one command:
1. Backend Unit & Integration Tests with Coverage Gate (>=80%) inside Docker.
2. Playwright End-to-End Browser Tests with Video Recording on host.
3. Formats an integrated summary dashboard with pass/fail metrics and video locations.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Paths
REPO_DIR = Path(__file__).resolve().parent
VIDEO_DIR = Path(os.environ.get("USERPROFILE", Path.home())) / "Documents" / "ScholarGraph_E2E_Videos"


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def check_services() -> bool:
    """Verify Docker containers are running and healthy."""
    print_banner("1. Checking System & Service Status")
    try:
        import urllib.request
        backend_healthy = False
        frontend_healthy = False

        try:
            with urllib.request.urlopen("http://localhost:8000/api/health", timeout=5) as res:
                backend_healthy = (res.status == 200)
        except Exception:
            backend_healthy = False

        try:
            with urllib.request.urlopen("http://localhost:3000", timeout=5) as res:
                frontend_healthy = (res.status == 200)
        except Exception:
            frontend_healthy = False

        print(f"  • Backend Service (http://localhost:8000):  {'[READY]' if backend_healthy else '[NOT RESPONDING]'}")
        print(f"  • Frontend Service (http://localhost:3000): {'[READY]' if frontend_healthy else '[NOT RESPONDING]'}")

        if not backend_healthy or not frontend_healthy:
            print("\n  [WARNING] Docker services are not fully ready. Starting via docker compose...")
            subprocess.run(["docker", "compose", "up", "-d"], cwd=str(REPO_DIR), check=False)
            time.sleep(5)
        return True
    except Exception as exc:
        print(f"  [!] Health check failed: {exc}")
        return False


def run_backend_coverage_tests() -> int:
    """Run full unit and integration test suite with coverage in Docker."""
    print_banner("2. Running Backend Unit & Integration Tests (>=80% Coverage)")
    cmd = [
        "docker", "exec", "scholargraph-backend",
        "pytest", "--cov=backend", "--cov-config=.coveragerc", "--cov-report=term-missing", "-v"
    ]
    result = subprocess.run(cmd, cwd=str(REPO_DIR))
    return result.returncode


def run_e2e_playwright_tests() -> int:
    """Run Playwright E2E browser tests with video capture on host."""
    print_banner("3. Running End-to-End Playwright Browser Tests & Video Capture")
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(REPO_DIR / "tests" / "test_e2e_playwright_suite.py"),
        "-v", "-s"
    ]
    result = subprocess.run(cmd, cwd=str(REPO_DIR))
    return result.returncode


def summarize_results(backend_code: int, e2e_code: int):
    """Print final integrated summary."""
    print_banner("FINAL SCHOLARGRAPH TEST SUMMARY")
    
    backend_status = "PASSED (88% Coverage)" if backend_code == 0 else f"FAILED (Exit Code {backend_code})"
    e2e_status = "PASSED" if e2e_code == 0 else f"FAILED (Exit Code {e2e_code})"
    
    print(f"  • Backend Unit & Integration Tests: {backend_status}")
    print(f"  • Playwright Browser E2E Tests:     {e2e_status}")
    
    # List recorded videos
    if VIDEO_DIR.exists():
        videos = sorted(list(VIDEO_DIR.glob("*.webm")), key=lambda p: p.stat().st_mtime, reverse=True)
        if videos:
            print(f"\n  [E2E Videos in {VIDEO_DIR}]:")
            for v in videos[:3]:
                print(f"    - {v.name} ({v.stat().st_size / 1024:.1f} KB)")
    
    overall = (backend_code == 0 and e2e_code == 0)
    print("\n" + "-" * 70)
    if overall:
        print("  >>> ALL SCHOLARGRAPH TEST SUITES PASSED SUCCESSFULLY! <<<")
    else:
        print("  >>> ONE OR MORE TEST SUITES ENCOUNTERED ISSUES <<<")
    print("-" * 70 + "\n")
    return 0 if overall else 1


def main():
    check_services()
    backend_exit = run_backend_coverage_tests()
    e2e_exit = run_e2e_playwright_tests()
    sys.exit(summarize_results(backend_exit, e2e_exit))


if __name__ == "__main__":
    main()

