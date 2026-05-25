GITHUB_REPO = "t8y2/dbx"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"

DOC_SEARCH_URL = "https://api.github.com/search/code"
ISSUE_SEARCH_URL = "https://api.github.com/search/issues"

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
