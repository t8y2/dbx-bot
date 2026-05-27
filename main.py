import json
import os
import re

import httpx
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At, Plain

from . import github_api
from .constants import (
    COMMANDS,
    SUPPORTED_DATABASES,
    WELCOME_MSG,
    GITHUB_REPO,
)

_BUG_KEYWORDS_CN = ["报错", "异常", "错误", "崩溃", "闪退"]
_FEATURE_KEYWORDS_CN = ["建议", "希望", "功能", "需求", "增加", "添加"]


@register(
    "astrbot_plugin_dbx",
    "t8y2",
    "DBX 数据库工具的 QQ 群助手插件",
    "1.3.1",
    f"https://github.com/{GITHUB_REPO}-bot",
)
class DBXPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.bot_token = os.environ.get("BOT_TOKEN", "")
        self.bot_pat = os.environ.get("BOT_PAT", "")
        self.deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_group_increase(self, event: AstrMessageEvent):
        """欢迎新成员"""
        raw = getattr(event.message_obj, "raw_message", None)
        if not isinstance(raw, dict):
            return
        if raw.get("post_type") == "notice" and raw.get("notice_type") == "group_increase":
            user_id = str(raw.get("user_id", ""))
            chain = [At(qq=user_id), Plain(WELCOME_MSG)]
            yield event.chain_result(chain)

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
            code, resp = await github_api.get_latest_release(client)

        if code != 200:
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
            code, resp = await github_api.get_repo_stats(client, self.bot_pat)

        if code != 200:
            yield event.plain_result("获取项目信息失败，请稍后再试。")
            return

        data = resp.json()

        # 统计最近版本下载量
        total_downloads = 0
        release_count = 0
        async with httpx.AsyncClient() as client:
            code2, resp2 = await github_api.get_releases(client, per_page=10, pat=self.bot_pat)
            if code2 == 200:
                releases = resp2.json()
                release_count = len(releases)
                for r in releases:
                    for a in r.get("assets", []):
                        total_downloads += a.get("download_count", 0)

        msg = (
            f"DBX 项目统计:\n"
            f"  Star: {data.get('stargazers_count', 0)}\n"
            f"  Fork: {data.get('forks_count', 0)}\n"
            f"  Open Issues: {data.get('open_issues_count', 0)}\n"
            f"  语言: {data.get('language', 'N/A')}\n"
            f"  主页: {data.get('html_url', '')}"
        )
        if total_downloads:
            msg += f"\n  近{release_count}个版本总下载: {total_downloads:,}"
        yield event.plain_result(msg)

    @filter.command("dbx-doc")
    async def search_doc(self, event: AstrMessageEvent):
        """搜索 DBX 文档"""
        keyword = event.message_str.strip()
        if keyword.startswith("dbx-doc"):
            keyword = keyword[7:].strip()
        keyword = re.sub(r'(?<=[a-zA-Z])(?=[一-鿿])|(?<=[一-鿿])(?=[a-zA-Z])', ' ', keyword)
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如: /dbx-doc MCP")
            return

        items = []
        async with httpx.AsyncClient() as client:
            code, resp = await github_api.search_docs(client, keyword, self.bot_pat)
            if code == 200:
                items = resp.json().get("items", [])

            if not items:
                en_only = re.sub(r'[一-鿿]+', '', keyword).strip()
                if en_only and en_only != keyword:
                    code, resp = await github_api.search_docs(client, en_only, self.bot_pat)
                    if code == 200:
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

    @filter.command("dbx-issue")
    async def create_issue(self, event: AstrMessageEvent):
        """提交 Issue 反馈，使用 LLM 自动分类并生成标题"""
        description = event.message_str.strip()
        if description.startswith("dbx-issue"):
            description = description[9:].strip()
        if not description:
            yield event.plain_result("请输入 Issue 描述，例如: /dbx-issue 启动时报错 XXX")
            return

        if not self.bot_token and not self.bot_pat:
            yield event.plain_result("Issue 反馈功能未配置，请联系管理员设置 BOT_TOKEN 或 BOT_PAT。")
            return

        sender = event.get_sender_name()
        result = None
        if self.deepseek_key:
            try:
                result = await self._classify_with_llm(description)
            except Exception as e:
                logger.error(f"LLM classification failed, falling back to keywords: {e}")

        if result:
            title = result["title"]
            labels = result["labels"] + ["qq-feedback"]
            body = f"**来源**: QQ 群反馈 (by {sender})\n\n## AI 摘要\n{result['summary']}\n\n## 原始描述\n{description}"
        else:
            desc_lower = description.lower()
            is_bug = any(kw in desc_lower for kw in _BUG_KEYWORDS_CN) or bool(re.search(r'\bbug\b', desc_lower, re.ASCII))
            is_feature = any(kw in desc_lower for kw in _FEATURE_KEYWORDS_CN) or bool(re.search(r'\bfeature\b', desc_lower, re.ASCII))
            prefix = "[Feature]" if (is_feature and not is_bug) else "[Bug]"
            labels = (["enhancement"] if prefix == "[Feature]" else ["bug"]) + ["qq-feedback"]
            title = f"{prefix} {description[:80]}"
            body = f"**来源**: QQ 群反馈 (by {sender})\n\n{description}"

        async with httpx.AsyncClient() as client:
            token = self.bot_token or self.bot_pat
            code, resp = await github_api.create_issue(client, title, body, token, labels)

        if code == 201:
            issue_url = resp.json().get("html_url", "")
            yield event.plain_result(f"Issue 已提交! {issue_url}")
        else:
            logger.error(f"Failed to create issue: {code} {resp.text}")
            yield event.plain_result("提交失败，请稍后再试。")

    async def _classify_with_llm(self, description: str):
        """使用 DeepSeek 对 Issue 进行分类并生成标题、摘要"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.deepseek_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "你是一个 GitHub Issue 分类助手。根据用户的问题描述，判断是 Bug 还是功能建议，"
                                "生成简洁的 Issue 标题（不超过 80 字），并提取关键摘要（不超过 200 字）。\n\n"
                                "返回 JSON：{\"type\": \"bug\"|\"feature\", \"title\": \"标题\", \"summary\": \"摘要\"}"
                            ),
                        },
                        {"role": "user", "content": description},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.3,
                },
                timeout=30,
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return {
                "title": parsed.get("title", description[:80]),
                "labels": ["bug"] if parsed.get("type") == "bug" else ["enhancement"],
                "summary": parsed.get("summary", ""),
            }

    @filter.command("dbx-changelog")
    async def changelog(self, event: AstrMessageEvent):
        """查看 DBX 指定版本的更新日志"""
        tag = event.message_str.strip()
        if tag.startswith("dbx-changelog"):
            tag = tag[len("dbx-changelog"):].strip()
        if not tag:
            yield event.plain_result("请指定版本号，例如: /dbx-changelog v0.5.19 或 /dbx-changelog latest")
            return

        if tag.lower() == "latest":
            async with httpx.AsyncClient() as client:
                code, resp = await github_api.get_latest_release(client)
        else:
            if not tag.startswith("v"):
                tag = f"v{tag}"
            async with httpx.AsyncClient() as client:
                code, resp = await github_api.get_release(client, tag, self.bot_pat)

        if code != 200:
            yield event.plain_result(f"未找到版本「{tag}」的更新日志。")
            return

        data = resp.json()
        body = data.get("body", "")
        html_url = data.get("html_url", "")
        tag_name = data.get("tag_name", tag)
        published = data.get("published_at", "")[:10]

        if len(body) > 1500:
            body = body[:1500] + f"\n\n... 完整内容: {html_url}"

        msg = f"DBX {tag_name} ({published})\n{html_url}\n\n{body}"
        yield event.plain_result(msg)

    @filter.command("dbx-support")
    async def check_support(self, event: AstrMessageEvent):
        """查询 DBX 是否支持某个数据库"""
        keyword = event.message_str.strip()
        if keyword.startswith("dbx-support"):
            keyword = keyword[len("dbx-support"):].strip()
        if not keyword:
            yield event.plain_result("请输入数据库名称，例如: /dbx-support MySQL")
            return

        keyword_lower = keyword.lower()
        matches = [db for db in SUPPORTED_DATABASES if keyword_lower in db.lower()]

        if not matches:
            yield event.plain_result(f"未找到与「{keyword}」匹配的数据库，DBX 可能暂不支持。\n已知支持的数据库列表: https://dbxio.com/docs/datasources/overview")
            return

        if len(matches) == 1 and matches[0].lower() == keyword_lower:
            yield event.plain_result(f"DBX 支持 {matches[0]}。\n文档: https://dbxio.com/docs/datasources/{matches[0].lower().replace(' ', '-')}")
        else:
            yield event.plain_result(f"找到 {len(matches)} 个匹配: {', '.join(matches)}")

    @filter.command("dbx-faq")
    async def search_faq(self, event: AstrMessageEvent):
        """搜索已解决的 GitHub Issue"""
        keyword = event.message_str.strip()
        if keyword.startswith("dbx-faq"):
            keyword = keyword[len("dbx-faq"):].strip()
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如: /dbx-faq 连接失败")
            return

        async with httpx.AsyncClient() as client:
            code, resp = await github_api.search_issues(client, keyword, self.bot_pat)

        if code != 200:
            yield event.plain_result("搜索 FAQ 失败，请稍后再试。")
            return

        items = resp.json().get("items", [])
        if not items:
            yield event.plain_result(f"未找到与「{keyword}」相关的已解决问题。")
            return

        lines = [f"找到 {len(items)} 个相关 Issue:\n"]
        for item in items:
            title = item.get("title", "")
            url = item.get("html_url", "")
            state = "已关闭" if item.get("state") == "closed" else item.get("state", "")
            lines.append(f"  [{state}] {title}\n  {url}")
        yield event.plain_result("\n".join(lines))

    @filter.command("dbx-admin")
    async def admin_cmd(self, event: AstrMessageEvent):
        """管理员运维命令"""
        sub = event.message_str.strip()
        if sub.startswith("dbx-admin"):
            sub = sub[len("dbx-admin"):].strip()

        if not sub or sub == "help":
            yield event.plain_result(
                "DBX Bot 管理命令:\n"
                "  /dbx-admin status — 查看 Bot 运行状态\n"
                "  /dbx-admin help — 显示此帮助"
            )
            return

        if sub == "status":
            import datetime
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = (
                f"DBX Bot 运行中\n"
                f"  版本: 1.3.0\n"
                f"  仓库: https://github.com/t8y2/dbx\n"
                f"  服务器时间: {now}"
            )
            yield event.plain_result(msg)
        else:
            yield event.plain_result(f"未知子命令「{sub}」，使用 /dbx-admin help 查看可用命令。")

    async def terminate(self):
        pass
