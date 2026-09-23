import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from generate_workflow import generate_workflow, validate_yaml  # noqa: E402


def test_generates_valid_yaml_for_python():
    reqs = {
        "language": "python",
        "framework": "fastapi",
        "testing": True,
        "security_scan": True,
        "docker": True,
        "kubernetes": True,
        "cloud": "azure",
    }
    content = generate_workflow(reqs)
    assert validate_yaml(content)
    parsed = yaml.safe_load(content)
    assert parsed["name"] == "CI/CD"
    assert "build" in parsed["jobs"]


def test_includes_expected_steps_when_enabled():
    reqs = {
        "language": "python",
        "testing": True,
        "security_scan": True,
        "docker": True,
        "kubernetes": False,
    }
    content = generate_workflow(reqs)
    parsed = yaml.safe_load(content)
    steps = parsed["jobs"]["build"]["steps"]
    step_names = [s.get("name") for s in steps]
    assert "Run tests" in step_names
    assert "Security scan" in step_names
    assert "Build Docker image" in step_names
    assert "Scan Docker image" in step_names


def test_omits_optional_steps_when_disabled():
    reqs = {
        "language": "python",
        "testing": False,
        "security_scan": False,
        "docker": False,
        "kubernetes": False,
    }
    content = generate_workflow(reqs)
    parsed = yaml.safe_load(content)
    steps = parsed["jobs"]["build"]["steps"]
    step_names = [s.get("name") for s in steps]
    assert "Run tests" not in step_names
    assert "Build Docker image" not in step_names


def test_generic_fallback_for_unknown_language():
    reqs = {"language": "rust"}
    content = generate_workflow(reqs)
    assert validate_yaml(content)


def test_invalid_yaml_is_detected():
    assert validate_yaml("key: [unclosed") is False
