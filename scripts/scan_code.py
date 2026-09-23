"""
Static code scanner for the demo.

Detects common security issues in Python source files without requiring
external services:
  - hardcoded passwords
  - hardcoded API keys / secrets / tokens
  - debug print statements
  - dangerous shell / eval / exec usage
  - use of shell=True in subprocess calls

Outputs a JSON list of findings compatible with generate_fix.py.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Any, Dict, List

PASSWORD_PATTERN = re.compile(
    r'\b(password|passwd|pwd)\s*=\s*[\'"][^\'"]+[\'"]', re.IGNORECASE
)
SECRET_PATTERN = re.compile(
    r'\b(api[_-]?key|secret|token|access[_-]?key)\s*=\s*[\'"][^\'"]+[\'"]',
    re.IGNORECASE,
)
DEBUG_PRINT_PATTERN = re.compile(r"^\s*print\(", re.IGNORECASE)
DANGEROUS_SHELL_PATTERN = re.compile(
    r"\b(os\.system|subprocess\.(call|run|Popen)\([^)]*shell\s*=\s*True|eval\(|exec\()"
)

DEFAULT_EXCLUDE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__"}


def scan_file(path: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"[scan_code] could not read {path}: {exc}")
        return findings

    for line_no, line in enumerate(lines, start=1):
        if PASSWORD_PATTERN.search(line):
            findings.append(
                {
                    "severity": "HIGH",
                    "file": path,
                    "line": line_no,
                    "issue": "Hardcoded password",
                    "recommendation": "Use GitHub Secrets or environment variables.",
                    "code": line.strip(),
                }
            )
        if SECRET_PATTERN.search(line):
            findings.append(
                {
                    "severity": "HIGH",
                    "file": path,
                    "line": line_no,
                    "issue": "Hardcoded API key or secret",
                    "recommendation": "Use GitHub Secrets or environment variables. Never commit credentials.",
                    "code": line.strip(),
                }
            )
        if DEBUG_PRINT_PATTERN.search(line):
            findings.append(
                {
                    "severity": "LOW",
                    "file": path,
                    "line": line_no,
                    "issue": "Debug print statement",
                    "recommendation": "Remove debug prints or replace with proper logging.",
                    "code": line.strip(),
                }
            )
        if DANGEROUS_SHELL_PATTERN.search(line):
            findings.append(
                {
                    "severity": "CRITICAL",
                    "file": path,
                    "line": line_no,
                    "issue": "Dangerous shell/eval/exec usage",
                    "recommendation": "Avoid shell=True, os.system, eval, and exec. Use subprocess with argument lists.",
                    "code": line.strip(),
                }
            )

    return findings


def scan_directory(root: str = ".") -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for path in glob.glob(os.path.join(root, "**", "*.py"), recursive=True):
        if any(part in DEFAULT_EXCLUDE_DIRS for part in path.split(os.sep)):
            continue
        findings.extend(scan_file(path))
    return findings


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if os.path.isfile(target):
        findings = scan_file(target)
    else:
        findings = scan_directory(target)

    print(json.dumps(findings, indent=2))

    with open("scan_results.json", "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2)

    critical_or_high = [f for f in findings if f["severity"] in ("HIGH", "CRITICAL")]
    if critical_or_high:
        print(f"\n{len(critical_or_high)} HIGH/CRITICAL issue(s) found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
