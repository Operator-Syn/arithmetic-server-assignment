#!/usr/bin/env python3
"""Build the final arithmetic-server submission ZIP.

This script intentionally refuses to package placeholder-only submissions. Run
the server, generate screenshots/logs/report.pdf, then run:

    python3 make_submission_zip.py <surname>
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_FILES = [
    Path("logs/l1_telnet_recv.log"),
    Path("logs/l2_pipelined_recv.log"),
    Path("logs/l3_drip_recv.log"),
]
REQUIRED_FILES = [
    Path("arithmetic_server.py"),
    Path("bench_client.py"),
    Path("drip_client.py"),
    Path("screenshots.pdf"),
    Path("report.pdf"),
    *LOG_FILES,
]


def existing_report_path() -> Path:
    candidates = [Path("report.pdf"), Path("report/report.pdf")]

    for candidate in candidates:
        if (ROOT / candidate).is_file():
            return candidate

    return Path("report.pdf")


def validate_required_files() -> list[str]:
    missing: list[str] = []

    required = REQUIRED_FILES.copy()
    required[required.index(Path("report.pdf"))] = existing_report_path()

    for relative_path in required:
        full_path = ROOT / relative_path

        if not full_path.is_file() or full_path.stat().st_size == 0:
            missing.append(str(relative_path))

    return missing


def add_file(zip_file: zipfile.ZipFile, relative_path: Path, archive_path: Path | None = None) -> None:
    full_path = ROOT / relative_path
    zip_file.write(full_path, archive_path or relative_path)


def add_directory(zip_file: zipfile.ZipFile, relative_dir: Path) -> None:
    for path in sorted((ROOT / relative_dir).rglob("*")):
        if path.is_file():
            relative_path = path.relative_to(ROOT)
            add_file(zip_file, relative_path)


def build_zip(surname: str) -> Path:
    output_path = ROOT / f"{surname}_arithmetic.zip"
    report_path = existing_report_path()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        add_file(zip_file, Path("arithmetic_server.py"))
        add_file(zip_file, Path("bench_client.py"))
        add_file(zip_file, Path("drip_client.py"))
        add_file(zip_file, Path("screenshots.pdf"))
        add_file(zip_file, report_path, Path("report.pdf"))

        add_directory(zip_file, Path("logs"))
        add_directory(zip_file, Path("benchmarks"))

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surname", help="surname prefix for <surname>_arithmetic.zip")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    missing = validate_required_files()

    if missing:
        print("Cannot build submission ZIP. Missing or empty required file(s):", file=sys.stderr)
        for path in missing:
            print(f"- {path}", file=sys.stderr)
        raise SystemExit(1)

    output_path = build_zip(args.surname)
    print(f"Created {output_path}")


if __name__ == "__main__":
    main()
