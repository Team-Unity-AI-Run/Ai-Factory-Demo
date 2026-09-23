"""
Generates a GitHub Actions CI/CD workflow YAML file from structured
requirement JSON produced by analyze_requirement.py.

Supports Python projects for this demo (per spec). Other languages fall
back to a minimal generic pipeline.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict

import yaml


def generate_python_workflow(reqs: Dict[str, Any]) -> str:
    docker = reqs.get("docker", False)
    security_scan = reqs.get("security_scan", False)
    testing = reqs.get("testing", False)

    steps = [
        {"name": "Checkout", "uses": "actions/checkout@v4"},
        {
            "name": "Setup Python",
            "uses": "actions/setup-python@v5",
            "with": {"python-version": "3.12"},
        },
        {"name": "Install dependencies", "run": "pip install -r requirements.txt"},
    ]

    if testing:
        steps.append({"name": "Run tests", "run": "pytest"})

    if security_scan:
        steps.append(
            {
                "name": "Security scan",
                "run": "pip install bandit\nbandit -r . -x tests,examples",
            }
        )

    if docker:
        steps.append(
            {"name": "Build Docker image", "run": "docker build -t demo-app ."}
        )
        steps.append(
            {
                "name": "Scan Docker image",
                "uses": "aquasecurity/trivy-action@master",
                "with": {
                    "image-ref": "demo-app",
                    "severity": "HIGH,CRITICAL",
                    "exit-code": "1",
                },
            }
        )

    if reqs.get("kubernetes"):
        steps.append(
            {
                "name": "Deploy to Kubernetes (manual approval required)",
                "run": (
                    "echo 'Kubernetes deployment step is a placeholder for this demo. "
                    "Configure kubectl/helm and cluster credentials via GitHub Secrets "
                    "before enabling real deployment.'"
                ),
            }
        )

    workflow = {
        "name": "CI/CD",
        "on": {
            "push": {"branches": ["main"]},
            "pull_request": {},
        },
        "permissions": {
            "contents": "read",
        },
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": steps,
            }
        },
    }
    return yaml.dump(workflow, sort_keys=False, default_flow_style=False)


def generate_generic_workflow(reqs: Dict[str, Any]) -> str:
    workflow = {
        "name": "CI/CD",
        "on": {"push": {"branches": ["main"]}, "pull_request": {}},
        "permissions": {"contents": "read"},
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"name": "Checkout", "uses": "actions/checkout@v4"},
                    {
                        "name": "Placeholder build step",
                        "run": f"echo 'No dedicated template for language: {reqs.get('language')}'",
                    },
                ],
            }
        },
    }
    return yaml.dump(workflow, sort_keys=False, default_flow_style=False)


def generate_workflow(reqs: Dict[str, Any]) -> str:
    language = (reqs.get("language") or "").lower()
    if language == "python":
        return generate_python_workflow(reqs)
    return generate_generic_workflow(reqs)


def validate_yaml(content: str) -> bool:
    try:
        yaml.safe_load(content)
        return True
    except yaml.YAMLError as exc:
        print(f"[generate_workflow] YAML validation failed: {exc}")
        return False


def main() -> None:
    if len(sys.argv) > 1:
        reqs = json.loads(sys.argv[1])
    else:
        with open("requirement_analysis.json", "r", encoding="utf-8") as fh:
            reqs = json.load(fh)

    content = generate_workflow(reqs)

    if not validate_yaml(content):
        raise SystemExit(1)

    output_file = "generated-ci-cd.yml"
    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"Generated workflow written to {output_file}")
    print(content)


if __name__ == "__main__":
    main()
