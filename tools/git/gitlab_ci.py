#!/usr/bin/env python3
"""Operate only the configured private M1 GitLab project without exposing its token.

The owner supplies GITLAB_PROJECT_URL and GITLAB_API_TOKEN in the ignored,
owner-only .env file. This utility never stores credentials in a Git remote,
command argument, log, or CI variable. Push is non-forced and branch-limited.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
BRANCH = "codex/v1-m1"
REQUIRED_JOBS = frozenset(
    {"foundation_test", "foundation_quality", "foundation_build", "foundation_docs"}
)


def blocked(code: str) -> NoReturn:
    print(f"GITLAB-M1: BLOCKED — {code}")
    raise SystemExit(3)


def failed(code: str) -> NoReturn:
    print(f"GITLAB-M1: FAILED — {code}")
    raise SystemExit(1)


def local_settings() -> tuple[str, str]:
    """Read only the two approved development settings from an owner-only file."""
    try:
        info = ENV_FILE.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            blocked("env_not_owner_regular_file")
        if stat.S_IMODE(info.st_mode) & 0o077:
            blocked("env_permissions_not_owner_only")
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        blocked("env_unavailable")
    values: dict[str, str] = {}
    for line in lines:
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name not in {"GITLAB_PROJECT_URL", "GITLAB_API_TOKEN"}:
            continue
        if name in values:
            blocked("duplicate_development_setting")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name] = value
    url = values.get("GITLAB_PROJECT_URL", "")
    token = values.get("GITLAB_API_TOKEN", "")
    if not url or not token:
        blocked("gitlab_development_settings_missing")
    if not 16 <= len(token) <= 1024 or any(not 33 <= ord(c) <= 126 for c in token):
        blocked("gitlab_token_format_invalid")
    return url, token


def project_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != "gitlab.com"
        or parts.port is not None
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        blocked("project_url_not_plain_gitlab_https")
    path = parts.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    segments = path.split("/")
    if len(segments) < 2 or any(
        not segment or segment in {".", ".."} or "%" in segment for segment in segments
    ):
        blocked("project_path_invalid")
    return path


def repo_url(url: str) -> str:
    return "https://gitlab.com/" + project_path(url) + ".git"


def api_get(endpoint: str, token: str) -> object:
    request = urllib.request.Request(
        "https://gitlab.com/api/v4" + endpoint,
        headers={"PRIVATE-TOKEN": token, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        blocked(f"gitlab_api_http_{error.code}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        blocked("gitlab_api_unavailable")


def project(url: str, token: str) -> int:
    result = api_get(
        "/projects/" + urllib.parse.quote(project_path(url), safe=""), token
    )
    if not isinstance(result, dict) or not isinstance(result.get("id"), int):
        blocked("gitlab_project_response_invalid")
    if result.get("visibility") != "private":
        blocked("gitlab_project_not_private")
    if result.get("builds_access_level") == "disabled":
        blocked("gitlab_ci_disabled")
    return result["id"]


def lint(project_id: int, token: str) -> None:
    """Validate the checked-out CI file in the real GitLab project context."""
    try:
        content = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        blocked("ci_configuration_unavailable")
    request = urllib.request.Request(
        f"https://gitlab.com/api/v4/projects/{project_id}/ci/lint",
        data=json.dumps({"content": content, "include_jobs": True}).encode(),
        headers={"PRIVATE-TOKEN": token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        blocked(f"ci_lint_http_{error.code}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        blocked("ci_lint_unavailable")
    if not isinstance(result, dict) or not isinstance(result.get("jobs"), list):
        blocked("ci_lint_response_invalid")
    names = {str(job.get("name")) for job in result["jobs"] if isinstance(job, dict)}
    if result.get("valid") is not True or not REQUIRED_JOBS <= names:
        failed("ci_lint_invalid_or_required_job_missing")
    print("GITLAB-M1: CI_LINT_PASSED required_jobs=4")


def git_environment() -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "GIT_ASKPASS": str(Path(__file__).resolve()),
        "GIT_TERMINAL_PROMPT": "0",
        "AGENTMONITOR_GITLAB_ASKPASS": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TRACE": "0",
        "GIT_TRACE_CURL": "0",
        "GIT_TRACE_PACKET": "0",
    }
    for name in (
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
        "https_proxy",
        "http_proxy",
        "no_proxy",
    ):
        if name in os.environ:
            environment[name] = os.environ[name]
    return environment


def git(
    *arguments: str, authenticated: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "credential.helper=", *arguments],
        cwd=ROOT,
        env=git_environment() if authenticated else None,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )


def askpass(prompt: str) -> int:
    if "username" in prompt.lower():
        print("oauth2")
        return 0
    if "password" in prompt.lower():
        _, token = local_settings()
        sys.stdout.write(token + "\n")
        return 0
    return 1


def configure(url: str, token: str) -> None:
    project_id = project(url, token)
    desired = repo_url(url)
    current = git("remote", "get-url", "origin")
    if current.returncode == 0:
        if current.stdout.strip() != desired:
            blocked("existing_origin_differs_from_configured_project")
    else:
        added = git("remote", "add", "origin", desired)
        if added.returncode:
            failed("origin_configuration_failed")
    print(f"GITLAB-M1: PROJECT_VERIFIED id={project_id} private=true")
    print("GITLAB-M1: ORIGIN_CONFIGURED token_in_url=false")


def probe(url: str, token: str) -> None:
    project_id = project(url, token)
    result = git("ls-remote", "--heads", repo_url(url), authenticated=True)
    if result.returncode:
        blocked("authenticated_git_transport_unavailable")
    print(f"GITLAB-M1: PROJECT_VERIFIED id={project_id} private=true")
    print("GITLAB-M1: AUTHENTICATED_GIT_READ_PASSED")


def push(url: str, token: str) -> None:
    project(url, token)
    if git("branch", "--show-current").stdout.strip() != BRANCH:
        blocked("unexpected_local_branch")
    if git("status", "--porcelain").stdout.strip():
        blocked("tracked_or_untracked_worktree_changes")
    if git("remote", "get-url", "origin").stdout.strip() != repo_url(url):
        blocked("origin_not_configured_for_project")
    result = git(
        "push",
        "--set-upstream",
        "origin",
        f"HEAD:refs/heads/{BRANCH}",
        authenticated=True,
    )
    if result.returncode:
        failed(f"nonforced_branch_push_exit_{result.returncode}")
    print(f"GITLAB-M1: NONFORCED_BRANCH_PUSH_PASSED ref={BRANCH}")


def pipeline(project_id: int, token: str, sha: str, wait_seconds: int) -> None:
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        blocked("commit_sha_invalid")
    deadline = time.monotonic() + wait_seconds
    query = urllib.parse.urlencode({"sha": sha, "ref": BRANCH, "per_page": 20})
    while True:
        results = api_get(f"/projects/{project_id}/pipelines?{query}", token)
        if not isinstance(results, list):
            blocked("pipeline_list_invalid")
        matches = [
            item
            for item in results
            if item.get("sha") == sha and item.get("ref") == BRANCH
        ]
        if matches:
            item = matches[0]
            pipeline_id = item.get("id")
            status = item.get("status")
            if not isinstance(pipeline_id, int) or not isinstance(status, str):
                blocked("pipeline_response_invalid")
            print(f"GITLAB-M1: PIPELINE id={pipeline_id} status={status}", flush=True)
            if status in {"success", "failed", "canceled", "skipped", "manual"}:
                jobs = api_get(
                    f"/projects/{project_id}/pipelines/{pipeline_id}/jobs?per_page=100",
                    token,
                )
                if not isinstance(jobs, list):
                    blocked("pipeline_jobs_invalid")
                actual = {str(job.get("name")): str(job.get("status")) for job in jobs}
                for name in sorted(REQUIRED_JOBS):
                    print(f"GITLAB-M1: JOB {name} {actual.get(name, 'Not Run')}")
                if status == "success" and all(
                    actual.get(name) == "success" for name in REQUIRED_JOBS
                ):
                    print("GITLAB-M1: HOSTED_GATE_PASSED")
                    return
                failed("hosted_pipeline_or_required_job_not_green")
        else:
            print("GITLAB-M1: PIPELINE_PENDING", flush=True)
        if time.monotonic() >= deadline:
            blocked("hosted_pipeline_timeout")
        time.sleep(15)


def main() -> int:
    if os.environ.get("AGENTMONITOR_GITLAB_ASKPASS") == "1":
        return askpass(sys.argv[1] if len(sys.argv) == 2 else "")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("probe", "configure", "lint", "push", "pipeline")
    )
    parser.add_argument("--sha")
    parser.add_argument("--wait-seconds", type=int, default=1200)
    args = parser.parse_args()
    url, token = local_settings()
    if args.action == "probe":
        probe(url, token)
    elif args.action == "configure":
        configure(url, token)
    elif args.action == "lint":
        lint(project(url, token), token)
    elif args.action == "push":
        push(url, token)
    else:
        if args.sha is None or not 0 <= args.wait_seconds <= 3600:
            blocked("pipeline_arguments_invalid")
        pipeline(project(url, token), token, args.sha, args.wait_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
