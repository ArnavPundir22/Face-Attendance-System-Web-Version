#!/usr/bin/env python3
"""
BioSecure AI — Distribution Build Helper (scripts/build_dist.py)

Compiles Python source files into optimized bytecode (.pyc), packages runtime assets,
and strips source (.py) files to produce a tamper-resistant production distribution.

Usage:
    python scripts/build_dist.py [--dist-dir dist] [--clean] [--optimize 1] [--verify] [--no-license]
"""

from __future__ import annotations

import argparse
import compileall
import os
from pathlib import Path
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Files and directories to package into distribution
DIST_INCLUDE = [
    "src",
    "nginx",
    "scripts/launchers",
    "wsgi.py",
    "app.py",
    "gunicorn.conf.py",
    "start_face_attendance.sh",
    "start_face_attendance.bat",
    "start_with_tunnel.bat",
    "requirements.txt",
    "requirements-windows.txt",
    ".env.example",
    "Procfile",
    "deploy",
]

# Sensitive artifacts strictly forbidden from distribution
DIST_FORBIDDEN = [
    "developer_private_key.pem",
    ".license_state",
    ".env",
    "tests",
    ".agents",
    ".git",
    ".pytest_cache",
    "scripts/devtools",
    "scripts/empirical_cache_stress_test.py",
    "license_console.sh",
    "license_console.bat",
    "license_kit",
    ".theme",
]


def build_dist(
    dist_dir: Path,
    clean: bool = True,
    optimize: int = 1,
    verify: bool = True,
    include_license: bool = True,
) -> int:
    """Compile and assemble the stripped distribution folder."""
    print("=" * 60)
    print("BioSecure AI — Distribution Packaging Pipeline")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Target Dist:  {dist_dir.resolve()}")
    print(f"Python Minor: {sys.version.split()[0]}")
    print(f"Optimization: Level {optimize} (0=none, 1=asserts stripped, 2=docstrings stripped)")

    # 1. Clean previous build if requested
    if dist_dir.exists() and clean:
        print(f"Cleaning previous distribution directory: {dist_dir}...")
        shutil.rmtree(dist_dir)

    dist_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copy allowed assets
    for item in DIST_INCLUDE:
        src_path = PROJECT_ROOT / item
        dest_path = dist_dir / item

        if not src_path.exists():
            continue

        if src_path.is_dir():
            shutil.copytree(
                src_path,
                dest_path,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.swp"),
                dirs_exist_ok=True,
            )
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)

    # Copy .license if present in root and requested
    license_src = PROJECT_ROOT / ".license"
    if include_license and license_src.exists():
        shutil.copy2(license_src, dist_dir / ".license")
        print("Included existing .license token in distribution.")

    # Create empty runtime directories
    (dist_dir / "known_faces").mkdir(parents=True, exist_ok=True)
    (dist_dir / "nginx" / "logs").mkdir(parents=True, exist_ok=True)
    (dist_dir / "nginx" / "temp").mkdir(parents=True, exist_ok=True)

    # 3. Compile all .py to legacy in-place .pyc
    print("Compiling Python sources to optimized bytecode (.pyc)...")
    compile_success = compileall.compile_dir(
        str(dist_dir),
        force=True,
        legacy=True,
        optimize=optimize,
        quiet=1,
    )
    if not compile_success:
        print("Error: Bytecode compilation encountered errors.", file=sys.stderr)
        return 1

    # 4. Strip .py files
    # Note: Retain nginx/setup_nginx.py for shell/bat launcher compatibility
    stripped_count = 0
    retained_scripts = {"setup_nginx.py"}
    for root, dirs, files in os.walk(dist_dir):
        # Remove any lingering __pycache__ folders
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)
        for f in files:
            if f.endswith(".py") and f not in retained_scripts:
                os.remove(os.path.join(root, f))
                stripped_count += 1

    print(f"Stripped {stripped_count} Python source (.py) files.")

    # 5. Security Guardrails: Purge forbidden files
    for forbidden in DIST_FORBIDDEN:
        f_path = dist_dir / forbidden
        if f_path.exists():
            if f_path.is_dir():
                shutil.rmtree(f_path)
            else:
                f_path.unlink()

    # Verify forbidden artifacts are strictly absent
    assert not (dist_dir / "developer_private_key.pem").exists(), "SECURITY VIOLATION: Private key found in dist!"
    assert not (dist_dir / ".license_state").exists(), "SECURITY VIOLATION: .license_state found in dist!"
    assert not (dist_dir / ".env").exists(), "SECURITY VIOLATION: .env found in dist!"
    assert not (dist_dir / "tests").exists(), "TEST LEAK: tests directory found in dist!"

    # Verify essential artifacts are present
    assert (dist_dir / "wsgi.pyc").exists(), "Critical error: wsgi.pyc missing from dist!"
    assert (dist_dir / "src" / "__init__.pyc").exists(), "Critical error: src/__init__.pyc missing from dist!"
    assert (dist_dir / "src" / "security" / "license_public_key.pem").exists(), "Critical error: license_public_key.pem missing!"

    # Ensure executable permissions on shell scripts
    for sh_file in dist_dir.rglob("*.sh"):
        try:
            sh_file.chmod(0o755)
        except OSError:
            pass

    print(f"Distribution build completed successfully at: {dist_dir.resolve()}")

    # 6. Optional Verification Smoke Test
    if verify:
        print("Running distribution verification smoke test...")
        smoke_state = dist_dir / ".smoke_test_license_state.tmp"
        env = os.environ.copy()
        env["FLASK_SECRET_KEY"] = "dist_verify_test_secret_key_1234567890"
        env["SUPABASE_URL"] = "https://example.supabase.co"
        env["SUPABASE_SERVICE_ROLE_KEY"] = "dummy_service_key_for_build_test"
        env["LICENSE_STATE_PATH"] = str(smoke_state)

        verify_cmd = (
            "import sys; "
            "sys.path.insert(0, '.'); "
            "import wsgi; "
            "print('Verified: wsgi imported successfully, app=', type(wsgi.app).__name__)"
        )
        proc = subprocess.run(
            [sys.executable, "-c", verify_cmd],
            cwd=str(dist_dir),
            env=env,
            capture_output=True,
            text=True,
        )
        if smoke_state.exists():
            smoke_state.unlink()
        if (dist_dir / ".license_state").exists():
            (dist_dir / ".license_state").unlink()

        if proc.returncode != 0:
            print(f"Distribution smoke test failed!\nStderr: {proc.stderr}", file=sys.stderr)
            return 1
        print("Smoke test PASSED: " + proc.stdout.strip())

    # Final Security Assertions
    assert not (dist_dir / "developer_private_key.pem").exists(), "SECURITY VIOLATION: Private key found in dist!"
    assert not (dist_dir / ".license_state").exists(), "SECURITY VIOLATION: .license_state found in dist!"
    assert not (dist_dir / ".env").exists(), "SECURITY VIOLATION: .env found in dist!"
    assert not (dist_dir / "tests").exists(), "TEST LEAK: tests directory found in dist!"

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="BioSecure AI Distribution Build Helper")
    parser.add_argument("--dist-dir", "-o", default="dist", help="Output directory (default: dist)")
    parser.add_argument("--clean", dest="clean", action="store_true", default=True, help="Wipe target dist directory first (default: True)")
    parser.add_argument("--no-clean", dest="clean", action="store_false", help="Do not wipe target dist directory")
    parser.add_argument("--optimize", type=int, choices=[0, 1, 2], default=1, help="Bytecode optimization level (default: 1)")
    parser.add_argument("--verify", dest="verify", action="store_true", default=True, help="Run post-build verification smoke test (default: True)")
    parser.add_argument("--no-verify", dest="verify", action="store_false", help="Skip post-build verification smoke test")
    parser.add_argument("--no-license", dest="include_license", action="store_false", help="Do not bundle root .license file")

    args = parser.parse_args()
    dist_path = Path(args.dist_dir)
    sys.exit(
        build_dist(
            dist_path,
            clean=args.clean,
            optimize=args.optimize,
            verify=args.verify,
            include_license=args.include_license,
        )
    )


if __name__ == "__main__":
    main()
