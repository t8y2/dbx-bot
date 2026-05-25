import os
import re

import httpx
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At, Plain

GITHUB_REPO = "t8y2/dbx"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"

DOC_SEARCH_URL = "https://api.github.com/search/code"

COMMANDS = {
    "/dbx-latest": "查询 DBX 最新版本",
    "/dbx-star": "查看 DBX 项目统计（Star、Fork、Issue）",
    "/dbx-doc <关键词>": "搜索 DBX 文档",
    "/dbx-changelog <版本号>": "查看指定版本的更新日志",
    "/dbx-support <数据库名>": "查询 DBX 是否支持某个数据库",
    "/dbx-faq <关键词>": "搜索已解决的 GitHub Issue",
    "/bug <描述>": "提交 Bug 反馈到 GitHub Issue",
    "/dbx-help": "显示所有可用命令",
}

SUPPORTED_DATABASES = [
    "MySQL", "PostgreSQL", "SQLite", "Redis", "MongoDB", "DuckDB",
    "ClickHouse", "SQL Server", "Oracle", "Elasticsearch", "MariaDB",
    "TiDB", "OceanBase", "openGauss", "GaussDB", "KingBase", "Vastbase",
    "GoldenDB", "Doris", "SelectDB", "StarRocks", "Redshift", "DM",
    "TDengine", "CockroachDB", "Access", "HighGo",
]

WELCOME_MSG = (
    " 欢迎加入 DBX 社区!\n"
    "  遇到问题? 提 Issue: https://github.com/t8y2/dbx/issues\n"
    "  欢迎贡献代码: https://github.com/t8y2/dbx/pulls\n"
    "  发送 /dbx-help 查看可用命令"
)


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
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_pat:
            headers["Authorization"] = f"token {self.github_pat}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GITHUB_API,
                headers=headers,
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
        keyword = re.sub(r'(?<=[a-zA-Z])(?=[一-鿿])|(?<=[一-鿿])(?=[a-zA-Z])', ' ', keyword)
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如: /dbx-doc MCP")
            return

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_pat:
            headers["Authorization"] = f"token {self.github_pat}"

        items = []
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
            if resp.status_code == 200:
                items = resp.json().get("items", [])

            if not items:
                en_only = re.sub(r'[一-鿿]+', '', keyword).strip()
                if en_only and en_only != keyword:
                    resp = await client.get(
                        DOC_SEARCH_URL,
                        params={
                            "q": f"{en_only} repo:{GITHUB_REPO} path:docs/ extension:mdx",
                            "per_page": 3,
                        },
                        headers=headers,
                        timeout=10,
                    )
                    if resp.status_code == 200:
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
            url = f"{GITHUB_API}/releases/latest"
        else:
            if not tag.startswith("v"):
                tag = f"v{tag}"
            url = f"{GITHUB_API}/releases/tags/{tag}"

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_pat:
            headers["Authorization"] = f"token {self.github_pat}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
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

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_pat:
            headers["Authorization"] = f"token {self.github_pat}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/search/issues",
                params={
                    "q": f"{keyword} repo:{GITHUB_REPO} is:issue is:closed",
                    "per_page": 3,
                    "sort": "updated",
                },
                headers=headers,
                timeout=10,
            )

        if resp.status_code != 200:
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
                f"  版本: 1.2.0\n"
                f"  仓库: https://github.com/t8y2/dbx\n"
                f"  服务器时间: {now}"
            )
            yield event.plain_result(msg)
        else:
            yield event.plain_result(f"未知子命令「{sub}」，使用 /dbx-admin help 查看可用命令。")

    async def terminate(self):
        pass
