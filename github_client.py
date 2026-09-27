"""
core/github_client.py
------------------------
Small, dependency-light GitHub integration:

- `resolve_raw_url` turns a normal github.com "blob" URL (what you'd
  copy from your browser) into the raw-content URL that actually
  returns the file's text.
- `fetch_file_from_github` downloads that file's source.
- `fetch_pr_diff` downloads a pull request's unified diff by appending
  ".diff" to its github.com URL — a small documented GitHub feature
  that needs no authentication for public repos.

No GitHub token is required for public repositories. For private
repos, pass a personal access token and it's sent as a Bearer header.
"""

import re
from dataclasses import dataclass
from typing import Optional

import requests

from utils.common import get_logger, retry_with_backoff

logger = get_logger(__name__)

BLOB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<ref>[^/]+)/(?P<path>.+)$"
)
PR_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)


@dataclass
class GithubFile:
    owner: str
    repo: str
    ref: str
    path: str
    content: str


def resolve_raw_url(url: str) -> str:
    """Convert a github.com/.../blob/... URL into its raw.githubusercontent.com equivalent.
    Already-raw URLs are returned unchanged."""
    if "raw.githubusercontent.com" in url:
        return url

    match = BLOB_URL_RE.match(url.strip())
    if not match:
        raise ValueError(
            "Expected a GitHub file URL like "
            "https://github.com/<owner>/<repo>/blob/<branch>/<path>, got: " + url
        )
    g = match.groupdict()
    return f"https://raw.githubusercontent.com/{g['owner']}/{g['repo']}/{g['ref']}/{g['path']}"


def parse_pr_url(url: str):
    match = PR_URL_RE.match(url.strip())
    if not match:
        raise ValueError(
            "Expected a GitHub PR URL like https://github.com/<owner>/<repo>/pull/<number>, "
            f"got: {url}"
        )
    g = match.groupdict()
    return g["owner"], g["repo"], int(g["number"])


@retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(requests.exceptions.RequestException,))
def fetch_file_from_github(url: str, token: Optional[str] = None) -> GithubFile:
    raw_url = resolve_raw_url(url)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    logger.info("Fetching file from GitHub: %s", raw_url)
    response = requests.get(raw_url, headers=headers, timeout=30)
    response.raise_for_status()

    match = BLOB_URL_RE.match(url.strip())
    if match:
        g = match.groupdict()
        owner, repo, ref, path = g["owner"], g["repo"], g["ref"], g["path"]
    else:
        # raw URL directly given: raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>
        parts = raw_url.replace("https://raw.githubusercontent.com/", "").split("/", 3)
        owner, repo, ref, path = (parts + ["", "", "", ""])[:4]

    return GithubFile(owner=owner, repo=repo, ref=ref, path=path, content=response.text)


@retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(requests.exceptions.RequestException,))
def fetch_pr_diff(pr_url: str, token: Optional[str] = None) -> str:
    owner, repo, number = parse_pr_url(pr_url)
    diff_url = f"https://github.com/{owner}/{repo}/pull/{number}.diff"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    logger.info("Fetching PR diff: %s", diff_url)
    response = requests.get(diff_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text
