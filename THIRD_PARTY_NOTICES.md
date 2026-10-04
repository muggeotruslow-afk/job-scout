# 来源与许可说明

Job Scout 新增实现采用 MIT。底层工具和方法来源按下面关系说明，不将上游作者的工作描述为本项目从零原创。

## intern-scout

- 来源：https://github.com/LogicShao/intern-scout
- 核对提交：`8d108870dd7f1cdfed497383a51a409d86cd39a5`。
- MIT；原版权声明 `Copyright (c) 2026 Logic Shao`。
- 调用 `intern_scout.crawler.ADAPTERS`，不在本仓库复制其源码。
- [上游完整许可](https://github.com/LogicShao/intern-scout/blob/8d108870dd7f1cdfed497383a51a409d86cd39a5/LICENSE)。若以后复制或分发上游代码，应随附其版权声明与完整许可。

## Career Ops

- 来源：https://github.com/career-ops-hq/career-ops
- 验证版本 1.10.0，提交 `edc971aea3105dcc97e44549bde3ef8f33d402fb`。
- MIT；原版权声明 `Copyright (c) 2026 Santiago Fernández de Valderrama`。
- 可选采用其候选人资料约定，并从用户明确配置的目录加载 `liveness-browser.mjs`、其相邻模块和 Playwright；默认路径现在使用本项目独立编写的核验模块，不在本仓库分发上游源码。
- [上游完整许可](https://github.com/career-ops-hq/career-ops/blob/edc971aea3105dcc97e44549bde3ef8f33d402fb/LICENSE)与[品牌政策](https://github.com/career-ops-hq/career-ops/blob/edc971aea3105dcc97e44549bde3ef8f33d402fb/TRADEMARK.md)。项目使用自己的名称，不表示上游官方背书。

## Crawl4AI

- 来源：https://github.com/unclecode/crawl4ai
- 可选备用工具；本项目没有包含或修改其源码。
- [上游许可](https://github.com/unclecode/crawl4ai/blob/main/LICENSE)为 Apache 2.0 并附额外署名要求，不能只写成普通 Apache 2.0。
- 如以后分发其软件或派生代码，还应随附完整许可、适用 NOTICE 及修改说明。

This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai).

## Playwright

- 来源：https://github.com/microsoft/playwright
- Apache 2.0；验证版本 1.58.1。默认从本项目的 Node 依赖环境加载，也可复用明确配置的 Career Ops 环境；本仓库不分发其包或浏览器。
- [上游许可](https://github.com/microsoft/playwright/blob/main/LICENSE)。

## 其他归属

本项目的抓取包装、百度 API 适配、链接兼容、招聘批次规则、历史匹配、评分规则及 Skill 指令通过项目协作新增或整理。实现由 Codex 辅助编写。没有把候选人的真实简历、画像、投递历史或验收结果作为公开示例。
