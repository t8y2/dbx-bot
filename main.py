import os

import httpx
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

GITHUB_REPO = "t8y2/dbx"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"


@register(
    "astrbot_plugin_dbx",
    "t8y2",
    "DBX 数据库工具的 QQ 群助手插件",
    "1.0.0",
    f"https://github.com/{GITHUB_REPO}-bot",
)
class DBXPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

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

    @filter.command("bug")
    async def report_bug(self, event: AstrMessageEvent):
        """提交 Bug 反馈到 GitHub Issue"""
        description = event.message_str.strip()
        if not description:
            yield event.plain_result("请描述你遇到的问题，例如: /bug 连接 MySQL 时闪退")
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
