# DBX QQ Bot

基于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的 DBX QQ 群助手插件。

## 功能

- `/dbx-latest` — 查询 DBX 最新版本
- `/dbx-star` — 查看 DBX 项目统计
- `/dbx-doc <关键词>` — 搜索 DBX 文档
- `/dbx-changelog <版本号>` — 查看指定版本更新日志
- `/dbx-support <数据库名>` — 查询是否支持某个数据库
- `/dbx-faq <关键词>` — 搜索已解决的 Issue
- `/dbx-issue <描述>` — 提交 Issue 反馈（自动识别 Bug/功能建议）
- `/dbx-help` — 显示所有可用命令
- `/dbx-admin` — 管理员运维命令

## 部署

1. [部署 AstrBot](https://docs.astrbot.app/deploy/astrbot/docker)（推荐 Docker）
2. 配置 QQ 平台（NapCat / OneBot v11）
3. 将此插件放入 `AstrBot/data/plugins/astrbot_plugin_dbx/` 目录
4. 在 AstrBot WebUI 中配置 LLM 提供商
5. 上传 DBX 文档到知识库（用于自动回答问题）
6. 设置环境变量 `BOT_TOKEN` 和 `BOT_PAT`（用于 GitHub API 调用）
