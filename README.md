# DBX QQ Bot

基于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的 DBX QQ 群助手插件。

## 功能

- `/dbx-latest` — 查询 DBX 最新版本
- `/bug <描述>` — 提交 Bug 反馈到 GitHub Issue
- 自动回答使用问题 — 通过 AstrBot 内置的 LLM + 知识库（RAG）实现

## 部署

1. [部署 AstrBot](https://docs.astrbot.app/deploy/astrbot/docker)（推荐 Docker）
2. 配置 QQ 平台（NapCat / OneBot v11）
3. 将此插件放入 `AstrBot/data/plugins/astrbot_plugin_dbx/` 目录
4. 在 AstrBot WebUI 中配置 LLM 提供商
5. 上传 DBX 文档到知识库（用于自动回答问题）
6. 设置环境变量 `GITHUB_TOKEN`（用于 `/bug` 命令创建 Issue）
