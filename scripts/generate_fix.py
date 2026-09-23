"""
AI fix engine.

Given a detected issue (from scan_code.py) and the relevant source snippet,
generates:
  1. Explanation of the problem
  2. Corrected code
  3. Minimal patch/change
  4. Reason for the fix

Uses OpenAI when OPENAI_API_KEY is configured; otherwise applies
deterministic template-based fixes for the known issue types so the demo
still works without a key.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

SYSTEM_PROMPT = (
    "You are a secure-coding assistant. You will be given a single detected "
    "security issue and the offending line of code. Return ONLY a JSON object "
    "with fields: explanation (string), fixed_code (string, the corrected line "
    "or minimal block), reason (string). Do not modify unrelated code. JSON only."
)


class AIFixClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, issue: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if not self.available:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            user_prompt = json.dumps(issue)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            print(f"[generate_fix] AI call failed, falling back to templates: {exc}")
            return None


def template_fix(issue: Dict[str, Any]) -> Dict[str, str]:
    """Deterministic fallback fixes keyed by issue type."""
    issue_type = issue.get("issue", "")
    code = issue.get("code", "")

    if "password" in issue_type.lower():
        var_name = code.split("=")[0].strip() if "=" in code else "password"
        return {
            "explanation": "A password is hardcoded directly in source code, which exposes it to "
            "anyone with repository access and to version history.",
            "fixed_code": f'{var_name} = os.environ.get("{var_name.upper()}")',
            "reason": "Secrets must be loaded from environment variables or GitHub Secrets, never committed to source.",
        }

    if "api key" in issue_type.lower() or "secret" in issue_type.lower():
        var_name = code.split("=")[0].strip() if "=" in code else "api_key"
        return {
            "explanation": "An API key or secret is hardcoded directly in source code.",
            "fixed_code": f'{var_name} = os.environ.get("{var_name.upper()}")',
            "reason": "Credentials must come from GitHub Secrets/environment variables, not committed code.",
        }

    if "debug print" in issue_type.lower():
        return {
            "explanation": "A debug print statement was left in the code, which can leak internal data in logs.",
            "fixed_code": "# removed debug print; use logging.debug(...) instead if needed",
            "reason": "Print statements should not be used for production logging or left as debug artifacts.",
        }

    if "shell" in issue_type.lower() or "eval" in issue_type.lower():
        return {
            "explanation": "Use of shell=True, os.system, eval, or exec can allow command/code injection.",
            "fixed_code": "subprocess.run([\"<command>\", \"<arg1>\"], shell=False, check=True)",
            "reason": "Avoiding shell=True/eval/exec removes the primary vector for shell/code injection.",
        }

    return {
        "explanation": f"Detected issue: {issue_type}",
        "fixed_code": code,
        "reason": "No automated template fix available; manual review recommended.",
    }


def generate_fix(issue: Dict[str, Any]) -> Dict[str, Any]:
    client = AIFixClient()
    ai_result = client.generate(issue)
    fix = ai_result if ai_result else template_fix(issue)

    return {
        "file": issue.get("file"),
        "line": issue.get("line"),
        "issue": issue.get("issue"),
        "severity": issue.get("severity"),
        "explanation": fix.get("explanation"),
        "fixed_code": fix.get("fixed_code"),
        "reason": fix.get("reason"),
    }


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as fh:
            issues = json.load(fh)
    else:
        with open("scan_results.json", "r", encoding="utf-8") as fh:
            issues = json.load(fh)

    if isinstance(issues, dict):
        issues = [issues]

    fixes = [generate_fix(issue) for issue in issues]

    print(json.dumps(fixes, indent=2))

    with open("fixes.json", "w", encoding="utf-8") as fh:
        json.dump(fixes, fh, indent=2)


if __name__ == "__main__":
    main()
