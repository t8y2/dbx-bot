import os

import httpx
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

GITHUB_REPO = "t8y2/dbx"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"

DOC_SEARCH_URL = "https://api.github.com/search/code"

COMMANDS = {
    "/dbx-latest": "查询 DBX 最新版本",
    "/dbx-star": "查看 DBX 项目统计（Star、Fork、Issue）",
    "/dbx-doc <关键词>": "搜索 DBX 文档",
    "/bug <描述>": "提交 Bug 反馈到 GitHub Issue",
    "/dbx-help": "显示所有可用命令",
}

WELCOME_MSG = "👋 欢迎 {name} 加入 DBX 社区! 发送 /dbx-help 查看可用命令~"


@register(
    "astrbot_plugin_dbx",
    "t8y2",
    "DBX 数据库工具的 QQ 群助手插件",
    "1.2.0",
    f"https://github.com/{GITHUB_REPO}-bot",
)
class DBXPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.github_pat = os.environ.get("GITHUB_PAT", "")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_group_increase(self, event: AstrMessageEvent):
        """欢迎新成员"""
        raw = getattr(event.message_obj, "raw_message", None)
        if not isinstance(raw, dict):
            return
        if raw.get("post_type") == "notice" and raw.get("notice_type") == "group_increase":
            name = event.get_sender_name() or "新朋友"
            yield event.plain_result(WELCOME_MSG.format(name=name))

    @filter.command("dbx-help")
    async def help_cmd(self, event: AstrMessageEvent):
        """显示所有可用命令"""
        lines = ["DBX Bot 可用命令:\n"]
        for cmd, desc in COMMANDS.items():
            lines.append(f"  {cmd} — {desc}")
        yield event.plain_result("\n".join(lines))

    @filter.command("dbx-latest")
    async def latest_release(self, event: AstrMessageEvent):
        """查询 DBX 最新版本"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )

        if resp.status_code != 200:
            yield event.plain_result("获取版本信息失败，请稍后再试。")
            return

        data = resp.json()
        tag = data.get("tag_name", "unknown")
        name = data.get("name", tag)
        published = data.get("published_at", "")[:10]
        url = data.get("html_url", "")

        msg = (
            f"DBX 最新版本: {name}\n"
            f"发布日期: {published}\n"
            f"下载: {url}"
        )
        yield event.plain_result(msg)

    @filter.command("dbx-star")
    async def repo_stats(self, event: AstrMessageEvent):
        """查看 DBX 项目统计"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GITHUB_API,
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )

        if resp.status_code != 200:
            yield event.plain_result("获取项目信息失败，请稍后再试。")
            return

        data = resp.json()
        msg = (
            f"DBX 项目统计:\n"
            f"  Star: {data.get('stargazers_count', 0)}\n"
            f"  Fork: {data.get('forks_count', 0)}\n"
            f"  Open Issues: {data.get('open_issues_count', 0)}\n"
            f"  语言: {data.get('language', 'N/A')}\n"
            f"  主页: {data.get('html_url', '')}"
        )
        yield event.plain_result(msg)

    @filter.command("dbx-doc")
    async def search_doc(self, event: AstrMessageEvent):
        """搜索 DBX 文档"""
        keyword = event.message_str.strip()
        if keyword.startswith("dbx-doc"):
            keyword = keyword[7:].strip()
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如: /dbx-doc MCP")
            return

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_pat:
            headers["Authorization"] = f"token {self.github_pat}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                DOC_SEARCH_URL,
                params={
                    "q": f"{keyword} repo:{GITHUB_REPO} path:docs/ extension:mdx",
                    "per_page": 3,
                },
                headers=headers,
                timeout=10,
            )

        if resp.status_code != 200:
            yield event.plain_result("搜索失败，请稍后再试。")
            return

        items = resp.json().get("items", [])
        if not items:
            yield event.plain_result(f"未找到与「{keyword}」相关的文档。")
            return

        lines = [f"找到 {len(items)} 篇相关文档:\n"]
        for item in items:
            name = item.get("name", "").replace(".mdx", "").replace(".md", "")
            url = item.get("html_url", "")
            lines.append(f"  {name}\n  {url}")
        yield event.plain_result("\n".join(lines))

    @filter.command("bug")
    async def report_bug(self, event: AstrMessageEvent):
        """提交 Bug 反馈到 GitHub Issue"""
        description = event.message_str.strip()
        if description.startswith("bug"):
            description = description[3:].strip()
        if not description:
            return

        if not self.github_token:
            yield event.plain_result("Bug 反馈功能未配置，请联系管理员设置 GITHUB_TOKEN。")
            return

        sender = event.get_sender_name()
        body = f"**来源**: QQ 群反馈 (by {sender})\n\n{description}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API}/issues",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "Authorization": f"Bearer {self.github_token}",
                },
                json={
                    "title": f"[QQ 反馈] {description[:80]}",
                    "body": body,
                    "labels": ["bug", "qq-feedback"],
                },
                timeout=10,
            )

        if resp.status_code == 201:
            issue_url = resp.json().get("html_url", "")
            yield event.plain_result(f"Bug 已提交! {issue_url}")
        else:
            logger.error(f"Failed to create issue: {resp.status_code} {resp.text}")
            yield event.plain_result("提交失败，请稍后再试。")

    async def terminate(self):
        pass
