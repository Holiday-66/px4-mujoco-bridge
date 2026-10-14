#!/usr/bin/env python3
"""Audit the standalone source tree without publishing or changing any file."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    ".gitignore", ".github/workflows/tests.yml", "README.md", "NOTICE.md",
    "CONTRIBUTING.md", "SECURITY.md", "RELEASE_CHECKLIST.md", "LICENSE",
    "pyproject.toml", "MANIFEST.in", "requirements-tested.txt", "scripts/check_release.py",
    "docs/setup.md", "docs/architecture.md", "docs/models.md",
    "docs/troubleshooting.md", "docs/validation.md", "docs/validation-result.json",
    "tests/test_bridge.py", "tests/test_lifecycle.py", "tests/test_release.py",
    "src/px4_mujoco_bridge/__init__.py", "src/px4_mujoco_bridge/__main__.py",
    "src/px4_mujoco_bridge/cli.py", "src/px4_mujoco_bridge/model.py",
    "src/px4_mujoco_bridge/frames.py", "src/px4_mujoco_bridge/sensors.py",
    "src/px4_mujoco_bridge/transport.py", "src/px4_mujoco_bridge/demo.py",
    "src/px4_mujoco_bridge/models/quadrotor.xml",
}
SKIP = {".git", ".venv", ".local", "runs", "build", "dist", "__pycache__", ".pytest_cache"}
PATTERNS = {
    "home-directory path": re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
    "GitHub token shape": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "private key header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access-key shape": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def candidates():
    if (ROOT / ".git").is_dir():
        top = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], text=True).strip()
        if Path(top).resolve() != ROOT:
            raise RuntimeError("Refusing to audit an inherited parent repository")
        raw = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
        return sorted(set(p.decode() for p in raw.split(b"\0") if p))
    found = []
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.endswith(".egg-info")]
        found.extend(str((Path(directory) / name).relative_to(ROOT)) for name in files)
    return sorted(found)


def release_marker_errors(license_text, readme, metadata, notice):
    """Check recorded release markers, not legal ownership or authorization."""
    failures = []
    if not license_text:
        failures.append("LICENSE: selected release license text has not been supplied")
    elif re.search(r"^Copyright[^\n]*(?:\[|<|TO BE CONFIRMED)", license_text, re.MULTILINE):
        failures.append("LICENSE: copyright-holder placeholder has not been resolved")
    if "Local draft" in readme:
        failures.append("README: still marked as an unreleased local draft")
    if not re.search(r'^license\s*=\s*"BSD-3-Clause"\s*$', metadata, re.MULTILINE):
        failures.append("pyproject.toml: selected BSD-3-Clause license metadata missing")
    for marker in ("Ownership confirmation", "Publication approval"):
        if f"{marker}: confirmed." not in notice.splitlines():
            failures.append(f"NOTICE: {marker.lower()} is not recorded as confirmed")
    return failures


def audit(ready=False):
    failures = []
    names = candidates()
    for name in names:
        path = ROOT / name
        if name not in ALLOWED:
            failures.append(f"{name}: not in reviewed file allowlist")
            continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            failures.append(f"{name}: must be an ordinary file within this checkout")
            continue
        if path.stat().st_size > 350_000:
            failures.append(f"{name}: unexpectedly large file")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"{name}: unexpected binary content")
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                failures.append(f"{name}: possible {label}; inspect locally")
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if "://" in target or target.startswith("#") or target.startswith("mailto:"):
                    continue
                local = target.split("#", 1)[0]
                destination = (path.parent / local).resolve()
                if not destination.is_relative_to(ROOT) or not destination.exists():
                    failures.append(f"{name}: missing or external local link {target}")
    for required in ALLOWED:
        if required not in names:
            failures.append(f"{required}: required release file missing")
    if ready:
        failures.extend(release_marker_errors(*(
            (ROOT / name).read_text() if (ROOT / name).is_file() else ""
            for name in ("LICENSE", "README.md", "pyproject.toml", "NOTICE.md")
        )))
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"PASS: {len(names)} allowlisted text files; no flagged patterns or broken local file links")
    print("This is a limited hygiene check, not ownership clearance or a comprehensive secret scan.")
    if not ready:
        print("Use --ready to additionally check recorded publication and license markers.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready", action="store_true", help="Also require recorded publication and license markers")
    args = parser.parse_args()
    raise SystemExit(audit(args.ready))
