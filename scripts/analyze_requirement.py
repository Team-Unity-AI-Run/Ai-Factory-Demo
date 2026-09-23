"""
AI-powered requirement analyzer.

Reads a GitHub Issue title/body and extracts structured DevOps requirements
using an LLM (OpenAI) when OPENAI_API_KEY is available, otherwise falls back
to a deterministic keyword-based parser so the demo works without secrets.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, Optional

STRUCTURED_SCHEMA_EXAMPLE = {
    "language": "python",
    "framework": "fastapi",
    "testing": True,
    "security_scan": True,
    "docker": True,
    "kubernetes": True,
    "cloud": "azure",
}

SYSTEM_PROMPT = (
    "You are a DevOps requirement analyzer. Read a GitHub issue describing an "
    "application/infrastructure requirement and return ONLY a JSON object with "
    "these fields: language (string), framework (string or null), testing (bool), "
    "security_scan (bool), docker (bool), kubernetes (bool), cloud (string or null), "
    "deployment (string or null). No prose, no markdown fences, JSON only."
)


class AIClient:
    """Thin wrapper around the OpenAI API. Falls back to None if no API key."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def analyze(self, title: str, body: str) -> Optional[Dict[str, Any]]:
        """Call the LLM to analyze the issue. Returns None on any failure."""
        if not self.available:
            return None
        try:
            from openai import OpenAI  # imported lazily so tests don't require the package

            client = OpenAI(api_key=self.api_key)
            user_prompt = f"Issue title: {title}\n\nIssue body:\n{body}"
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            content = response.choices[0].message.content.strip()
            content = re.sub(r"^```json|```$", "", content, flags=re.MULTILINE).strip()
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001 - demo-grade fallback, never crash
            print(f"[analyze_requirement] AI call failed, falling back to keyword parser: {exc}")
            return None


def keyword_based_analysis(title: str, body: str) -> Dict[str, Any]:
    """Deterministic fallback analyzer used when no AI provider is configured."""
    text = f"{title}\n{body}".lower()

    def has(*keywords: str) -> bool:
        return any(k in text for k in keywords)

    language = "python" if has("python", "fastapi", "pytest", "bandit") else (
        "node" if has("node", "javascript", "npm", "express") else "python"
    )

    framework = None
    if "fastapi" in text:
        framework = "fastapi"
    elif "flask" in text:
        framework = "flask"
    elif "django" in text:
        framework = "django"
    elif "express" in text:
        framework = "express"

    cloud = None
    if has("azure"):
        cloud = "azure"
    elif has("aws"):
        cloud = "aws"
    elif has("gcp", "google cloud"):
        cloud = "gcp"

    return {
        "language": language,
        "framework": framework,
        "testing": has("test", "pytest", "unit test"),
        "security_scan": has("security", "bandit", "vulnerab", "scan"),
        "docker": has("docker", "container", "image"),
        "kubernetes": has("kubernetes", "k8s", "deploy to kubernetes"),
        "cloud": cloud,
        "deployment": "kubernetes" if has("kubernetes", "k8s") else ("docker" if has("docker") else None),
    }


def analyze_requirement(title: str, body: str) -> Dict[str, Any]:
    """Analyze an issue and return structured requirement JSON.

    Tries the AI client first, falls back to keyword parsing, and always
    fills any missing fields from the fallback so downstream code can rely
    on a complete schema.
    """
    fallback = keyword_based_analysis(title, body)

    client = AIClient()
    ai_result = client.analyze(title, body)
    if not ai_result:
        return fallback

    merged = dict(fallback)
    merged.update({k: v for k, v in ai_result.items() if v is not None})
    return merged


def _read_issue_from_env() -> Dict[str, str]:
    """Read issue title/body from GitHub Actions event environment variables."""
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")
    if not title and not body:
        raise SystemExit("ISSUE_TITLE/ISSUE_BODY env vars not set and no CLI args given")
    return {"title": title, "body": body}


def main() -> None:
    if len(sys.argv) >= 3:
        title, body = sys.argv[1], sys.argv[2]
    else:
        issue = _read_issue_from_env()
        title, body = issue["title"], issue["body"]

    result = analyze_requirement(title, body)
    print(json.dumps(result, indent=2))

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(f"requirements={json.dumps(result)}\n")

    with open("requirement_analysis.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)


if __name__ == "__main__":
    main()
