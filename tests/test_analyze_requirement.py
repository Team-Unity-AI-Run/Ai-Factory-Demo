import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from analyze_requirement import analyze_requirement, keyword_based_analysis  # noqa: E402


SAMPLE_TITLE = "Generate CI/CD Pipeline"
SAMPLE_BODY = """
Create a CI/CD pipeline for a Python FastAPI application.

Requirements:
- Install Python dependencies.
- Run unit tests using pytest.
- Run a security scan.
- Build a Docker image.
- Scan the Docker image.
- Deploy to Kubernetes.
- Use GitHub Actions.
- Do not expose secrets in the workflow.
"""


def test_keyword_analysis_detects_python_and_fastapi():
    result = keyword_based_analysis(SAMPLE_TITLE, SAMPLE_BODY)
    assert result["language"] == "python"
    assert result["framework"] == "fastapi"
    assert result["testing"] is True
    assert result["security_scan"] is True
    assert result["docker"] is True
    assert result["kubernetes"] is True


def test_analyze_requirement_falls_back_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = analyze_requirement(SAMPLE_TITLE, SAMPLE_BODY)
    assert result["language"] == "python"
    assert result["docker"] is True


def test_keyword_analysis_detects_cloud_provider():
    result = keyword_based_analysis("Deploy to Azure", "Use Azure Kubernetes Service")
    assert result["cloud"] == "azure"


def test_keyword_analysis_no_docker_mentioned():
    result = keyword_based_analysis("Simple script", "Just run a python script on a schedule")
    assert result["docker"] is False
