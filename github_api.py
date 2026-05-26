import httpx
from constants import GITHUB_REPO, GITHUB_API, DOC_SEARCH_URL, ISSUE_SEARCH_URL


def _build_headers(pat=None):
    """构造带可选 PAT 认证的 GitHub API 请求头"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if pat:
        headers["Authorization"] = f"token {pat}"
    return headers


async def get_latest_release(client: httpx.AsyncClient):
    """获取最新 Release"""
    resp = await client.get(
        f"{GITHUB_API}/releases/latest",
        headers=_build_headers(),
        timeout=10,
    )
    return resp.status_code, resp


async def get_repo_stats(client: httpx.AsyncClient, pat=""):
    """获取仓库统计信息"""
    resp = await client.get(
        GITHUB_API,
        headers=_build_headers(pat),
        timeout=10,
    )
    return resp.status_code, resp


async def get_release(client: httpx.AsyncClient, tag: str, pat=""):
    """获取指定 tag 的 Release"""
    resp = await client.get(
        f"{GITHUB_API}/releases/tags/{tag}",
        headers=_build_headers(pat),
        timeout=10,
    )
    return resp.status_code, resp


async def get_releases(client: httpx.AsyncClient, per_page=5, pat=""):
    """获取最近的 Release 列表"""
    resp = await client.get(
        f"{GITHUB_API}/releases",
        params={"per_page": per_page},
        headers=_build_headers(pat),
        timeout=10,
    )
    return resp.status_code, resp


async def search_docs(client: httpx.AsyncClient, keyword: str, pat=""):
    """搜索文档"""
    resp = await client.get(
        DOC_SEARCH_URL,
        params={
            "q": f"{keyword} repo:{GITHUB_REPO} path:docs/ extension:mdx",
            "per_page": 3,
        },
        headers=_build_headers(pat),
        timeout=10,
    )
    return resp.status_code, resp


async def search_issues(client: httpx.AsyncClient, keyword: str, pat=""):
    """搜索已关闭的 Issue"""
    resp = await client.get(
        ISSUE_SEARCH_URL,
        params={
            "q": f"{keyword} repo:{GITHUB_REPO} is:issue is:closed",
            "per_page": 3,
            "sort": "updated",
        },
        headers=_build_headers(pat),
        timeout=10,
    )
    return resp.status_code, resp


async def create_issue(client: httpx.AsyncClient, title: str, body: str, token: str, labels=None):
    """创建 GitHub Issue"""
    if labels is None:
        labels = ["bug", "qq-feedback"]
    resp = await client.post(
        f"{GITHUB_API}/issues",
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}",
        },
        json={"title": title, "body": body, "labels": labels},
        timeout=10,
    )
    return resp.status_code, resp
