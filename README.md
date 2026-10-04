<p align="center"><img src="assets/job-scout-icon.png" alt="Job Scout" width="160"></p>

<h1 align="center">Job Scout</h1>

<p align="center"><strong>描述目标 → 发现官网岗位 → 证据匹配 → 核验链接</strong></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-orange" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/platform-Windows-blue" alt="Tested platform: Windows">
  <a href="https://github.com/muggeotruslow-afk/job-scout/releases/tag/v0.1.1"><img src="https://img.shields.io/badge/release-v0.1.1-blue" alt="Release v0.1.1"></a>
  <img src="https://img.shields.io/badge/type-AI%20Skill-teal" alt="AI Skill">
</p>

<p align="center"><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

---

用一句话寻找实习岗位，读取官网完整 JD，并根据使用者的真实简历解释资格门槛、匹配分和投递优先级。

这是 **AI Skill + 抓取与核验脚本**。脚本负责获取、整理岗位和核验页面；AI 负责理解简历、映射岗位要求、评分和输出报告。Python 脚本不会独立生成匹配分，也不会提交申请。

首版：**v0.1.1**。下载源码包与演示视频见 [GitHub Release](https://github.com/muggeotruslow-afk/job-scout/releases/tag/v0.1.1)。

## 演示

### 一句话找岗完整演示（约45秒）

https://github.com/user-attachments/assets/19e9ab97-dff8-4127-ad09-2e77daa500b1

过程已加速，实际耗时约5分钟。

### 打开官网岗位链接（约15秒）

https://github.com/user-attachments/assets/9e721f27-a07c-4068-85d4-3b7c0f197d82

[高清成片与源码下载](https://github.com/muggeotruslow-afk/job-scout/releases/tag/v0.1.1)

演示使用事先确认的虚构候选人资料。下载项目后不带已确认画像，首次使用会引导你导入自己的材料；岗位数量与核验状态是录制当时的结果。

## 为什么不只搜索职位名称

职位名称不统一，同一求职方向可能以不同名称出现。用户想找“产品运营”，相关机会可能叫 AI 产品运营、产品实习生、运营实习生、项目实习生或数据实习生。只搜索一个职位名称，可能漏掉实际职责相关的岗位。

Job Scout 希望解决的是这种发现问题：把用户的求职方向转成职责、工作场景和能力要求，在可获取的岗位范围内读取完整 JD，识别相关机会，再结合候选人资料筛选和排序。它不只是把同名岗位与简历做匹配。这种能力更准确地说是“按职责发现岗位”或“语义岗位搜索”，不只是关键词的模糊匹配。

这些名称是扩大候选范围的线索，不是岗位等价关系。例如项目经理不一定承担产品经理职责，数据实习生也不一定适合产品运营。是否推荐以实际 JD 和候选人证据为准；抓取范围、分类过滤和官网可用性仍会影响覆盖，不能承诺找全所有相关岗位。

以上定位记录于 2026-10-03，作为后续筛选策略与演示说明的依据，不代表已经对所有公司验收这一能力。

## 能力

- 固定官网入口：百度、腾讯、网易、小红书、快手、京东、拼多多、华为使用公开 HTTP API；阿里、字节、小米使用匿名浏览器执行官网自身的查询。统一支持中文公司名称、分页去重、JD和招聘批次。
- 其他公司可调用 intern-scout 适配器；`intern-scout --list` 是适配器名单，不是当前可用性保证。上线前已检查31家公司，结果见 [公司覆盖实测](references/company-coverage.md)。
- 招聘批次分类、投递历史匹配、蔚来已知链接修正。
- 浏览器核验岗位标题与申请提示，区分 `active / uncertain / expired / unverified`。
- AI 按真实候选人证据分别判断资格、100 分匹配度与投递优先级。

## 安装

需要 Python 3.10+；浏览器抓取/核验还需要 Node.js 20+ 和 Playwright。Career Ops 为可选兼容。当前实际验证环境是 Windows；macOS/Linux 尚未完成端到端验证。

### 1. 安装 Skill

下载本项目到名为 `job-scout` 的目录，例如 `D:\projects\job-scout`。

在 Codex 中明确引用该目录的 `SKILL.md` 即可使用；如需全局发现，将公开文件复制到 `~/.codex/skills/job-scout`。不要复制 `local/`、私人资料或交接文件。此处的 `~` 表示当前用户主目录。

### 2. 抓取依赖

**百度、腾讯、网易、小红书、快手、京东、拼多多、华为的抓取无需 Python 第三方库。** 可直接运行 `scripts/scan_jobs.py`。阿里、字节、小米的抓取需要下述 Node 浏览器依赖；不会求解验证码或登录账户。

抓取其他支持的公司，需要 Git 并安装已核对的 intern-scout 提交：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-intern-scout.txt
.venv\Scripts\intern-scout --list
```

后续用 `.venv\Scripts\python` 运行抓取脚本。若已通过 uv tool 安装 intern-scout，脚本也会尝试定位其 Python 环境；普通虚拟环境不依赖这项自动发现。

### 3. 浏览器核验依赖

浏览器固定抓取入口与详情核验均可使用本项目的 Playwright 安装：

```powershell
npm ci
npx playwright install chromium
```

默认使用项目内独立核验模块，不需要Career Ops。已有Career Ops用户可通过 `--career-ops-root <path>` 复用其浏览器依赖和存活检查模块，可选安装步骤如下。

在项目目录之外安装 Career Ops。已验证版本：1.10.0，提交 `edc971aea3105dcc97e44549bde3ef8f33d402fb`。

```powershell
git clone https://github.com/career-ops-hq/career-ops.git ../career-ops
git -C ../career-ops checkout edc971aea3105dcc97e44549bde3ef8f33d402fb
Push-Location ../career-ops
npm install
npx playwright install chromium
Pop-Location
$env:CAREER_OPS_ROOT = (Resolve-Path ../career-ops).Path
```

验证器从该目录读取 `package.json`、`liveness-browser.mjs` 和安装的 Playwright。它会优先使用 Windows 已安装的 Chrome/Edge，否则使用 Playwright Chromium。系统浏览器存在但无法启动时，应先排查安装或权限问题。

新版本 Career Ops 的模块接口可能变化，升级后需重新核验兼容性。

## 配置候选人资料

首次在AI客户端调用时，直接说“帮我找腾讯AI产品实习”即可。Skill会检查环境和本地资料；读取你提供的简历，提取已有经历、学历和技能，只补问缺失的城市、出勤、到岗、时长等条件。显示摘要供你纠正，确认后保存并继续原来的找岗任务。可参考 [虚构资料模板](examples/candidate.md)。

私人资料默认保存到 `local/user/profile.json`，Git已忽略。通过 `JOB_SCOUT_DATA_DIR` 或 `onboarding.py --data-dir <path>` 可指定其他本地目录。下次复用资料，不重复完整问卷；换简历或改条件时更新受影响部分。未知条件保留为未知，作品链接、投递历史可跳过，不要求提供电话、邮箱或照片。

Markdown、UTF-8文本和DOCX有内置文字提取；PDF/图片由AI客户端读取或OCR，无法读取时可粘贴文本。保存前的确认用于核对提取结果，未确认草稿不会当作已就绪。首次引导规则见 [first-use.md](references/first-use.md)。

```powershell
# 状态和环境检查不会自动安装软件，也不创建个人资料
python scripts/onboarding.py status
python scripts/onboarding.py doctor
# 文本导入：只读取，不自动确认或保存
python scripts/onboarding.py import-resume --resume <resume.docx>
```

Career Ops 的资料约定为 `cv.md`、`config/profile.yml`、`modes/_profile.md`，可选投递历史为 `data/applications.md`。当前用户提供的新材料优先于旧文件。AI 读取资料后评分，抓取脚本不会自动解析 DOCX 或计算相性分。

历史匹配是可选的；不提供历史时，结果中的 `new` 只表示未匹配到历史，不代表从未申请。额外 Markdown 历史文件通过重复的 `--history <path>` 指定，格式见 [虚构历史样例](examples/applications.md)。

仅设置 `--career-ops-root` 不会读取投递历史；若明确选择使用其中的记录，再加 `--use-career-ops-history`。这避免把只用于浏览器依赖的目录误当成个人资料来源。

将私人资料和运行结果放在 `local/`、`data/` 或 `output/`，这些目录已被 Git 忽略。上传前仍须检查实际暂存文件。

## 使用

给 AI 的示例：

> 使用这个目录的 Job Scout。我的简历在本地指定位置，每周可出勤 5 天、持续 6 个月。帮我找百度适合我的 AI 产品日常实习，按匹配度排序，给出评分理由和官网链接。

脚本示例均从项目根目录运行：

```powershell
# 百度所有产品类日常实习：不安装 intern-scout、不读取私人资料
python scripts/scan_jobs.py --company baidu --baidu-category product --output output/baidu.json

# 关键词搜索；--limit 只限制输出，不代替分页抓取
python scripts/scan_jobs.py --company baidu --baidu-category product --keyword AI --limit 10 --output output/baidu-ai.json

# 同时核验：先在本项目安装Playwright，Career Ops无需配置
python scripts/scan_jobs.py --company baidu --baidu-category product --keyword AI --verify --verify-limit 10 --output output/baidu-ai-verified.json

# 其他公司使用已安装 intern-scout 的环境
.venv\Scripts\python scripts/scan_jobs.py --company vivo --keyword 产品 --output output/vivo.json
```

新增固定入口可直接使用中文名称，例如：

```powershell
python scripts/scan_jobs.py --company 腾讯 --keyword 产品 --http-proxy direct --output output/tencent.json
python scripts/scan_jobs.py --company 京东 --http-proxy direct --output output/jd.json
python scripts/scan_jobs.py --company 拼多多 --http-proxy direct --output output/pdd.json
python scripts/scan_jobs.py --company 阿里 --browser-proxy direct --output output/alibaba.json
python scripts/scan_jobs.py --company 字节 --page-size 50 --max-pages 100 --browser-proxy direct --output output/bytedance.json
```

阿里、字节、小米用浏览器固定入口，需先完成 Node 依赖安装，不依赖 intern-scout。只有确认代理失败时才需要 `direct` 参数。

`--max-pages` 默认50。大量岗位需提高上限；未收齐时结果为partial。阿里与网易等部分接口的关键词不稳定，采用来源扫描后本地关键词筛选，`scope.keyword_filter`说明实际方式；不能把筛选后的条数称为官网全部岗位。

百度默认获取所有类别的**日常实习**；`--baidu-category product` 限制为官网产品类别，这一类别也包含部分运营岗位。自然语言里的“AI 产品”仍需 AI 阅读 JD 筛选，不应只匹配岗位标题中的 AI。

百度官网 API 的分页大小固定为 10，不使用 `--page-size`。其他入口的有效分页大小以结果中的 `pagination.page_size` 为准。`--max-pages` 默认 50；达到上限、重复页或总数未收齐时会给出 `complete=false`，不能宣传为全量。

### 代理与详情页兼容

默认保留系统连接方式。如果已确认代理导致连接错误，可仅对本次运行使用直连：

```powershell
python scripts/scan_jobs.py --company baidu --baidu-category product --http-proxy direct --browser-proxy direct --verify --verify-limit 10 --output output/baidu-verified.json
```

也可设置 `JOB_SCOUT_HTTP_PROXY`、`JOB_SCOUT_BROWSER_PROXY` 为 `direct` 或代理 URL；命令行参数优先。不要把带凭据的代理地址提交到仓库。

百度官方页面会把检测到调试连接的浏览器跳转到 `about:blank`。验证器仅在其官方实习详情页加入官网脚本提供的 `dev=0` 参数，保留原链接，并将实际检查地址写入 `verification.requested_url`。这是已实测的兼容处理，官网变化后可能需要调整。

## 输出与边界

新固定入口已接入，但可用性以 [公司覆盖实测](references/company-coverage.md) 的最新验收为准。京东取官方实习生计划，拼多多取实习入口，不能把它们一律称为日常实习；具体批次仍需阅读 JD。其他适配器的空结果或连接失败也不能解释成“没有岗位”。

抓取 JSON 明确给出 `status`：`complete`（范围内分页收齐且 JD 字段完整）、`partial`（页数上限、重复页、缺JD或中途失败）、`failed`（未取得数据）、`empty_query`（该查询没有返回记录）。`errors`保留失败阶段和页码，`pagination`说明停止原因；中途失败保留已取得岗位，进程返回码2。不会自动拿第三方摘要替代官方JD。

分页总数是官网返回行数，可能包含重复职位；`pagination.rows_received`与`duplicate_rows`分别记录原始行数与去重数量。`pagination.completion_basis=raw_rows` 表示按官网原始行数判断分页收齐，不能解释成已取得同样数量的唯一岗位；去重后的数量另见 `unique_positions`。列表是实时变化的，本次完整扫描不保证永久不变，也不证明覆盖其他招聘入口。

- JSON 包含抓取范围、总数、完整性、岗位 JD、日期、招聘批次、历史匹配及可选浏览器核验结果。
- `--verify-limit` 默认 30，仅检查前若干条；其他岗位仍为 `unverified`。脚本顺序不是 AI 匹配分排序。建议 AI 先筛选候选，再直接对候选 JSON 运行 `verify_jobs.mjs`。
- 核验发现的是标题与申请提示，并未完成登录、点击提交或确认招聘方还有剩余名额。
- 批次分类使用关键词，历史匹配使用名称相似度，均需对重要结果复核。
- 未提供完整 JD 或候选人资料时不输出精确匹配分；学历硬门槛与“专业优先”分开判断。
- 不自动投递、上传简历、联系招聘者或更新投递记录。
- Crawl4AI 是 AI 可选的备用网页抓取工具，不是 Python 脚本自动回退依赖；不安装也能使用百度固定入口。

## 验证

```powershell
python -m unittest discover -s tests -v
npm test
```

发布包以根目录 `release-files.json` 为唯一打包清单，运行 `python scripts/build_release.py` 生成到 `local/releases/`。不要压缩整个开发目录；Git忽略规则不会自动作用于普通压缩包。包内不含画像、录屏、node_modules或验收记录，依赖仍按安装说明配置。

发布文件以 `release-files.json` 为准；测试数量以当前运行输出为准。

2026-10-03 验收：

- 原始环境验收为Windows / Python 3.12 / Node.js 24；后续发布复查当前共44项Python测试和9项Node测试通过，覆盖发布包排除、失败恢复和核验参数等场景。当前本机Python已更新至3.14，早期3.12验收记录仍保留。
- 百度产品类日常实习分页获得 197 条完整 JD；10 条候选通过标题和申请提示检查。此数量是当时结果，不是固定测试断言。
- 公开文件复制到隔离目录，新建无 intern-scout 的 Python 环境、不配置私人 Career Ops，也能通过统一入口抓到 197 条岗位。
- 从固定上游提交重新下载 Career Ops 核验模块，按其声明安装全新 Node 依赖；使用统一 `scan_jobs.py --verify` 入口核验一条岗位成功。浏览器复用本机 Chrome，未验证全新电脑的浏览器下载流程。
- 固定提交的 intern-scout 在隔离环境安装成功，能列出 20 个适配入口；没有对这些公司进行全量网络回归。

个人简历参与的筛选验收与依赖隔离验收分开完成。后者验证脚本安装与调用，不代表已经在全新 AI 会话中验证过简历理解、评分一致性，也不宣称所有环境都已验证。

后续在独立对话中完成了虚构候选人的百度流程验收（197条、精选12条浏览器核验）。本轮又完成9个官方入口的完整分页扫描，具体数量、批次和详情控件限制见公司覆盖表。快手详情可能要求用户确认隐私政策，禁用控件保持uncertain，不代用户接受条款。

首次使用的独立对话验收也已完成：新测试目录识别为first_use；只读取虚构资料，展示摘要并等待确认；确认后保存为ready，继续取得百度产品类日常实习197条，并用本项目独立模块核验15条。未配置Career Ops或读取旧profile。

缺失条件分支随后完成独立对话验收：只使用消息里的简短虚构经历，主动补问城市、每周出勤、到岗时间和实习时长；按用户回答更新为北京、每周4天、2026-10-17到岗、4个月。确认前未保存或抓取；确认后保存并继续获取197条，精选7条AI产品及1条明确标注的相邻岗位，8条详情核验通过，排除不满足出勤、时长或届别硬门槛的岗位。

## 来源与许可证

本项目是 AI 辅助开发的工作流整合：需求定义、筛选规则、工具编排及验收迭代由项目维护者主导，脚本由 Codex 辅助实现。

| 上游 | 使用关系 |
|---|---|
| [intern-scout](https://github.com/LogicShao/intern-scout) | 调用其 ATS 适配器；本项目增加分页包装、加工与历史匹配 |
| [Career Ops](https://github.com/career-ops-hq/career-ops) | 可选兼容候选人资料约定、岗位存活检查模块及依赖环境 |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | AI 对不支持站点的可选备用抓取路径 |
| [Playwright](https://github.com/microsoft/playwright) | 浏览器运行时，由本项目或可选Career Ops环境提供 |

百度公开 API 适配、核验兼容处理及本项目包装脚本在此项目中实现；不宣称底层 ATS 或 Career Ops 存活检查是自主原创。job-pro 是早期选型工具，当前代码没有直接依赖。

本项目新增内容采用 [MIT](LICENSE)，上游各自许可不被覆盖，详见 [来源与许可说明](THIRD_PARTY_NOTICES.md)。仓库不包含 intern-scout、Career Ops 或 Crawl4AI 的源码副本。

This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai).
