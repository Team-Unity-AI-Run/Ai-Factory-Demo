"""
Shared helper to create a branch, commit generated/fixed files, and open a
Pull Request using the GitHub CLI (gh) when available, falling back to the
GitHub REST API via `requests`.

Never prints tokens or secrets.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import List, Optional

import requests


def run(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True)


def create_branch(branch_name: str) -> None:
    run(["git", "checkout", "-b", branch_name])


def commit_files(files: List[str], message: str) -> None:
    run(["git", "add", *files])
    run(["git", "-c", "user.name=ai-devops-bot", "-c", "user.email=ai-devops-bot@users.noreply.github.com",
         "commit", "-m", message])


def push_branch(branch_name: str) -> None:
    run(["git", "push", "-u", "origin", branch_name])


def create_pr_with_gh(title: str, body: str, base: str = "main") -> Optional[str]:
    if not shutil.which("gh"):
        return None
    result = subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body, "--base", base],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"[create_pr] gh pr create failed: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def create_pr_with_api(
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> Optional[str]:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("[create_pr] GITHUB_TOKEN or GITHUB_REPOSITORY not set; cannot call REST API.")
        return None

    url = f"https://api.github.com/repos/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"title": title, "body": body, "head": head, "base": base}
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 300:
        print(f"[create_pr] REST API PR creation failed with status {response.status_code}")
        return None
    return response.json().get("html_url")


def create_pull_request(title: str, body: str, head: str, base: str = "main") -> Optional[str]:
    pr_url = create_pr_with_gh(title, body, base=base)
    if pr_url:
        return pr_url
    return create_pr_with_api(title, body, head=head, base=base)


def main() -> None:
    """CLI entry point: create_pr.py <branch> <files.json> <title> <body_file>"""
    if len(sys.argv) < 5:
        print("Usage: create_pr.py <branch_name> <files_json> <title> <body_file>")
        sys.exit(1)

    branch_name, files_json, title, body_file = sys.argv[1:5]
    files = json.loads(files_json)
    with open(body_file, "r", encoding="utf-8") as fh:
        body = fh.read()

    create_branch(branch_name)
    commit_files(files, message=title)
    push_branch(branch_name)
    pr_url = create_pull_request(title, body, head=branch_name)

    if pr_url:
        print(f"Pull request created: {pr_url}")
    else:
        print("Pull request could not be created automatically. Push succeeded; open the PR manually.")


if __name__ == "__main__":
    main()
